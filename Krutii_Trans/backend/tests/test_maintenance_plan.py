"""Оптимізація графіка ТО: обмеження, порівняння з наївним планом, затвердження."""
from datetime import datetime, timedelta

from bson import ObjectId

from services import maintenance_optimizer as mo
from services import predictive_maintenance as pm
from tests.conftest import login, make_vehicle


def _fleet(db, n=8, due_in=None):
    ids = []
    now = datetime.utcnow()
    for i in range(n):
        days = due_in[i] if due_in else 2 + i * 2
        ids.append(make_vehicle(db, plate_number=f'BC{i:04d}MP', year=2016 + i % 6, odometer=100000,
                                fuel_norm=28.0 if i % 2 else 11.0, next_maintenance_km=150000,
                                next_maintenance_date=now + timedelta(days=days)))
    return ids


def _risk(monkeypatch, values):
    """Підміняємо ML-прогноз заданими ймовірностями (тестуємо саме оптимізацію)."""
    monkeypatch.setattr(pm, 'fleet_risk', lambda db, vehicle_id=None: {'items': [
        {'vehicle_id': k, 'probability': v, 'level': 'high' if v >= 0.25 else 'low'} for k, v in values.items()]})


def test_capacity_days_off_and_trips(app, db, ids, monkeypatch):
    vids = _fleet(db, 8, due_in=[1] * 8)                 # усім ТО потрібне майже одночасно
    _risk(monkeypatch, {v: 0.05 for v in vids})
    now = datetime.utcnow()
    start = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    db.waybills.insert_one({'number': 'ПЛ-777777', 'vehicle_id': vids[0], 'driver_id': ids['driver'], 'status': 'issued',
                            'valid_from': start, 'valid_until': start + timedelta(days=3, hours=12)})
    plan = mo.optimize(db, bays=2, horizon_days=14, now=now)
    days = plan['days']
    assert all(d['load'] <= d['capacity'] for d in days)
    assert all(d['capacity'] == 0 for d in days if datetime.fromisoformat(str(d['date'])).weekday() == 6) \
        if isinstance(days[0]['date'], str) else all(d['capacity'] == 0 for d in days if d['date'].weekday() == 6)
    first = next(i for i in plan['items'] if i['vehicle_id'] == vids[0])
    assert first['day'] is not None and first['day'] >= 4 and 'ПЛ-777777' in first['trips']   # не в дні рейсу
    assert plan['optimized']['scheduled'] == 8


def test_risky_vehicle_goes_first(app, db, monkeypatch):
    vids = _fleet(db, 4, due_in=[10, 10, 10, 10])
    _risk(monkeypatch, {vids[0]: 0.02, vids[1]: 0.02, vids[2]: 0.6, vids[3]: 0.02})
    plan = mo.optimize(db, bays=1, horizon_days=21)
    by = {i['vehicle_id']: i for i in plan['items']}
    assert by[vids[2]]['day'] < min(by[v]['day'] for v in (vids[0], vids[1], vids[3]))
    assert by[vids[2]]['day'] <= 1
    # низькоризикові - не надто рано (без зайвого «недовикористаного» ресурсу)
    assert all(by[v]['day'] >= 6 for v in (vids[0], vids[1], vids[3]))
    assert plan['optimized']['cost'] <= plan['naive']['cost']
    assert plan['optimized']['expected_failures'] < plan['naive']['expected_failures']


def test_optimal_not_worse_than_naive(app, db, monkeypatch):
    vids = _fleet(db, 10)
    _risk(monkeypatch, {v: 0.03 + 0.05 * k for k, v in enumerate(vids)})
    for bays in (1, 2, 3):
        plan = mo.optimize(db, bays=bays, horizon_days=21)
        # оптимальний розв'язок задачі про призначення не гірший за будь-який допустимий план, зокрема наївний
        assert plan['optimized']['cost'] <= plan['naive']['cost']
        assert plan['optimized']['scheduled'] >= plan['naive']['scheduled'] - 1


def test_api_plan_and_apply(app, db, ids):
    vids = _fleet(db, 5)
    db.vehicles.update_one({'_id': ObjectId(vids[4])}, {'$set': {'status': 'repair'}})   # у ремонті - не плануємо
    assert login(app, 'mech').get('/api/maintenance-plan').status_code == 403
    admin = login(app, 'admin')
    r = admin.get('/api/maintenance-plan?horizon=14&bays=2').get_json()
    assert r['success'] and r['params']['horizon_days'] == 14 and r['params']['bays'] == 2
    planned = [i for i in r['items'] if i['date']]
    assert planned and vids[4] not in {i['vehicle_id'] for i in r['items']}
    assert admin.post('/api/maintenance-plan/apply', json={'items': []}).status_code == 400
    res = admin.post('/api/maintenance-plan/apply', json={'items': [{'vehicle_id': i['vehicle_id'], 'date': i['date']} for i in planned]})
    assert res.status_code == 201
    created = res.get_json()['created']
    assert len(created) == len(planned)
    rep = db.repairs.find_one({'_id': ObjectId(created[0]['repair_id'])})
    assert rep['repair_type'] == 'maintenance' and rep['status'] == 'planned' and rep['mechanic_id'] in (ids['mech'], ids['mech2'])
    # повторно ті самі авто не плануються, а в новому плані вони - як уже заплановані
    assert admin.post('/api/maintenance-plan/apply', json={'items': [{'vehicle_id': planned[0]['vehicle_id'], 'date': planned[0]['date']}]}).status_code == 400
    r2 = admin.get('/api/maintenance-plan?horizon=14&bays=2').get_json()
    assert len(r2['fixed']) == len(planned)
    assert db.audit_log.count_documents({'endpoint': 'maintenance_plan.apply', 'status': 'success'}) == 1
