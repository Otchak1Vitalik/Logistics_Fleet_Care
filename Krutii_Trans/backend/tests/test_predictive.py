"""Прогноз несправностей: синтетична історія, навчання й оцінка моделей, ризик автопарку, API."""
from datetime import datetime, timedelta

from bson import ObjectId

from services import predictive_maintenance as pm
from tests.conftest import login, make_vehicle


def _fleet(db, n=8):
    ids = []
    for i in range(n):
        heavy = i % 2 == 0
        ids.append(make_vehicle(db, plate_number=f'BC{i:04d}PM', year=2016 + i % 6, odometer=60000 + i * 25000,
                                fuel_norm=28.0 if heavy else 11.0, tank_capacity=400 if heavy else 70,
                                last_maintenance_km=55000 + i * 25000,
                                last_maintenance_date=datetime.utcnow() - timedelta(days=30 + i * 10)))
    return ids


def test_synthetic_history_is_deterministic(app, db):
    _fleet(db, 3)
    vehicles = list(db.vehicles.find())
    settings = db.settings.find_one({'_id': 'system'})
    now = datetime(2026, 6, 1)
    a, ev = pm.synthetic_history(vehicles, settings, now=now)
    b, _ = pm.synthetic_history(vehicles, settings, now=now)
    assert a == b and len(a) > 150
    assert set(a[0]['features']) == set(pm.FEATURE_KEYS)
    assert {s['label'] for s in a} == {0, 1}
    # мітка відповідає подіям: несправність у межах 30 днів після знімка
    faults = [e for e in ev if e['type'] == 'fault']
    s = next(x for x in a if x['label'] == 1)
    assert any(f['vehicle_id'] == s['vehicle_id'] and 0 < (f['date'] - s['date']).days <= pm.HORIZON_DAYS for f in faults)
    assert all(x['date'] + timedelta(days=pm.HORIZON_DAYS) < now for x in a)   # знімки без «майбутнього»


def test_train_compares_methods(app, db):
    _fleet(db)
    pm.seed_history(db)
    state = pm.train(db, force=True)
    assert state['ready']
    ev = state['evaluation']
    methods = {m['key']: m for m in ev['methods']}
    assert set(methods) == {'rule', 'logreg', 'gboost'}
    assert ev['best'] in ('logreg', 'gboost')
    assert ev['train']['to'] < ev['test']['from']                   # хронологічне розбиття
    for m in methods.values():
        assert 0 <= m['roc_auc'] <= 1 and m['roc'] and m['pr']
    assert methods[ev['best']]['pr_auc'] > methods['rule']['pr_auc']
    assert len(ev['importance']) == len(pm.FEATURE_KEYS)
    assert pm.train(db) is state                                     # кеш, доки дані не змінилися


def test_fleet_risk_and_alerts(app, db):
    ids = _fleet(db)
    db.vehicles.update_one({'_id': ObjectId(ids[0])}, {'$set': {'status': 'decommissioned'}})
    pm.seed_history(db)
    res = pm.fleet_risk(db)
    assert res['ready'] and len(res['items']) == 7                   # списані не прогнозуються
    probs = [i['probability'] for i in res['items']]
    assert probs == sorted(probs, reverse=True) and all(0 <= p <= 1 for p in probs)
    assert res['summary']['high'] + res['summary']['medium'] + res['summary']['low'] == 7
    one = pm.fleet_risk(db, ids[1])['items']
    assert len(one) == 1 and one[0]['vehicle_id'] == ids[1]

    # авто з простроченим ТО і перевитратою пального -> високий ризик і одне сповіщення за тиждень
    pm.LEVEL_HIGH, saved = 0.0, pm.LEVEL_HIGH
    try:
        first = pm.check_risks(db)
        assert first == 7 and pm.check_risks(db) == 0
    finally:
        pm.LEVEL_HIGH = saved
    assert db.alerts.count_documents({'related_type': 'vehicle_risk', 'category': 'maintenance'}) == 7


def test_live_snapshots_get_labels(app, db, ids):
    vid = _fleet(db, 2)[0]
    assert pm.take_snapshot(db) == 2
    old = datetime.utcnow() - timedelta(days=40)
    db.maintenance_history.update_many({}, {'$set': {'date': old}})
    db.fault_reports.insert_one({'vehicle_id': vid, 'report_date': old + timedelta(days=10), 'severity': 'medium',
                                 'reported_by': ids['driver'], 'status': 'new'})
    rows = pm._label_live(db, list(db.maintenance_history.find()))
    labels = {r['vehicle_id']: r['label'] for r in rows}
    assert labels[vid] == 1 and sorted(labels.values()) == [0, 1]
    assert db.maintenance_history.count_documents({'label': None}) == 0


def test_api_access(app, db):
    _fleet(db)
    assert login(app, 'driver').get('/api/predictive/risk').status_code == 403
    assert app.test_client().get('/api/predictive/risk').status_code == 401
    mech = login(app, 'mech')
    assert mech.get('/api/predictive/model').status_code == 403
    admin = login(app, 'admin')
    assert admin.get('/api/predictive/risk').get_json()['ready'] is False       # ще немає історії
    assert admin.post('/api/predictive/retrain').status_code == 400
    pm.seed_history(db)
    r = mech.get('/api/predictive/risk').get_json()
    assert r['ready'] and len(r['items']) == 8 and r['items'][0]['probability'] >= r['items'][-1]['probability']
    m = admin.get('/api/predictive/model').get_json()
    assert m['ready'] and m['evaluation']['test']['n'] > 0
    assert admin.post('/api/predictive/retrain').status_code == 200
    assert db.audit_log.count_documents({'endpoint': 'predictive.retrain', 'status': 'success'}) == 1
    s = admin.get('/api/predictive/scania').get_json()
    assert s['success'] and (not s['ready'] or s['report']['test']['n'] == 16000)
