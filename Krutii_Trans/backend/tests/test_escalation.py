"""Експеримент 4. Ескалація необроблених несправностей."""
from datetime import datetime, timedelta

from services.alert_engine import check_fault_escalation
from tests.conftest import make_vehicle


def add_fault(db, vid, hours_ago, status='new'):
    return str(db.fault_reports.insert_one({
        'number': 'НС-000001', 'vehicle_id': vid, 'reported_by': 'x', 'category': 'engine',
        'severity': 'high', 'description': 'Тестова несправність', 'status': status,
        'report_date': datetime.utcnow() - timedelta(hours=hours_ago),
    }).inserted_id)


def escalations(db, fid, role):
    return db.alerts.count_documents({'related_id': fid, 'category': 'escalation', 'recipient_role': role})


def test_escalation_levels(app, db):
    vid = make_vehicle(db)
    fresh, h5, h25 = add_fault(db, vid, 1), add_fault(db, vid, 5), add_fault(db, vid, 25)
    check_fault_escalation(db)
    assert escalations(db, fresh, 'mechanic') == 0
    assert escalations(db, h5, 'mechanic') == 1 and escalations(db, h5, 'manager') == 0
    assert escalations(db, h25, 'mechanic') == 1 and escalations(db, h25, 'manager') == 1


def test_acknowledged_fault_not_escalated(app, db):
    fid = add_fault(db, make_vehicle(db), 30, status='acknowledged')
    check_fault_escalation(db)
    assert db.alerts.count_documents({'related_id': fid}) == 0


def test_escalation_is_idempotent(app, db):
    fid = add_fault(db, make_vehicle(db), 30)
    check_fault_escalation(db)
    check_fault_escalation(db)
    assert escalations(db, fid, 'mechanic') == 1 and escalations(db, fid, 'manager') == 1


def test_escalation_uses_settings(app, db):
    db.settings.update_one({'_id': 'system'}, {'$set': {'fault_mechanic_hours': 1}})
    fid = add_fault(db, make_vehicle(db), 2)
    check_fault_escalation(db)
    assert escalations(db, fid, 'mechanic') == 1
