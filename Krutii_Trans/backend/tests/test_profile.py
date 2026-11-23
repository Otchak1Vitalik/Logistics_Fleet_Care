"""Експеримент 8. Сторінка «Мій профіль»."""
from datetime import datetime, timedelta

from tests.conftest import login, make_vehicle


def test_profile_contains_role_stats(app, db, ids):
    vid = make_vehicle(db)
    done = datetime.utcnow() - timedelta(days=2)
    db.waybills.insert_one({'vehicle_id': vid, 'driver_id': ids['driver'], 'status': 'completed', 'odometer_start': 1000,
                            'odometer_end': 1450, 'fuel_used': 130, 'completed_at': done})
    db.users.update_one({'username': 'driver'}, {'$set': {'license_number': 'АВС123456',
                                                           'license_expiry': datetime.utcnow() + timedelta(days=10)}})
    profile = login(app, 'driver').get('/api/auth/me').get_json()['profile']
    assert profile['stats']['waybills'] == 1 and profile['stats']['distance'] == 450
    assert profile['license_warning'] is True and profile['license_days_left'] in (9, 10)

    started = datetime.utcnow() - timedelta(hours=30)
    db.repairs.insert_one({'mechanic_id': ids['mech'], 'status': 'completed', 'started_at': started,
                           'completed_at': started + timedelta(hours=6)})
    stats = login(app, 'mech').get('/api/auth/me').get_json()['profile']['stats']
    assert stats['repairs_completed'] == 1 and stats['avg_repair_hours'] == 6.0
    assert 'vehicles_total' in login(app, 'admin').get('/api/auth/me').get_json()['profile']['stats']


def test_update_own_contacts(app, db):
    client = login(app, 'driver')
    resp = client.put('/api/auth/me', json={'phone': '+380 67 123 45 67', 'email': 'driver@example.com'})
    assert resp.status_code == 200
    user = db.users.find_one({'username': 'driver'})
    assert user['phone'] == '+380 67 123 45 67' and user['email'] == 'driver@example.com'
    # роль і ПІБ через профіль змінити не можна
    client.put('/api/auth/me', json={'role': 'manager', 'full_name': 'Хакер', 'email': ''})
    user = db.users.find_one({'username': 'driver'})
    assert user['role'] == 'driver' and user['full_name'] != 'Хакер' and user['email'] is None


def test_update_contacts_validation(app, db):
    client = login(app, 'driver')
    assert client.put('/api/auth/me', json={'email': 'not-an-email'}).status_code == 400
    assert client.put('/api/auth/me', json={'phone': 'abc'}).status_code == 400
    assert app.test_client().put('/api/auth/me', json={'phone': '+380671234567'}).status_code == 401
