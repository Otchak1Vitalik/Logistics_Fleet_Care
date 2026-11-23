"""Експеримент 7. Прогноз ТО, історія авто, склад запчастин."""
from datetime import datetime, timedelta

from bson import ObjectId

from services.alert_engine import check_maintenance_alerts
from services.maintenance_forecast import forecast
from tests.conftest import login, make_vehicle


def add_completed_waybill(db, vid, driver_id, km, days_ago):
    done = datetime.utcnow() - timedelta(days=days_ago)
    db.waybills.insert_one({'number': 'ПЛ-1', 'vehicle_id': vid, 'driver_id': driver_id, 'status': 'completed',
                            'odometer_start': 1000, 'odometer_end': 1000 + km, 'fuel_used': km * 0.3,
                            'issue_date': done, 'completed_at': done, 'created_at': done})


# --- Прогноз ТО ---
def test_forecast_formula():
    today = datetime(2026, 11, 1).date()
    v = {'odometer': 100000, 'next_maintenance_km': 103000, 'next_maintenance_date': datetime(2027, 3, 1)}
    f = forecast(v, 200, today)                      # 3000 км / 200 км/добу = 15 днів
    assert f['forecast_by_km'] == '2026-11-16' and f['expected_date'] == '2026-11-16'
    assert f['days_left'] == 15 and f['basis'] == 'mileage'
    f = forecast(v, 10, today)                       # 300 днів - раніше настане планова дата
    assert f['expected_date'] == '2027-03-01' and f['basis'] == 'date'
    assert forecast(v, None, today)['basis'] == 'date'
    assert forecast({**v, 'odometer': 104000}, 50, today)['days_left'] == 0   # уже перевищено


def test_vehicle_detail_contains_forecast(app, db, ids):
    vid = make_vehicle(db, odometer=100000, next_maintenance_km=104500,
                       next_maintenance_date=datetime.utcnow() + timedelta(days=200))
    for d in range(1, 10):                           # 9 путівок по 500 км за 90 днів -> 50 км/добу
        add_completed_waybill(db, vid, ids['driver'], 500, d * 5)
    f = login(app, 'admin').get(f'/api/vehicles/{vid}').get_json()['maintenance_forecast']
    assert f['avg_daily_km'] == 50.0 and f['days_left'] == 90 and f['basis'] == 'mileage'


def test_forecast_alert(app, db, ids):
    """ТО за пробігом ще далеко (> порога 1000 км), але за прогнозом настане раніше ніж за 14 днів."""
    vid = make_vehicle(db, odometer=100000, next_maintenance_km=103000,
                       next_maintenance_date=datetime.utcnow() + timedelta(days=200))
    for d in range(1, 31):                           # 30 путівок по 900 км -> 300 км/добу -> 10 днів
        add_completed_waybill(db, vid, ids['driver'], 900, d * 2)
    check_maintenance_alerts(db)
    alert = db.alerts.find_one({'related_id': vid, 'category': 'maintenance'})
    assert alert and alert['alert_type'] == 'warning' and 'за прогнозом' in alert['message']


# --- Історія авто ---
def test_vehicle_history_timeline_and_totals(app, db, ids):
    vid = make_vehicle(db)
    add_completed_waybill(db, vid, ids['driver'], 400, 3)
    db.fault_reports.insert_one({'number': 'НС-1', 'vehicle_id': vid, 'reported_by': ids['driver'], 'status': 'new',
                                 'description': 'Скрип гальм', 'severity': 'high', 'report_date': datetime.utcnow()})
    db.repairs.insert_one({'number': 'РМ-1', 'vehicle_id': vid, 'status': 'completed', 'repair_type': 'repair',
                           'description': 'Колодки', 'labor_cost': 1000, 'parts_cost': 3200,
                           'completed_at': datetime.utcnow() - timedelta(days=1)})
    db.fuel_records.insert_one({'vehicle_id': vid, 'record_type': 'external', 'quantity': 100,
                                'total_amount': 5300, 'date': datetime.utcnow() - timedelta(days=2)})
    data = login(app, 'mech').get(f'/api/vehicles/{vid}/history').get_json()
    assert [e['type'] for e in data['timeline']] == ['fault', 'repair', 'fuel', 'waybill']
    t = data['totals']
    assert t['distance'] == 400 and t['repairs_cost'] == 4200 and t['fuel_cost'] == 5300 and t['open_faults'] == 1


# --- Склад запчастин ---
def make_part(app, **kw):
    body = {'name': 'Колодки гальмівні', 'unit': 'компл.', 'quantity': 5, 'min_quantity': 2, 'price': 3000, **kw}
    resp = login(app, 'admin').post('/api/parts', json=body)
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()['part']['_id']


def start_repair(app, vid):
    mech = login(app, 'mech')
    rid = mech.post('/api/repairs', json={'vehicle_id': vid, 'repair_type': 'repair',
                                          'description': 'Заміна колодок'}).get_json()['repair']['_id']
    mech.put(f'/api/repairs/{rid}', json={'status': 'in_progress'})
    return mech, rid


def test_parts_consumed_on_repair_completion(app, db):
    pid = make_part(app)
    mech, rid = start_repair(app, make_vehicle(db))
    resp = mech.put(f'/api/repairs/{rid}', json={'status': 'completed', 'work_performed': 'Замінено колодки',
                                                 'labor_hours': None, 'labor_cost': 800, 'parts_cost': None,
                                                 'parts_used': [{'part_id': pid, 'quantity': 3}]})
    assert resp.status_code == 200, resp.get_json()
    repair = db.repairs.find_one({'_id': ObjectId(rid)})
    assert repair['parts_cost'] == 9000 and repair['parts_used'][0]['name'] == 'Колодки гальмівні'
    assert db.parts.find_one({'_id': ObjectId(pid)})['quantity'] == 2
    # залишок досяг мінімуму -> попередження механікам і керівнику
    assert db.alerts.count_documents({'related_type': 'part', 'related_id': pid}) == 2
    assert db.part_movements.count_documents({'part_id': pid, 'type': 'out', 'repair_id': rid}) == 1


def test_insufficient_stock_rejected_without_changes(app, db):
    pid = make_part(app, quantity=1)
    mech, rid = start_repair(app, make_vehicle(db))
    resp = mech.put(f'/api/repairs/{rid}', json={'status': 'completed', 'work_performed': 'Готово',
                                                 'parts_used': [{'part_id': pid, 'quantity': 2}]})
    assert resp.status_code == 400 and 'Недостатньо' in resp.get_json()['error']
    assert db.parts.find_one({'_id': ObjectId(pid)})['quantity'] == 1
    assert db.repairs.find_one({'_id': ObjectId(rid)})['status'] == 'in_progress'


def test_receive_stock_clears_low_alert(app, db):
    pid = make_part(app, quantity=1)                 # одразу нижче мінімуму -> попередження
    assert db.alerts.count_documents({'related_id': pid, 'is_dismissed': False}) == 2
    resp = login(app, 'mech').post(f'/api/parts/{pid}/receive', json={'quantity': 10, 'price': 3100})
    assert resp.status_code == 200
    part = db.parts.find_one({'_id': ObjectId(pid)})
    assert part['quantity'] == 11 and part['price'] == 3100
    assert db.alerts.count_documents({'related_id': pid, 'is_dismissed': False}) == 0


def test_driver_has_no_access_to_parts(app, db):
    assert login(app, 'driver').get('/api/parts').status_code == 403
