"""
Спільні фікстури для автоматизованих тестів АСУ ТО.
Тести працюють з окремою тестовою базою MongoDB (krutii_test),
яка очищується перед кожним тестом.
"""
import os
import sys
from datetime import datetime, timedelta

import bcrypt
import pytest

os.environ.setdefault('MONGO_URI', 'mongodb://localhost:27017/krutii_test')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config  # noqa: E402

Config.RATELIMIT_ENABLED = False
Config.MONGO_URI = os.environ['MONGO_URI']

from app import create_app  # noqa: E402
from extensions import mongo, scheduler  # noqa: E402

PASSWORDS = {'admin': 'Admin1234', 'mech': 'Mech1234', 'mech2': 'Mech1234',
             'driver': 'Driver1234', 'driver2': 'Driver1234'}
ROLES = {'admin': 'manager', 'mech': 'mechanic', 'mech2': 'mechanic',
         'driver': 'driver', 'driver2': 'driver'}


@pytest.fixture(scope='session')
def app():
    application = create_app()
    application.config['TESTING'] = True
    # Фонові задачі в тестах викликаються явно, тому планувальник зупиняємо
    scheduler.remove_all_jobs()
    return application


@pytest.fixture()
def db(app):
    with app.app_context():
        database = mongo.db
        for name in database.list_collection_names():
            database[name].delete_many({})
        database.settings.insert_one({
            '_id': 'system', 'default_fuel_norm': 25.0, 'overspend_threshold': 10,
            'winter_coefficient': 1.09, 'maintenance_warning_km': 1000,
            'maintenance_warning_days': 14, 'maintenance_interval_km': 10000,
            'maintenance_interval_days': 180,
            'fault_mechanic_hours': 4, 'fault_manager_hours': 24,
        })
        ids = {}
        for username, role in ROLES.items():
            res = database.users.insert_one({
                'username': username, 'full_name': f'Тест {username}', 'role': role,
                'password_hash': bcrypt.hashpw(PASSWORDS[username].encode(), bcrypt.gensalt(4)).decode(),
                'is_active': True, 'created_at': datetime.utcnow(),
            })
            ids[username] = str(res.inserted_id)
        database.test_ids = ids
        yield database


@pytest.fixture()
def ids(db):
    return db.test_ids


def make_vehicle(db, **overrides):
    doc = {
        'plate_number': 'BC0001AA', 'brand': 'MAN', 'model': 'TGX', 'year': 2020,
        'status': 'active', 'fuel_type': 'diesel', 'fuel_norm': 28.0,
        'odometer': 100000, 'last_maintenance_km': 95000,
        'next_maintenance_km': 105000,
        'next_maintenance_date': datetime.utcnow() + timedelta(days=60),
        'created_at': datetime.utcnow(), 'updated_at': datetime.utcnow(),
    }
    doc.update(overrides)
    return str(db.vehicles.insert_one(doc).inserted_id)


def make_waybill(db, vehicle_id, driver_id, status='active', odometer_start=100000):
    now = datetime.utcnow()
    return str(db.waybills.insert_one({
        'number': 'ПЛ-000001', 'vehicle_id': vehicle_id, 'driver_id': driver_id,
        'issue_date': now, 'valid_from': now, 'valid_until': now + timedelta(days=1),
        'odometer_start': odometer_start, 'odometer_end': None, 'fuel_issued': 100,
        'fuel_used': None, 'status': status, 'created_at': now, 'updated_at': now,
    }).inserted_id)


def login(app, username):
    client = app.test_client()
    resp = client.post('/api/auth/login', json={'username': username, 'password': PASSWORDS[username]})
    assert resp.status_code == 200, resp.get_json()
    return client
