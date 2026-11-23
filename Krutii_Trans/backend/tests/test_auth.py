"""Експеримент 1. Автентифікація та рольове розмежування доступу."""
from tests.conftest import login, PASSWORDS


def test_login_success(app, db):
    client = app.test_client()
    resp = client.post('/api/auth/login', json={'username': 'admin', 'password': PASSWORDS['admin']})
    assert resp.status_code == 200
    assert 'access_token_cookie' in resp.headers.get('Set-Cookie', '')


def test_login_wrong_password(app, db):
    resp = app.test_client().post('/api/auth/login', json={'username': 'admin', 'password': 'wrong'})
    assert resp.status_code == 401


def test_request_without_token_rejected(app, db):
    assert app.test_client().get('/api/vehicles').status_code == 401


def test_driver_cannot_access_repairs(app, db):
    assert login(app, 'driver').get('/api/repairs').status_code == 403


def test_driver_cannot_change_settings(app, db):
    assert login(app, 'driver').put('/api/settings', json={'overspend_threshold': 20}).status_code == 403


def test_mechanic_can_see_pending_faults(app, db):
    assert login(app, 'mech').get('/api/faults/pending').status_code == 200


def test_deactivated_user_loses_access(app, db, ids):
    client = login(app, 'driver')
    db.users.update_one({'username': 'driver'}, {'$set': {'is_active': False}})
    assert client.get('/api/auth/me').status_code == 403


def test_fault_photo_requires_auth(app, db):
    """Фото несправностей не повинні бути доступні без автентифікації."""
    resp = app.test_client().get('/api/faults/uploads/any.jpg')
    assert resp.status_code == 401
