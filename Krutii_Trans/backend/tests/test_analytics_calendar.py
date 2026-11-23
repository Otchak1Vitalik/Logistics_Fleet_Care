"""Експеримент 6. Аналітика для графіків і календар ТО."""
from datetime import datetime, timedelta

from tests.conftest import login, make_vehicle


def test_analytics_groups_costs_faults_and_fuel_types(app, db):
    now = datetime.utcnow()
    v1 = make_vehicle(db, fuel_type='diesel')
    make_vehicle(db, plate_number='P1', fuel_type='petrol')
    make_vehicle(db, plate_number='G1', fuel_type='gas')
    make_vehicle(db, plate_number='G2', fuel_type='gas')
    db.repairs.insert_many([
        {'vehicle_id': v1, 'status': 'completed', 'completed_at': now, 'labor_cost': 1000, 'parts_cost': 500},
        {'vehicle_id': v1, 'status': 'completed', 'completed_at': now, 'labor_cost': 200},
        {'vehicle_id': v1, 'status': 'planned', 'labor_cost': 9999},   # не завершено - не враховується
    ])
    db.fuel_invoices.insert_one({'date': now, 'total_amount': 52000.0, 'fuel_type': 'diesel'})
    db.fault_reports.insert_many([
        {'vehicle_id': v1, 'category': 'brakes', 'report_date': now},
        {'vehicle_id': v1, 'category': 'brakes', 'report_date': now},
        {'vehicle_id': v1, 'category': 'engine', 'report_date': now},
    ])
    data = login(app, 'admin').get('/api/reports/analytics').get_json()['analytics']

    assert len(data['monthly_costs']) == 6
    current = data['monthly_costs'][-1]
    assert current['repairs'] == 1700 and current['fuel'] == 52000
    assert data['faults_by_category'][0] == {'category': 'brakes', 'label': 'Гальма', 'count': 2}
    fuel = {r['fuel_type']: r['count'] for r in data['fleet_by_fuel']}
    assert fuel == {'diesel': 1, 'petrol': 1, 'gas': 2}


def test_analytics_only_for_manager(app, db):
    assert login(app, 'mech').get('/api/reports/analytics').status_code == 403


def test_calendar_contains_planned_maintenance_and_repairs(app, db):
    now = datetime.utcnow()
    first = datetime(now.year, now.month, 1)
    due = first + timedelta(days=14)
    vid = make_vehicle(db, plate_number='CAL01', next_maintenance_date=due)
    make_vehicle(db, plate_number='OTHER', next_maintenance_date=first + timedelta(days=70))  # інший місяць
    db.repairs.insert_one({'vehicle_id': vid, 'repair_type': 'maintenance', 'status': 'planned',
                           'scheduled_date': first + timedelta(days=3), 'description': 'ТО-1'})
    db.repairs.insert_one({'vehicle_id': vid, 'repair_type': 'repair', 'status': 'cancelled',
                           'scheduled_date': first + timedelta(days=4), 'description': 'Скасовано'})

    resp = login(app, 'mech').get(f'/api/reports/maintenance-calendar?year={now.year}&month={now.month}')
    assert resp.status_code == 200
    events = resp.get_json()['events']
    kinds = sorted((e['type'], e['plate_number']) for e in events)
    assert kinds == [('planned_maintenance', 'CAL01'), ('repair', 'CAL01')]
    assert next(e for e in events if e['type'] == 'planned_maintenance')['date'] == due.strftime('%Y-%m-%d')


def test_calendar_rejects_bad_month(app, db):
    assert login(app, 'mech').get('/api/reports/maintenance-calendar?year=2026&month=13').status_code == 400


def test_seed_has_all_fuel_types(app, db, capsys):
    from seed import seed_database
    seed_database()
    capsys.readouterr()
    assert set(db.vehicles.distinct('fuel_type')) == {'diesel', 'petrol', 'gas'}


def test_unknown_fault_categories_merged_into_other(app, db):
    vid = make_vehicle(db)
    now = datetime.utcnow()
    db.fault_reports.insert_many([{'vehicle_id': vid, 'category': c, 'report_date': now}
                                  for c in ('tires', 'cooling', 'other', 'engine')])
    rows = login(app, 'admin').get('/api/reports/analytics').get_json()['analytics']['faults_by_category']
    assert {r['category']: r['count'] for r in rows} == {'other': 3, 'engine': 1}


def test_seed_external_refuels_counted_in_costs(app, db, capsys):
    """Демо-дані містять зовнішні заправки з сумою, тож блок «Витрати на пальне» не порожній."""
    from seed import seed_database
    seed_database()
    capsys.readouterr()
    assert db.fuel_records.count_documents({'record_type': 'external', 'total_amount': {'$gt': 0}}) > 0
    costs = login(app, 'admin').get('/api/reports/costs-summary').get_json()
    assert costs['fuel']['external']['total'] > 0


def test_seed_statuses_and_visible_alerts(app, db, capsys):
    """Демо-дані: бензин і газ у різних статусах, по одному списаному авто кожного типу,
    а сповіщення мають формат системи і відображаються керівнику та механіку."""
    from collections import Counter
    from seed import seed_database
    seed_database()
    capsys.readouterr()
    by = Counter((v['fuel_type'], v['status']) for v in db.vehicles.find())
    for fuel in ('petrol', 'gas'):
        assert by[(fuel, 'repair')] == 2 and by[(fuel, 'inspection')] == 2 and by[(fuel, 'active')] >= 1
    assert {f for (f, s) in by if s == 'decommissioned'} == {'diesel', 'petrol', 'gas'}
    # кожне авто в ремонті / на огляді має відповідну роботу в процесі
    for v in db.vehicles.find({'status': {'$in': ['repair', 'inspection']}}):
        assert db.repairs.count_documents({'vehicle_id': str(v['_id']), 'status': 'in_progress'}) >= 1
    assert db.alerts.count_documents({'user_id': {'$exists': True}}) == 0
    assert login(app, 'admin').get('/api/alerts').get_json()['total'] > 0
    mech = app.test_client()  # демо-механік із seed.py
    assert mech.post('/api/auth/login', json={'username': 'mech_koval', 'password': 'Mech1234'}).status_code == 200
    assert mech.get('/api/alerts').get_json()['total'] > 0
