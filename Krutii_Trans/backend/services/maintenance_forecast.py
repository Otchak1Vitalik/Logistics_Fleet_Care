"""
Прогноз дати наступного технічного обслуговування.

Ідея: за завершеними путівками за останні window_days днів обчислюється
середній добовий пробіг автомобіля. Тоді дата, коли буде досягнуто пробіг
наступного ТО, прогнозується як

    D_прогн = D_0 + ceil(Δk / v),

де Δk - залишок пробігу до ТО, км; v - середній добовий пробіг, км/добу.
Очікувана дата ТО - найраніша з прогнозованої за пробігом і планової за календарем.
"""
import math
from datetime import datetime, timedelta

DEFAULT_WINDOW_DAYS = 90


def _to_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00')).date()
        except ValueError:
            return None
    return None


def daily_mileage(db, window_days=DEFAULT_WINDOW_DAYS, vehicle_ids=None):
    """
    Середній добовий пробіг {vehicle_id: км/добу} за завершеними путівками.
    Один агрегаційний запит для всього автопарку.
    """
    since = datetime.utcnow() - timedelta(days=window_days)
    match = {
        'status': 'completed',
        'completed_at': {'$gte': since},
        'odometer_end': {'$ne': None},
    }
    if vehicle_ids is not None:
        match['vehicle_id'] = {'$in': list(vehicle_ids)}
    rows = db.waybills.aggregate([
        {'$match': match},
        {'$group': {
            '_id': '$vehicle_id',
            'distance': {'$sum': {'$max': [0, {'$subtract': ['$odometer_end', '$odometer_start']}]}},
        }},
    ])
    return {r['_id']: r['distance'] / window_days for r in rows if r['distance'] > 0}


def forecast(vehicle, avg_daily_km, today=None):
    """Прогноз ТО для одного автомобіля."""
    today = today or datetime.utcnow().date()
    next_km = vehicle.get('next_maintenance_km')
    odometer = vehicle.get('odometer') or 0
    km_left = next_km - odometer if next_km else None
    planned = _to_date(vehicle.get('next_maintenance_date'))

    by_km = None
    if km_left is not None:
        if km_left <= 0:
            by_km = today
        elif avg_daily_km and avg_daily_km > 0:
            by_km = today + timedelta(days=math.ceil(km_left / avg_daily_km))

    candidates = [d for d in (by_km, planned) if d]
    expected = min(candidates) if candidates else None
    basis = None
    if expected:
        basis = 'mileage' if by_km and (planned is None or by_km < planned) else 'date'

    return {
        'avg_daily_km': round(avg_daily_km, 1) if avg_daily_km else None,
        'km_left': km_left,
        'forecast_by_km': by_km.isoformat() if by_km else None,
        'planned_date': planned.isoformat() if planned else None,
        'expected_date': expected.isoformat() if expected else None,
        'days_left': (expected - today).days if expected else None,
        'basis': basis,
    }


def forecast_for_vehicle(db, vehicle, window_days=DEFAULT_WINDOW_DAYS):
    vid = str(vehicle['_id'])
    return forecast(vehicle, daily_mileage(db, window_days, [vid]).get(vid))
