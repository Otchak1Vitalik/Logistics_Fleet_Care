"""Телематика: ключі пристроїв, прийом даних, правила (перегрів, напруга, коди, злив, рух без путівки), карта."""
from datetime import datetime, timedelta

from bson import ObjectId

from services import telematics as tm
from services.geo_ukraine import route, route_points
from tests.conftest import login, make_vehicle, make_waybill


def _pt(sec, **kw):
    base = {'ts': (datetime.utcnow() - timedelta(seconds=150 - sec * 0.25)).isoformat() + 'Z', 'lat': 50.45, 'lon': 30.52,
            'speed': 60, 'odometer': 100000 + sec / 10, 'fuel_level': 300, 'engine_temp': 88, 'battery_v': 27.8}
    base.update(kw)
    return base


def _device(db, **kw):
    vid = make_vehicle(db, tank_capacity=400, **kw)
    return vid, tm.provision(db, vid)


def _post(app, key, points):
    return app.test_client().post('/api/telematics/ingest', json={'points': points}, headers={'X-Device-Key': key})


def test_route_by_roads():
    assert route('Київ', 'Львів') == ['Київ', 'Житомир', 'Звягель', 'Рівне', 'Дубно', 'Броди', 'Львів']
    pts, km = route_points('Київ', 'Одеса')
    assert pts[0] == [50.4501, 30.5234] and 450 < km < 600
    assert route('Київ', 'Атлантида') is None


def test_device_key_and_validation(app, db, ids):
    vid, key = _device(db)
    v = db.vehicles.find_one({'_id': ObjectId(vid)})
    assert v['telematics']['key_hash'] != key and key.endswith(v['telematics']['key_hint'])   # у базі лише хеш
    assert _post(app, 'kt_wrong', [_pt(0)]).status_code == 401
    assert _post(app, key, [{'lat': 999, 'lon': 30, 'ts': datetime.utcnow().isoformat()}]).status_code == 400
    make_waybill(db, vid, ids['driver'], status='active')
    r = _post(app, key, [_pt(0), _pt(2), {'bad': 1}])
    assert r.status_code == 200 and r.get_json()['accepted'] == 2 and r.get_json()['rejected'] == 1
    # повтор старої точки ігнорується, одометр авто оновлюється з телематики
    _post(app, key, [_pt(0)])
    assert db.telemetry.count_documents({'vehicle_id': vid}) == 3
    assert db.vehicles.find_one({'_id': ObjectId(vid)})['odometer'] == 100000
    _post(app, key, [_pt(30, odometer=100250)])
    assert db.vehicles.find_one({'_id': ObjectId(vid)})['odometer'] == 100250


def test_rules_and_alerts(app, db, ids):
    vid, key = _device(db, fuel_norm=28.0)
    make_waybill(db, vid, ids['driver'], status='active')
    pts = [_pt(0), _pt(2, engine_temp=107), _pt(4, engine_temp=109), _pt(6, battery_v=22.4),
           _pt(8, dtc=['P0087']), _pt(10, dtc=['P0087'])]
    res = _post(app, key, pts).get_json()
    assert sorted(res['events']) == ['dtc', 'low_battery', 'overheat']       # кожне - один раз
    assert db.alerts.count_documents({'category': 'telematics', 'recipient_role': 'mechanic'}) == 3
    # злив: машина стоїть, рівень різко впав -> подія, сповіщення і запис в «Аномалії пального»
    res = _post(app, key, [_pt(20, speed=0, fuel_level=300), _pt(80, speed=0, fuel_level=220)]).get_json()
    assert res['events'] == ['fuel_drain']
    fa = db.fuel_anomalies.find_one({'kind': 'fuel_drain', 'vehicle_id': vid})
    assert fa and fa['metrics']['liters'] == 80 and fa['status'] == 'new' and fa['driver_id'] == ids['driver']
    # заправка на стоянці - подія без сповіщення; плавна витрата в русі - не злив
    res = _post(app, key, [_pt(90, speed=0, fuel_level=380), _pt(120, speed=70, fuel_level=378)]).get_json()
    assert res['events'] == ['refuel']
    # «перерахунок» аномалій пального не видаляє зливи з телематики
    from services.fuel_anomalies import run_detection
    run_detection(db, notify=False)
    assert db.fuel_anomalies.count_documents({'kind': 'fuel_drain'}) == 1
    # сповіщення того самого типу - не частіше ніж раз на 2 години
    _post(app, key, [_pt(130, engine_temp=80), _pt(140, engine_temp=110)])
    assert db.alerts.count_documents({'category': 'telematics', 'title': {'$regex': '^Перегрів'}, 'recipient_role': 'manager'}) == 1


def test_movement_without_waybill(app, db):
    vid, key = _device(db)
    res = _post(app, key, [_pt(0, speed=0), _pt(2, speed=45), _pt(4, speed=50)]).get_json()
    assert res['events'] == ['no_waybill']
    assert db.alerts.find_one({'title': {'$regex': '^Рух без путівки'}, 'alert_type': 'critical'})


def test_fleet_and_vehicle_api(app, db, ids):
    vid, key = _device(db, plate_number='BC7777TM')
    make_vehicle(db, plate_number='BC8888TM')                                   # без трекера
    wid = make_waybill(db, vid, ids['driver'], status='active')
    db.waybills.update_one({'_id': ObjectId(wid)}, {'$set': {'route_from': 'Київ', 'route_to': 'Львів'}})
    _post(app, key, [_pt(i * 2, odometer=100000 + i) for i in range(10)])
    assert login(app, 'driver').get('/api/telematics/fleet').status_code == 403
    r = login(app, 'mech').get('/api/telematics/fleet').get_json()
    items = {i['plate']: i for i in r['items']}
    assert items['BC7777TM']['connection'] == 'moving' and items['BC7777TM']['tracker']
    assert items['BC7777TM']['waybill']['route'][0] == [50.4501, 30.5234]
    assert items['BC8888TM']['connection'] == 'none' and r['summary']['moving'] == 1
    assert any(c['name'] == 'Одеса' for c in r['cities'])
    d = login(app, 'admin').get(f'/api/telematics/vehicle/{vid}?hours=1').get_json()
    assert len(d['points']) == 10 and d['distance_km'] == 9
    # керівник видає новий ключ; старий перестає працювати
    admin = login(app, 'admin')
    new = admin.post(f'/api/telematics/devices/{vid}').get_json()['key']
    assert _post(app, key, [_pt(500)]).status_code == 401 and _post(app, new, [_pt(500)]).status_code == 200
    assert login(app, 'mech').post(f'/api/telematics/devices/{vid}').status_code == 403
    assert db.audit_log.count_documents({'endpoint': 'telematics.provision', 'status': 'success'}) == 1


def test_offline_and_risk_signals(app, db, ids):
    vid, key = _device(db)
    make_waybill(db, vid, ids['driver'], status='active')
    _post(app, key, [_pt(0, engine_temp=108, dtc=['P0217'])])
    db.telematics_state.update_one({'_id': vid}, {'$set': {'ts': datetime.utcnow() - timedelta(minutes=20)}})
    assert {i['vehicle_id']: i['connection'] for i in tm.fleet(db)['items']}[vid] == 'offline'
    sig = tm.signals(db)[vid]
    assert sig['overheat'] == 1 and sig['dtc'] == 1 and sig['codes'] == ['P0217']
