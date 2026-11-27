"""Виявлення аномалій у витраті пального: методи, перевірки заправок, рішення керівника, оцінка."""
import random
from datetime import datetime, timedelta

from bson import ObjectId

from services.fuel_anomalies import robust_z, run_detection, evaluate
from tests.conftest import login, make_vehicle


def _trips(db, vid, driver_id, n=30, overspend=(), seed=1):
    """n завершених рейсів по 300 км; рейси з індексами з overspend мають витрату +40 %."""
    rnd = random.Random(seed)
    now = datetime.utcnow()
    ids = []
    for i in range(n):
        ratio = rnd.uniform(0.93, 0.99) * (1.4 if i in overspend else 1.0)
        done = now - timedelta(days=n - i)
        ids.append(str(db.waybills.insert_one({
            'number': f'ПЛ-{i:06d}', 'vehicle_id': vid, 'driver_id': driver_id, 'status': 'completed',
            'odometer_start': 100000 + i * 300, 'odometer_end': 100300 + i * 300,
            'fuel_used': round(300 / 100 * 25.0 * ratio, 1), 'completed_at': done,
            'demo_anomaly': 'overspend' if i in overspend else None,
            'created_at': done, 'updated_at': done,
        }).inserted_id))
    return ids


def test_robust_z():
    z, med = robust_z(1.5, [1.0, 1.01, 0.99, 1.02, 0.98, 1.0])
    assert med == 1.0 and z > 3.5
    z, _ = robust_z(1.0, [1.0, 1.01, 0.99, 1.02, 0.98, 1.0])
    assert abs(z) < 0.1


def test_detection_finds_overspend(app, db, ids):
    db.settings.update_one({'_id': 'system'}, {'$set': {'winter_coefficient': 1.0}})
    vid = make_vehicle(db, fuel_norm=25.0, tank_capacity=400)
    wids = _trips(db, vid, ids['driver'], overspend={10, 20})
    res = run_detection(db, notify=True)
    assert res['trips_checked'] == 30
    found = {d['source_id']: d for d in db.fuel_anomalies.find({'kind': 'trip_overspend'})}
    for i in (10, 20):
        d = found[wids[i]]
        assert {'rule', 'stat'} <= set(d['methods'])
        assert d['level'] == 'high' and d['status'] == 'new' and d['reasons']
        assert d['metrics']['excess_l'] > 0 and d['metrics']['cost'] > 0
    # нормальні рейси правилом і статистикою не позначаються
    assert all(not ({'rule', 'stat'} & set(d['methods'])) for s, d in found.items() if s not in (wids[10], wids[20]))
    # два нові випадки з високим ризиком -> одне зведене сповіщення керівнику
    assert db.alerts.count_documents({'category': 'fuel', 'recipient_role': 'manager'}) == 1


def test_refuel_checks(app, db, ids):
    vid = make_vehicle(db, tank_capacity=300)
    now = datetime.utcnow()
    base = {'vehicle_id': vid, 'driver_id': ids['driver'], 'fuel_type': 'diesel', 'type': 'station'}
    for days, price in ((40, 54.0), (35, 54.5), (30, 53.8)):
        db.fuel_records.insert_one({**base, 'date': now - timedelta(days=days), 'quantity': 150,
                                    'price_per_liter': price, 'odometer': 100000 + days * 10})
    over = db.fuel_records.insert_one({**base, 'date': now - timedelta(days=20), 'quantity': 380,
                                       'price_per_liter': 54.0, 'odometer': 101000}).inserted_id
    first = now - timedelta(days=10)
    db.fuel_records.insert_one({**base, 'date': first, 'quantity': 200, 'price_per_liter': 54.0, 'odometer': 102000})
    double = db.fuel_records.insert_one({**base, 'date': first + timedelta(hours=5), 'quantity': 180,
                                         'price_per_liter': 54.2, 'odometer': 102040}).inserted_id
    pricey = db.fuel_records.insert_one({**base, 'date': now - timedelta(days=3), 'quantity': 100,
                                         'price_per_liter': 70.0, 'odometer': 104000}).inserted_id
    run_detection(db, notify=False)
    kinds = {(d['kind'], d['source_id']) for d in db.fuel_anomalies.find()}
    assert ('over_tank', str(over)) in kinds
    assert ('double_refuel', str(double)) in kinds
    assert ('price', str(pricey)) in kinds
    assert len(kinds) == 3


def test_api_review_keeps_decision(app, db, ids):
    db.settings.update_one({'_id': 'system'}, {'$set': {'winter_coefficient': 1.0}})
    vid = make_vehicle(db, fuel_norm=25.0, tank_capacity=400)
    wids = _trips(db, vid, ids['driver'], overspend={15})
    client = login(app, 'admin')
    assert client.post('/api/fuel/anomalies/run').status_code == 200
    r = client.get('/api/fuel/anomalies')
    body = r.get_json()
    assert body['summary']['new'] >= 1
    assert all('demo_label' not in d for d in body['items'])           # прихована мітка не віддається
    item = next(d for d in body['items'] if d['source_id'] == wids[15])

    assert client.put(f"/api/fuel/anomalies/{item['_id']}", json={'status': 'bad'}).status_code == 400
    assert client.put(f'/api/fuel/anomalies/{ObjectId()}', json={'status': 'confirmed'}).status_code == 404
    r = client.put(f"/api/fuel/anomalies/{item['_id']}", json={'status': 'confirmed', 'comment': 'Злив пального'})
    assert r.status_code == 200
    a = r.get_json()['anomaly']
    assert a['status'] == 'confirmed' and a['review']['comment'] == 'Злив пального'
    assert a['review']['by_name'] == 'Тест admin'
    # повторна перевірка не скидає рішення керівника
    client.post('/api/fuel/anomalies/run')
    assert db.fuel_anomalies.find_one({'_id': ObjectId(item['_id'])})['status'] == 'confirmed'
    # рішення потрапило в журнал дій
    assert db.audit_log.count_documents({'endpoint': 'fuel_anomalies.review', 'status': 'success'}) == 1


def test_api_access_and_evaluation(app, db, ids):
    vid = make_vehicle(db, fuel_norm=25.0, tank_capacity=400)
    _trips(db, vid, ids['driver'], overspend={5, 12, 22})
    for user in ('driver', 'mech'):
        assert login(app, user).get('/api/fuel/anomalies').status_code == 403
    assert app.test_client().get('/api/fuel/anomalies').status_code == 401
    client = login(app, 'admin')
    ev = client.get('/api/fuel/anomalies/evaluation').get_json()['evaluation']
    assert ev['source'] == 'demo' and ev['labeled'] == 30 and ev['positives'] == 3
    methods = {m['key']: m for m in ev['methods']}
    assert set(methods) == {'rule', 'stat', 'ml', 'any', 'vote'}
    assert methods['rule']['recall'] == 1.0 and methods['any']['recall'] == 1.0
    assert len(ev['rule_thresholds']) == 6
    hist = client.get(f'/api/fuel/anomalies/vehicle/{vid}').get_json()['history']
    assert len(hist['points']) == 30 and 80 < hist['typical_pct'] < 100


def test_completing_waybill_triggers_check(app, db, ids):
    db.settings.update_one({'_id': 'system'}, {'$set': {'winter_coefficient': 1.0}})
    vid = make_vehicle(db, fuel_norm=25.0, tank_capacity=400, odometer=200000)
    _trips(db, vid, ids['driver'])
    now = datetime.utcnow()
    wid = db.waybills.insert_one({
        'number': 'ПЛ-999999', 'vehicle_id': vid, 'driver_id': ids['driver'], 'status': 'active',
        'issue_date': now, 'valid_from': now, 'valid_until': now + timedelta(days=1),
        'odometer_start': 200000, 'odometer_end': None, 'fuel_issued': 150, 'fuel_used': None,
        'created_at': now, 'updated_at': now}).inserted_id
    r = login(app, 'admin').put(f'/api/waybills/{wid}', json={'status': 'completed', 'odometer_end': 200300, 'fuel_used': 112})
    assert r.status_code == 200, r.get_json()
    assert db.fuel_anomalies.find_one({'source_id': str(wid), 'kind': 'trip_overspend'})
