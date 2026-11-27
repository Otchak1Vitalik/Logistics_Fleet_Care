"""Журнал дій: автоматичний запис змін «було -> стало», невдалі входи, захист від перебору паролів."""
from tests.conftest import PASSWORDS, login, make_vehicle


def last(db, **query):
    return db.audit_log.find_one(query, sort=[('ts', -1)])


def test_vehicle_change_is_logged_with_diff(app, db, ids):
    vid = make_vehicle(db, plate_number='BC7777AA', status='active', fuel_norm=28.0)
    client = login(app, 'admin')
    r = client.put(f'/api/vehicles/{vid}', json={'status': 'repair', 'fuel_norm': 30.5})
    assert r.status_code == 200, r.get_json()
    entry = last(db, endpoint='vehicles.update_vehicle')
    assert entry['username'] == 'admin' and entry['role'] == 'manager' and entry['status'] == 'success'
    assert entry['action'] == 'Зміна автомобіля' and entry['entity_id'] == vid
    assert entry['entity_label'].startswith('BC7777AA')
    changes = {c['field']: (c['old'], c['new']) for c in entry['changes']}
    assert changes['status'] == ('active', 'repair')
    assert changes['fuel_norm'] == ('28.0', '30.5')
    assert 'updated_at' not in changes and entry['ip']


def test_settings_change_is_logged(app, db, ids):
    client = login(app, 'admin')
    assert client.put('/api/settings', json={'maintenance_interval_km': 15000}).status_code == 200
    entry = last(db, endpoint='settings.update_settings')
    assert entry['entity_label'] == 'Налаштування системи'
    assert {'field': 'maintenance_interval_km', 'old': '10000', 'new': '15000'} in entry['changes']


def test_failed_login_logged_without_password(app, db, ids):
    client = app.test_client()
    r = client.post('/api/auth/login', json={'username': 'driver', 'password': 'WrongPass99'})
    assert r.status_code == 401
    entry = last(db, endpoint='auth.login')
    assert entry['status'] == 'fail' and entry['username'] == 'driver' and entry['category'] == 'login'
    assert 'WrongPass99' not in str(entry)               # пароль ніколи не потрапляє в журнал
    ok = client.post('/api/auth/login', json={'username': 'driver', 'password': PASSWORDS['driver']})
    assert ok.status_code == 200
    assert last(db, endpoint='auth.login')['status'] == 'success'


def test_bruteforce_creates_single_security_alert(app, db, ids):
    client = app.test_client()
    for _ in range(7):
        client.post('/api/auth/login', json={'username': 'admin', 'password': 'nope'})
    alerts = list(db.alerts.find({'category': 'security'}))
    assert len(alerts) == 1                                # одне сповіщення, без дублів
    assert alerts[0]['recipient_role'] == 'manager' and alerts[0]['alert_type'] == 'critical'
    assert 'admin' in alerts[0]['title']


def test_password_change_shows_masked_change(app, db, ids):
    client = login(app, 'mech')
    r = client.post('/api/auth/change-password', json={'current_password': PASSWORDS['mech'], 'new_password': 'NewMech12345'})
    assert r.status_code == 200, r.get_json()
    entry = last(db, endpoint='auth.change_password')
    assert entry['username'] == 'mech' and entry['category'] == 'security'
    assert {'field': 'password', 'old': '•••', 'new': 'змінено'} in entry['changes']
    assert 'password_hash' not in str(entry['changes'])


def test_audit_api_manager_only_and_filters(app, db, ids):
    app.test_client().post('/api/auth/login', json={'username': 'driver', 'password': 'bad'})
    assert login(app, 'driver').get('/api/audit').status_code == 403
    client = login(app, 'admin')
    r = client.get('/api/audit?category=login&status=fail')
    body = r.get_json()
    assert r.status_code == 200 and body['total'] == 1
    assert body['items'][0]['username'] == 'driver' and body['summary']['failed_logins_24h'] == 1
    assert 'admin' in body['users'] and 'login' in body['categories']
    # журнал не можна змінити чи видалити
    assert client.delete('/api/audit').status_code == 405
    assert client.put('/api/audit').status_code == 405


def test_read_only_requests_not_logged(app, db, ids):
    client = login(app, 'admin')
    before = db.audit_log.count_documents({})
    client.get('/api/vehicles')
    client.get('/api/reports/dashboard')
    assert db.audit_log.count_documents({}) == before
