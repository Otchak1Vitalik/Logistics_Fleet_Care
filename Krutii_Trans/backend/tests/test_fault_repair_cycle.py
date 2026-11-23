"""Експеримент 2. Повний цикл: несправність -> ремонт -> закриття."""
from bson import ObjectId

from tests.conftest import login, make_vehicle, make_waybill

FAULT = {'category': 'brakes', 'severity': 'critical',
         'description': 'Скрип і зниження ефективності гальм'}


def test_driver_without_waybill_cannot_report(app, db, ids):
    vid = make_vehicle(db)
    resp = login(app, 'driver').post('/api/faults', json={**FAULT, 'vehicle_id': vid})
    assert resp.status_code == 403


def test_full_cycle(app, db, ids):
    vid = make_vehicle(db)
    make_waybill(db, vid, ids['driver'])

    # 1. Водій реєструє несправність
    resp = login(app, 'driver').post('/api/faults', json={**FAULT, 'vehicle_id': vid})
    assert resp.status_code == 201
    fault = resp.get_json()['fault']
    assert fault['number'].startswith('НС-') and fault['status'] == 'new'

    # 2. Система автоматично сповіщає механіків (critical -> critical)
    alert = db.alerts.find_one({'related_id': fault['_id'], 'category': 'fault'})
    assert alert and alert['recipient_role'] == 'mechanic' and alert['alert_type'] == 'critical'

    # 3. Механік створює ремонт, пов'язаний з несправністю
    mech = login(app, 'mech')
    resp = mech.post('/api/repairs', json={'vehicle_id': vid, 'fault_id': fault['_id'],
                                           'repair_type': 'repair', 'description': 'Заміна колодок'})
    assert resp.status_code == 201
    repair_id = resp.get_json()['repair']['_id']
    assert db.fault_reports.find_one({'_id': ObjectId(fault['_id'])})['status'] == 'in_repair'

    # 4. Початок робіт -> авто в ремонті
    assert mech.put(f'/api/repairs/{repair_id}', json={'status': 'in_progress'}).status_code == 200
    assert db.vehicles.find_one({'_id': ObjectId(vid)})['status'] == 'repair'

    # 5. Завершення -> авто активне, несправність вирішена
    resp = mech.put(f'/api/repairs/{repair_id}', json={'status': 'completed',
                                                       'work_performed': 'Замінено колодки', 'parts_cost': 2400})
    assert resp.status_code == 200
    assert db.vehicles.find_one({'_id': ObjectId(vid)})['status'] == 'active'
    assert db.fault_reports.find_one({'_id': ObjectId(fault['_id'])})['status'] == 'resolved'


def test_completed_repair_cannot_be_completed_again(app, db, ids):
    vid = make_vehicle(db)
    mech = login(app, 'mech')
    rid = mech.post('/api/repairs', json={'vehicle_id': vid, 'repair_type': 'repair',
                                          'description': 'Ремонт генератора'}).get_json()['repair']['_id']
    mech.put(f'/api/repairs/{rid}', json={'status': 'in_progress'})
    mech.put(f'/api/repairs/{rid}', json={'status': 'completed', 'work_performed': 'Готово'})
    resp = mech.put(f'/api/repairs/{rid}', json={'status': 'completed', 'work_performed': 'Ще раз'})
    assert resp.status_code == 400


def test_vehicle_stays_in_repair_while_other_repair_active(app, db, ids):
    vid = make_vehicle(db)
    mech = login(app, 'mech')
    r1 = mech.post('/api/repairs', json={'vehicle_id': vid, 'repair_type': 'repair',
                                         'description': 'Ремонт 1'}).get_json()['repair']['_id']
    r2 = mech.post('/api/repairs', json={'vehicle_id': vid, 'repair_type': 'repair',
                                         'description': 'Ремонт 2'}).get_json()['repair']['_id']
    mech.put(f'/api/repairs/{r1}', json={'status': 'in_progress'})
    mech.put(f'/api/repairs/{r2}', json={'status': 'in_progress'})
    mech.put(f'/api/repairs/{r1}', json={'status': 'completed', 'work_performed': 'Готово'})
    assert db.vehicles.find_one({'_id': ObjectId(vid)})['status'] == 'repair'


def test_lists_contain_related_data(app, db, ids):
    """Списки несправностей і ремонтів містять дані авто, водія та механіка (пакетне завантаження)."""
    vid = make_vehicle(db)
    make_waybill(db, vid, ids['driver'])
    fid = login(app, 'driver').post('/api/faults', json={**FAULT, 'vehicle_id': vid}).get_json()['fault']['_id']
    mech = login(app, 'mech')
    mech.post('/api/repairs', json={'vehicle_id': vid, 'fault_id': fid, 'repair_type': 'repair',
                                    'description': 'Заміна колодок'})
    fault = mech.get('/api/faults').get_json()['faults'][0]
    assert fault['vehicle']['plate_number'] == 'BC0001AA' and fault['reporter']['username'] == 'driver'
    assert 'password_hash' not in fault['reporter']
    repair = mech.get('/api/repairs').get_json()['repairs'][0]
    assert repair['vehicle']['plate_number'] == 'BC0001AA'
    assert repair['mechanic']['username'] == 'mech' and repair['fault']['_id'] == fid
