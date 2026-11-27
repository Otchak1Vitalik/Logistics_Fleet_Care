"""PDF путівного листа: формування, права доступу, вміст."""
from bson import ObjectId

from tests.conftest import login, make_vehicle, make_waybill


def test_pdf_for_manager(app, db, ids):
    vid = make_vehicle(db, plate_number='BC1234PDF')
    wid = make_waybill(db, vid, ids['driver'], status='active')
    r = login(app, 'admin').get(f'/api/waybills/{wid}/pdf')
    assert r.status_code == 200
    assert r.headers['Content-Type'] == 'application/pdf'
    assert 'putivka-PL-000001.pdf' in r.headers['Content-Disposition']
    assert r.data.startswith(b'%PDF') and len(r.data) > 20000      # шрифт з кирилицею вбудовано
    assert b'/Title' in r.data and b'DejaVuSans' in r.data
    assert b'/Type /Page' in r.data or b'/Type/Page' in r.data


def test_pdf_access_rules(app, db, ids):
    vid = make_vehicle(db)
    wid = make_waybill(db, vid, ids['driver'])
    assert login(app, 'driver').get(f'/api/waybills/{wid}/pdf').status_code == 200    # власна путівка
    assert login(app, 'driver2').get(f'/api/waybills/{wid}/pdf').status_code == 403   # чужа
    assert login(app, 'mech').get(f'/api/waybills/{wid}/pdf').status_code == 200      # механік (передрейсовий огляд)
    assert app.test_client().get(f'/api/waybills/{wid}/pdf').status_code == 401        # без входу
    assert login(app, 'admin').get(f'/api/waybills/{ObjectId()}/pdf').status_code == 404


def test_pdf_completed_and_cancelled(app, db, ids):
    vid = make_vehicle(db, fuel_norm=25.0)
    wid = make_waybill(db, vid, ids['driver'], status='completed', odometer_start=100000)
    db.waybills.update_one({'_id': ObjectId(wid)}, {'$set': {'odometer_end': 100400, 'fuel_used': 110}})
    client = login(app, 'admin')
    assert client.get(f'/api/waybills/{wid}/pdf').status_code == 200
    db.waybills.update_one({'_id': ObjectId(wid)}, {'$set': {'status': 'cancelled'}})
    assert client.get(f'/api/waybills/{wid}/pdf').status_code == 200
    # перегляд PDF не змінює даних і не потрапляє в журнал дій
    assert db.audit_log.count_documents({'endpoint': 'waybills.waybill_pdf'}) == 0


def test_pdf_download_mode(app, db, ids):
    vid = make_vehicle(db)
    wid = make_waybill(db, vid, ids['driver'])
    client = login(app, 'admin')
    assert client.get(f'/api/waybills/{wid}/pdf').headers['Content-Disposition'].startswith('inline')
    r = client.get(f'/api/waybills/{wid}/pdf?download=1')
    assert r.status_code == 200 and r.headers['Content-Disposition'].startswith('attachment')
