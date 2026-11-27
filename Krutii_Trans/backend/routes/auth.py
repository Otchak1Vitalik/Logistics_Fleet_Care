"""
Маршрути автентифікації
"""
from datetime import datetime
from flask import Blueprint, request, jsonify, g, current_app
from flask_jwt_extended import create_access_token, unset_jwt_cookies, set_access_cookies
import bcrypt
from bson import ObjectId
from marshmallow import ValidationError

from extensions import mongo, limiter
from middleware.auth_middleware import require_auth
from models.user import UserSchema, PasswordChangeSchema, ProfileUpdateSchema
from services.profile import build_profile
from services.login_codes import create_code, check_code, seconds_until_resend, mask_email
from services.mailer import send_login_code

auth_bp = Blueprint('auth', __name__)
user_schema = UserSchema()
password_schema = PasswordChangeSchema()
profile_schema = ProfileUpdateSchema()


@auth_bp.route('/login', methods=['POST'])
@limiter.limit("10/minute")
def login():
    """
    Вхід в систему.
    Повертає JWT токен у httpOnly cookie.
    """
    data = request.get_json()

    if not data:
        return jsonify({
            'success': False,
            'error': 'Не надано даних для входу.'
        }), 400

    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({
            'success': False,
            'error': 'Введіть логін та пароль.'
        }), 400

    # Пошук користувача
    user = mongo.db.users.find_one({'username': username})

    if not user:
        return jsonify({
            'success': False,
            'error': 'Невірний логін або пароль.'
        }), 401

    # Перевірка пароля
    if not bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
        return jsonify({
            'success': False,
            'error': 'Невірний логін або пароль.'
        }), 401

    # Перевірка активності
    if not user.get('is_active', True):
        return jsonify({
            'success': False,
            'error': 'Обліковий запис деактивовано. Зверніться до адміністратора.'
        }), 403

    return _login_response(user)


def _login_response(user):
    """Спільне завершення входу: час входу, JWT у httpOnly cookie, дані користувача."""
    mongo.db.users.update_one(
        {'_id': user['_id']},
        {'$set': {'last_login': datetime.utcnow()}}
    )
    access_token = create_access_token(identity=str(user['_id']))
    response = jsonify({
        'success': True,
        'message': 'Вхід виконано успішно.',
        'user': user_schema.dump(user)
    })
    set_access_cookies(response, access_token)
    return response


# ---------------- Вхід за кодом з пошти ----------------
CODE_UNAVAILABLE = ('Неможливо надіслати код: перевірте логін або попросіть керівника '
                    'додати email до вашого облікового запису.')


@auth_bp.route('/email-code/request', methods=['POST'])
@limiter.limit("5/minute")
def email_code_request():
    """Крок 1: надсилає 4-значний код на email користувача."""
    data = request.get_json() or {}
    username = (data.get('username') or '').strip()
    lang = 'en' if data.get('lang') == 'en' else 'uk'
    if not username:
        return jsonify({'success': False, 'error': 'Введіть логін.'}), 400

    user = mongo.db.users.find_one({'username': username})
    # Одне повідомлення для «немає користувача» і «немає email», щоб не підказувати, які логіни існують
    if not user or not user.get('email') or not user.get('is_active', True):
        return jsonify({'success': False, 'error': CODE_UNAVAILABLE}), 400

    wait = seconds_until_resend(mongo.db, user['_id'])
    if wait > 0:
        return jsonify({'success': False, 'error': 'Повторно надіслати код можна через {0} с.'.replace('{0}', str(wait)),
                        'retry_after': wait}), 429

    code = create_code(mongo.db, user['_id'])
    try:
        mode = send_login_code(user['email'], user.get('full_name') or username, code, lang)
    except Exception as exc:  # noqa: BLE001 - помилка SMTP не повинна «валити» сервер
        mongo.db.login_codes.delete_one({'user_id': str(user['_id'])})
        current_app.logger.error('Не вдалося надіслати лист: %s', exc)
        return jsonify({'success': False, 'error': 'Не вдалося надіслати лист. Спробуйте пізніше або увійдіть за паролем.'}), 502

    return jsonify({
        'success': True,
        'message': 'Код надіслано на пошту.',
        'email': mask_email(user['email']),
        'mode': mode,  # 'sent' - лист надіслано, 'demo' - код у консолі сервера
        'expires_in': current_app.config['LOGIN_CODE_TTL_MINUTES'] * 60,
        'resend_in': current_app.config['LOGIN_CODE_RESEND_SECONDS'],
        'length': 4,
    })


@auth_bp.route('/email-code/verify', methods=['POST'])
@limiter.limit("20/minute")
def email_code_verify():
    """Крок 2: перевіряє код і виконує вхід."""
    data = request.get_json() or {}
    username = (data.get('username') or '').strip()
    code = str(data.get('code') or '').strip()
    if not username or not code.isdigit() or len(code) != 4:
        return jsonify({'success': False, 'error': 'Введіть 4 цифри коду.'}), 400

    user = mongo.db.users.find_one({'username': username})
    if not user or not user.get('is_active', True):
        return jsonify({'success': False, 'error': 'Невірний код.', 'attempts_left': 0}), 400

    ok, reason, left = check_code(mongo.db, user['_id'], code)
    if ok:
        return _login_response(user)
    errors = {
        'wrong': ('Невірний код. Залишилось спроб: {0}.'.replace('{0}', str(left)), 400),
        'locked': ('Забагато невдалих спроб. Надішліть новий код.', 429),
        'expired': ('Термін дії коду минув. Надішліть новий код.', 410),
        'missing': ('Код не знайдено. Надішліть новий код.', 404),
    }
    message, status = errors[reason]
    return jsonify({'success': False, 'error': message, 'reason': reason, 'attempts_left': left}), status


@auth_bp.route('/logout', methods=['POST'])
def logout():
    """
    Вихід з системи.
    Видаляє JWT cookie.
    """
    response = jsonify({
        'success': True,
        'message': 'Вихід виконано успішно.'
    })
    unset_jwt_cookies(response)
    return response


@auth_bp.route('/me', methods=['GET'])
@require_auth
def me():
    """
    Отримання даних поточного користувача.
    """
    return jsonify({
        'success': True,
        'user': user_schema.dump(g.current_user),
        # Статистика для сторінки «Мій профіль» (залежить від ролі)
        'profile': build_profile(mongo.db, g.current_user)
    })


@auth_bp.route('/me', methods=['PUT'])
@require_auth
def update_me():
    """
    Зміна власних контактів (телефон, email).
    ПІБ, роль і дані посвідчення змінює лише керівник.
    """
    raw = request.get_json() or {}
    payload = {k: (raw[k].strip() or None) if isinstance(raw.get(k), str) else raw.get(k)
               for k in ('phone', 'email') if k in raw}
    try:
        data = profile_schema.load(payload)
    except ValidationError as err:
        return jsonify({
            'success': False,
            'error': 'Помилка валідації.',
            'details': err.messages
        }), 400

    if not data:
        return jsonify({'success': False, 'error': 'Немає даних для оновлення.'}), 400

    data['updated_at'] = datetime.utcnow()
    mongo.db.users.update_one({'_id': ObjectId(g.current_user['_id'])}, {'$set': data})
    user = mongo.db.users.find_one({'_id': ObjectId(g.current_user['_id'])})
    return jsonify({
        'success': True,
        'message': 'Контакти оновлено.',
        'user': user_schema.dump(user)
    })


@auth_bp.route('/change-password', methods=['POST'])
@require_auth
def change_password():
    """
    Зміна пароля поточного користувача.
    """
    try:
        data = password_schema.load(request.get_json())
    except ValidationError as err:
        return jsonify({
            'success': False,
            'error': 'Помилка валідації.',
            'details': err.messages
        }), 400

    # Отримання поточного користувача з БД (потрібен хеш пароля)
    user = mongo.db.users.find_one({'_id': ObjectId(g.current_user['_id'])})

    # Перевірка поточного пароля
    if not bcrypt.checkpw(
        data['current_password'].encode('utf-8'),
        user['password_hash'].encode('utf-8')
    ):
        return jsonify({
            'success': False,
            'error': 'Поточний пароль невірний.'
        }), 400

    # Хешування нового пароля
    new_hash = bcrypt.hashpw(
        data['new_password'].encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')

    # Оновлення пароля
    mongo.db.users.update_one(
        {'_id': user['_id']},
        {
            '$set': {
                'password_hash': new_hash,
                'updated_at': datetime.utcnow()
            }
        }
    )

    return jsonify({
        'success': True,
        'message': 'Пароль успішно змінено.'
    })
