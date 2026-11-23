"""Експеримент 3. Автоматичне планування технічного обслуговування."""
from datetime import datetime, timedelta

from bson import ObjectId

from services.alert_engine import check_maintenance_alerts
from tests.conftest import login, make_vehicle, make_waybill


def complete_maintenance(app, vid):
    mech = login(app, 'mech')
    rid = mech.post('/api/repairs', json={'vehicle_id': vid, 'repair_type': 'maintenance',
                                          'description': 'Планове ТО-1'}).get_json()['repair']['_id']
    mech.put(f'/api/repairs/{rid}', json={'status': 'in_progress'})
    resp = mech.put(f'/api/repairs/{rid}', json={'status': 'completed', 'work_performed': 'ТО-1 виконано'})
    assert resp.status_code == 200


def test_next_maintenance_km_uses_settings_interval(app, db):
    db.settings.update_one({'_id': 'system'}, {'$set': {'maintenance_interval_km': 15000}})
    vid = make_vehicle(db, odometer=120000)
    complete_maintenance(app, vid)
    assert db.vehicles.find_one({'_id': ObjectId(vid)})['next_maintenance_km'] == 135000


def test_next_maintenance_date_is_rescheduled(app, db):
    vid = make_vehicle(db, next_maintenance_date=datetime.utcnow() - timedelta(days=5))
    complete_maintenance(app, vid)
    nxt = db.vehicles.find_one({'_id': ObjectId(vid)})['next_maintenance_date']
    assert isinstance(nxt, datetime) and nxt > datetime.utcnow() + timedelta(days=170)


def test_warning_and_critical_alerts(app, db):
    warn = make_vehicle(db, plate_number='WARN', odometer=104500, next_maintenance_km=105000)
    crit = make_vehicle(db, plate_number='CRIT', odometer=106000, next_maintenance_km=105000)
    ok = make_vehicle(db, plate_number='OK', odometer=90000, next_maintenance_km=105000)
    check_maintenance_alerts(db)
    assert db.alerts.find_one({'related_id': warn, 'alert_type': 'warning', 'recipient_role': 'mechanic'})
    assert db.alerts.find_one({'related_id': crit, 'alert_type': 'critical', 'recipient_role': 'manager'})
    assert db.alerts.count_documents({'related_id': ok}) == 0


def test_no_duplicate_alerts_on_repeat_check(app, db):
    make_vehicle(db, odometer=106000, next_maintenance_km=105000)
    check_maintenance_alerts(db)
    first = db.alerts.count_documents({})
    check_maintenance_alerts(db)
    assert db.alerts.count_documents({}) == first


def test_waybill_completion_triggers_immediate_check(app, db, ids):
    """Після завершення путівки, яка перетнула межу ТО, сповіщення має з'явитися одразу."""
    vid = make_vehicle(db, odometer=104000, next_maintenance_km=105000)
    wid = make_waybill(db, vid, ids['driver'], odometer_start=104000)
    resp = login(app, 'driver').put(f'/api/waybills/{wid}', json={'status': 'completed',
                                                                    'odometer_end': 105400, 'fuel_used': 400})
    assert resp.status_code == 200
    assert db.alerts.find_one({'related_id': vid, 'category': 'maintenance', 'alert_type': 'critical'})


def test_dashboard_counts_vehicles_with_due_date(app, db):
    make_vehicle(db, odometer=50000, next_maintenance_km=80000,
                 next_maintenance_date=datetime.utcnow() + timedelta(days=5))
    resp = login(app, 'admin').get('/api/reports/dashboard')
    assert resp.get_json()['dashboard']['vehicles']['maintenance_due'] == 1


def test_seeded_vehicles_counted_on_dashboard(app, db, capsys):
    """Демонстраційні дані повинні коректно враховуватися на дашборді керівника."""
    from seed import seed_database
    seed_database()
    capsys.readouterr()
    vehicles = list(db.vehicles.find({'status': 'active'}))
    assert all(isinstance(v['next_maintenance_date'], datetime) for v in vehicles)
    deadline = datetime.utcnow() + timedelta(days=14)
    expected = sum(1 for v in vehicles
                   if v['next_maintenance_km'] - v['odometer'] <= 1000 or v['next_maintenance_date'] <= deadline)
    resp = login(app, 'admin').get('/api/reports/dashboard')
    assert resp.get_json()['dashboard']['vehicles']['maintenance_due'] == expected
