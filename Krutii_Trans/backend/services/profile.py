"""
Дані для сторінки «Мій профіль»: короткий зріз роботи користувача залежно від ролі.
"""
from datetime import datetime, timedelta

PERIOD_DAYS = 30
LICENSE_WARNING_DAYS = 30


def _to_datetime(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00')).replace(tzinfo=None)
        except ValueError:
            return None
    return None


def build_profile(db, user):
    uid = str(user['_id'])
    now = datetime.utcnow()
    since = now - timedelta(days=PERIOD_DAYS)
    role = user.get('role')
    profile = {'role': role, 'period_days': PERIOD_DAYS, 'last_login': user.get('last_login')}

    if role == 'driver':
        waybills = list(db.waybills.find({'driver_id': uid, 'status': 'completed', 'completed_at': {'$gte': since}},
                                         {'odometer_start': 1, 'odometer_end': 1, 'fuel_used': 1}))
        expiry = _to_datetime(user.get('license_expiry'))
        days_left = (expiry.date() - now.date()).days if expiry else None
        profile.update({
            'license_number': user.get('license_number'),
            'license_expiry': expiry,
            'license_days_left': days_left,
            'license_warning': days_left is not None and days_left <= LICENSE_WARNING_DAYS,
            'stats': {
                'waybills': len(waybills),
                'distance': sum(max(0, (w.get('odometer_end') or 0) - (w.get('odometer_start') or 0)) for w in waybills),
                'fuel_used': round(sum(w.get('fuel_used') or 0 for w in waybills), 1),
                'faults_reported': db.fault_reports.count_documents({'reported_by': uid, 'report_date': {'$gte': since}}),
                'active_waybill': db.waybills.count_documents({'driver_id': uid, 'status': {'$in': ['issued', 'active']}}) > 0,
            },
        })
    elif role == 'mechanic':
        done = list(db.repairs.find({'mechanic_id': uid, 'status': 'completed', 'completed_at': {'$gte': since}},
                                    {'started_at': 1, 'completed_at': 1}))
        durations = [(r['completed_at'] - r['started_at']).total_seconds() / 3600
                     for r in done if r.get('started_at') and r.get('completed_at') and r['completed_at'] > r['started_at']]
        profile['stats'] = {
            'repairs_completed': len(done),
            'repairs_in_progress': db.repairs.count_documents({'mechanic_id': uid, 'status': 'in_progress'}),
            'repairs_planned': db.repairs.count_documents({'mechanic_id': uid, 'status': 'planned'}),
            'avg_repair_hours': round(sum(durations) / len(durations), 1) if durations else None,
            'faults_acknowledged': db.fault_reports.count_documents({'acknowledged_by': uid, 'acknowledged_at': {'$gte': since}}),
        }
    elif role == 'manager':
        profile['stats'] = {
            'vehicles_active': db.vehicles.count_documents({'status': 'active'}),
            'vehicles_total': db.vehicles.count_documents({'status': {'$ne': 'decommissioned'}}),
            'drivers_active': db.users.count_documents({'role': 'driver', 'is_active': True}),
            'open_faults': db.fault_reports.count_documents({'status': {'$in': ['new', 'acknowledged']}}),
            'waybills_issued': db.waybills.count_documents({'issued_by': uid, 'created_at': {'$gte': since}}),
        }
    return profile
