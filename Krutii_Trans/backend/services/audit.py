"""
Журнал дій (аудит): хто, коли, що змінив, з якої адреси.

Запис робиться автоматично для кожного запиту, що змінює дані (POST / PUT / DELETE):
перед запитом зберігається «знімок» запису, після успішного запиту - новий знімок,
а різниця між ними записується як «було -> стало». Журнал лише доповнюється:
API для зміни або видалення записів журналу немає.
"""
import json
import re
from datetime import datetime, timedelta

from bson import ObjectId
from flask import g, request

# endpoint -> (категорія, опис дії)
ACTIONS = {
    'auth.login': ('login', 'Вхід у систему'),
    'auth.email_code_request': ('login', 'Запит коду входу на пошту'),
    'auth.email_code_verify': ('login', 'Вхід за кодом з пошти'),
    'auth.logout': ('logout', 'Вихід із системи'),
    'auth.update_me': ('user', 'Зміна власних контактів'),
    'auth.change_password': ('security', 'Зміна пароля'),
    'users.create_user': ('user', 'Створення користувача'),
    'users.update_user': ('user', 'Зміна користувача'),
    'users.reset_password': ('security', 'Скидання пароля користувача'),
    'vehicles.create_vehicle': ('vehicle', 'Додавання автомобіля'),
    'vehicles.update_vehicle': ('vehicle', 'Зміна автомобіля'),
    'vehicles.update_odometer': ('vehicle', 'Оновлення пробігу'),
    'waybills.create_waybill': ('waybill', 'Видача путівки'),
    'waybills.update_waybill': ('waybill', 'Зміна путівки'),
    'waybills.cancel_waybill': ('waybill', 'Скасування путівки'),
    'fuel.create_invoice': ('fuel', 'Накладна на пальне'),
    'fuel.create_record': ('fuel', 'Видача або заправка пального'),
    'faults.create_fault': ('fault', 'Повідомлення про несправність'),
    'faults.update_fault': ('fault', 'Обробка несправності'),
    'faults.upload_photo': ('fault', 'Додавання фото несправності'),
    'faults.delete_photo': ('fault', 'Видалення фото несправності'),
    'repairs.create_repair': ('repair', 'Створення ремонту / ТО'),
    'repairs.update_repair': ('repair', 'Зміна ремонту / ТО'),
    'settings.update_settings': ('settings', 'Зміна налаштувань системи'),
    'settings.reset_settings': ('settings', 'Скидання налаштувань до стандартних'),
    'parts.create_part': ('part', 'Додавання запчастини'),
    'parts.update_part': ('part', 'Зміна запчастини'),
    'parts.receive': ('part', 'Надходження запчастин'),
}
# параметр маршруту -> колекція, з якої береться «знімок» запису
SNAPSHOT_ARGS = {
    'user_id': 'users', 'vehicle_id': 'vehicles', 'waybill_id': 'waybills',
    'fault_id': 'fault_reports', 'repair_id': 'repairs', 'part_id': 'parts',
}
ENTITY_TYPES = {
    'users': 'user', 'vehicles': 'vehicle', 'waybills': 'waybill', 'fault_reports': 'fault',
    'repairs': 'repair', 'parts': 'part', 'settings': 'settings',
}
# службові поля, які не показуємо в «було -> стало»
IGNORED_FIELDS = {'_id', 'created_at', 'updated_at', 'last_login', 'password_hash', 'photos', 'created_by', 'updated_by'}
SECURITY_FAIL_LIMIT = 5          # невдалих входів поспіль -> сповіщення керівнику
SECURITY_FAIL_WINDOW_MIN = 15
RETENTION_DAYS = 365


def client_ip():
    forwarded = request.headers.get('X-Forwarded-For', '')
    return (forwarded.split(',')[0].strip() if forwarded else request.remote_addr) or '-'


def short_agent(ua):
    """Коротко: «Chrome · Windows»."""
    ua = ua or ''
    browser = next((name for key, name in [('Edg/', 'Edge'), ('OPR/', 'Opera'), ('Firefox/', 'Firefox'),
                                            ('Chrome/', 'Chrome'), ('Safari/', 'Safari')] if key in ua), 'Інший')
    system = next((name for key, name in [('Windows', 'Windows'), ('Android', 'Android'), ('iPhone', 'iPhone'),
                                           ('iPad', 'iPad'), ('Mac OS', 'macOS'), ('Linux', 'Linux')] if key in ua), '')
    if 'python' in ua.lower() or 'werkzeug' in ua.lower():
        return 'API'
    return f'{browser} · {system}' if system else browser


def entity_label(doc, collection=None):
    if not doc:
        return None
    if collection == 'settings' or doc.get('_id') == 'system':
        return 'Налаштування системи'
    if doc.get('plate_number'):
        return f"{doc['plate_number']} {doc.get('brand', '')} {doc.get('model', '')}".strip()
    if doc.get('number'):
        return doc['number']
    if doc.get('full_name'):
        return f"{doc['full_name']} ({doc.get('username', '')})" if doc.get('username') else doc['full_name']
    if doc.get('name'):
        return doc['name']
    return doc.get('username')


def _fmt(value):
    if value is None or value == '':
        return '—'
    if isinstance(value, datetime):
        return value.strftime('%Y-%m-%d %H:%M') if (value.hour or value.minute) else value.strftime('%Y-%m-%d')
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, bool):
        return 'так' if value else 'ні'
    if isinstance(value, (list, dict)):
        text = json.dumps(value, ensure_ascii=False, default=str)
        return text if len(text) <= 140 else text[:137] + '...'
    if isinstance(value, str) and re.match(r'^\d{4}-\d{2}-\d{2}T', value):
        return value[:16].replace('T', ' ').removesuffix(' 00:00')
    return str(value)


def diff(old, new):
    """Список змін [{field, old, new}] між двома версіями документа."""
    if not old or not new:
        return []
    changes = []
    for key in sorted(set(old) | set(new)):
        if key in IGNORED_FIELDS:
            continue
        a, b = old.get(key), new.get(key)
        if _fmt(a) != _fmt(b):
            changes.append({'field': key, 'old': _fmt(a), 'new': _fmt(b)})
    if old.get('password_hash') != new.get('password_hash') and new.get('password_hash'):
        changes.append({'field': 'password', 'old': '•••', 'new': 'змінено'})
    if len(old.get('photos') or []) != len(new.get('photos') or []):
        changes.append({'field': 'photos', 'old': str(len(old.get('photos') or [])), 'new': str(len(new.get('photos') or []))})
    return changes


def _load(db, collection, doc_id):
    try:
        if collection == 'settings':
            return db.settings.find_one({'_id': 'system'})
        return db[collection].find_one({'_id': ObjectId(doc_id)})
    except Exception:  # noqa: BLE001 - некоректний id: просто без знімка
        return None


def _current_user_id():
    """Ідентифікатор користувача з JWT (до виконання маршруту g.current_user ще не встановлено)."""
    try:
        from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
        verify_jwt_in_request(optional=True)
        return get_jwt_identity()
    except Exception:  # noqa: BLE001
        return None


def before(db):
    """Знімок запису перед зміною."""
    # дані попереднього запиту не повинні «перетекти» в цей (актуально, коли контекст застосунку спільний)
    g.pop('audit_before', None)
    g.pop('current_user', None)
    if request.method not in ('POST', 'PUT', 'DELETE') or request.endpoint not in ACTIONS:
        return
    collection, doc_id = None, None
    for arg, coll in SNAPSHOT_ARGS.items():
        if request.view_args and arg in request.view_args:
            collection, doc_id = coll, request.view_args[arg]
    if request.endpoint.startswith('settings.'):
        collection, doc_id = 'settings', 'system'
    if request.endpoint in ('auth.update_me', 'auth.change_password'):
        collection, doc_id = 'users', _current_user_id()
    g.audit_before = (collection, doc_id, _load(db, collection, doc_id) if collection and doc_id else None)


def after(db, response):
    """Запис у журнал після запиту. Помилка журналу ніколи не ламає основну відповідь."""
    try:
        if request.method not in ('POST', 'PUT', 'DELETE') or request.endpoint not in ACTIONS:
            return response
        category, action = ACTIONS[request.endpoint]
        ok = response.status_code < 400
        body = response.get_json(silent=True) if response.is_json else None
        body = body if isinstance(body, dict) else {}
        payload = request.get_json(silent=True) if request.is_json else None
        payload = payload if isinstance(payload, dict) else {}

        # хто
        user = getattr(g, 'current_user', None)
        if not user and isinstance(body.get('user'), dict) and ok:
            user = body['user']
        username = (user or {}).get('username') or payload.get('username') or None
        user_id = str((user or {}).get('_id')) if user and user.get('_id') else None

        # над чим і що змінилося
        collection, doc_id, old = getattr(g, 'audit_before', (None, None, None))
        new = _load(db, collection, doc_id) if (ok and collection and doc_id) else None
        changes = diff(old, new) if (old and new) else []
        created = next((v for v in body.values() if isinstance(v, dict) and v.get('_id')), None)
        if request.endpoint.startswith('auth.'):
            created = None
        label = entity_label(new or old, collection) or entity_label(created)
        entity_id = doc_id if doc_id and doc_id != 'system' else (str(created['_id']) if created else None)
        entity_type = ENTITY_TYPES.get(collection) or category

        db.audit_log.insert_one({
            'ts': datetime.utcnow(),
            'user_id': user_id,
            'username': username,
            'full_name': (user or {}).get('full_name'),
            'role': (user or {}).get('role'),
            'category': category,
            'action': action,
            'endpoint': request.endpoint,
            'method': request.method,
            'entity_type': entity_type,
            'entity_id': entity_id,
            'entity_label': label,
            'changes': changes,
            'status': 'success' if ok else 'fail',
            'http_status': response.status_code,
            'error': None if ok else body.get('error'),
            'ip': client_ip(),
            'agent': short_agent(request.headers.get('User-Agent')),
        })
        if not ok and category == 'login' and username:
            _check_bruteforce(db, username)
    except Exception as exc:  # noqa: BLE001
        try:
            from flask import current_app
            current_app.logger.warning('Журнал дій: не вдалося записати подію: %s', exc)
        except Exception:  # noqa: BLE001
            pass
    return response


def _check_bruteforce(db, username):
    """5 невдалих спроб входу за 15 хв -> критичне сповіщення керівнику (один раз за вікно)."""
    since = datetime.utcnow() - timedelta(minutes=SECURITY_FAIL_WINDOW_MIN)
    fails = db.audit_log.count_documents({'category': 'login', 'status': 'fail', 'username': username, 'ts': {'$gte': since}})
    if fails != SECURITY_FAIL_LIMIT:
        return
    from services.alert_engine import create_alert
    create_alert(
        db, alert_type='critical', category='security',
        title=f'Підозріла активність: вхід «{username}»',
        message=f'{fails} невдалих спроб входу для облікового запису «{username}» за {SECURITY_FAIL_WINDOW_MIN} хв. '
                f'Остання спроба з адреси {client_ip()}.',
        recipient_role='manager', related_type='audit', related_id=username,
    )


def summary(db):
    now = datetime.utcnow()
    day, week = now - timedelta(days=1), now - timedelta(days=7)
    return {
        'events_24h': db.audit_log.count_documents({'ts': {'$gte': day}}),
        'changes_7d': db.audit_log.count_documents({'ts': {'$gte': week}, 'category': {'$nin': ['login', 'logout']}, 'status': 'success'}),
        'failed_logins_24h': db.audit_log.count_documents({'ts': {'$gte': day}, 'category': 'login', 'status': 'fail'}),
        'active_users_24h': len(db.audit_log.distinct('username', {'ts': {'$gte': day}, 'status': 'success', 'username': {'$ne': None}})),
    }
