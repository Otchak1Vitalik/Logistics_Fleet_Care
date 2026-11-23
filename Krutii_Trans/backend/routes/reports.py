"""
Маршрути звітів для керівника
"""
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, g
from bson import ObjectId

from extensions import mongo
from services.maintenance_forecast import daily_mileage, forecast
from middleware.auth_middleware import require_auth, require_role

reports_bp = Blueprint('reports', __name__)


@reports_bp.route('/dashboard', methods=['GET'])
@require_auth
@require_role('manager')
def dashboard():
    """
    Дані для дашборду керівника.
    """
    # Кількість активних авто
    active_vehicles = mongo.db.vehicles.count_documents({'status': 'active'})
    total_vehicles = mongo.db.vehicles.count_documents({})

    # Кількість водіїв
    active_drivers = mongo.db.users.count_documents({'role': 'driver', 'is_active': True})

    # Активні путівки
    active_waybills = mongo.db.waybills.count_documents({'status': {'$in': ['issued', 'active']}})

    # Нові несправності
    new_faults = mongo.db.fault_reports.count_documents({'status': 'new'})
    critical_faults = mongo.db.fault_reports.count_documents({'status': {'$in': ['new', 'acknowledged']}, 'severity': 'critical'})

    # Ремонти в роботі
    repairs_in_progress = mongo.db.repairs.count_documents({'status': 'in_progress'})
    planned_repairs = mongo.db.repairs.count_documents({'status': 'planned'})

    # Непрочитані сповіщення
    unread_alerts = mongo.db.alerts.count_documents({
        '$or': [
            {'recipient_id': g.current_user['_id']},
            {'recipient_role': 'manager'}
        ],
        'is_read': False,
        'is_dismissed': False
    })

    # Авто, що потребують ТО (в межах 1000 км або 14 днів)
    today = datetime.utcnow()
    deadline = today + timedelta(days=14)
    maintenance_due = mongo.db.vehicles.count_documents({
        'status': 'active',
        '$or': [
            {'$expr': {'$lte': [{'$subtract': ['$next_maintenance_km', '$odometer']}, 1000]}},
            {'next_maintenance_date': {'$lte': deadline}}
        ]
    })

    return jsonify({
        'success': True,
        'dashboard': {
            'vehicles': {
                'active': active_vehicles,
                'total': total_vehicles,
                'maintenance_due': maintenance_due
            },
            'drivers': {
                'active': active_drivers
            },
            'waybills': {
                'active': active_waybills
            },
            'faults': {
                'new': new_faults,
                'critical': critical_faults
            },
            'repairs': {
                'in_progress': repairs_in_progress,
                'planned': planned_repairs
            },
            'alerts': {
                'unread': unread_alerts
            }
        }
    })


@reports_bp.route('/fleet-status', methods=['GET'])
@require_auth
@require_role('manager')
def fleet_status():
    """
    Статус автопарку.
    """
    # По статусах
    by_status = list(mongo.db.vehicles.aggregate([
        {'$group': {'_id': '$status', 'count': {'$sum': 1}}}
    ]))

    # Деталі по авто
    vehicles = list(mongo.db.vehicles.find().sort('plate_number', 1))

    result = []
    for v in vehicles:
        # Поточна путівка
        current_waybill = mongo.db.waybills.find_one({
            'vehicle_id': str(v['_id']),
            'status': {'$in': ['issued', 'active']}
        })

        # Відкриті несправності
        open_faults = mongo.db.fault_reports.count_documents({
            'vehicle_id': str(v['_id']),
            'status': {'$in': ['new', 'acknowledged', 'in_repair']}
        })

        result.append({
            '_id': str(v['_id']),
            'plate_number': v['plate_number'],
            'brand': v['brand'],
            'model': v['model'],
            'status': v['status'],
            'odometer': v.get('odometer', 0),
            'next_maintenance_km': v.get('next_maintenance_km'),
            'next_maintenance_date': v.get('next_maintenance_date'),
            'has_active_waybill': current_waybill is not None,
            'current_driver': None,
            'open_faults': open_faults
        })

        if current_waybill:
            driver = mongo.db.users.find_one({'_id': ObjectId(current_waybill['driver_id'])})
            if driver:
                result[-1]['current_driver'] = driver['full_name']

    return jsonify({
        'success': True,
        'by_status': by_status,
        'vehicles': result
    })


@reports_bp.route('/fuel-consumption', methods=['GET'])
@require_auth
@require_role('manager')
def fuel_consumption_report():
    """
    Звіт по витратах пального.
    """
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')

    if not date_from:
        date_from = (datetime.utcnow() - timedelta(days=30)).isoformat()
    if not date_to:
        date_to = datetime.utcnow().isoformat()

    # Витрати по авто
    pipeline = [
        {
            '$match': {
                'status': 'completed',
                'completed_at': {
                    '$gte': datetime.fromisoformat(date_from),
                    '$lte': datetime.fromisoformat(date_to)
                },
                'fuel_used': {'$exists': True, '$ne': None}
            }
        },
        {
            '$group': {
                '_id': '$vehicle_id',
                'total_distance': {'$sum': {'$subtract': ['$odometer_end', '$odometer_start']}},
                'total_fuel': {'$sum': '$fuel_used'},
                'waybills_count': {'$sum': 1}
            }
        }
    ]

    by_vehicle = list(mongo.db.waybills.aggregate(pipeline))

    # Збагачуємо даними про авто
    result = []
    for item in by_vehicle:
        if item['_id']:
            vehicle = mongo.db.vehicles.find_one({'_id': ObjectId(item['_id'])})
            if vehicle and item['total_distance'] > 0:
                consumption = (item['total_fuel'] / item['total_distance']) * 100
                result.append({
                    'vehicle_id': item['_id'],
                    'plate_number': vehicle['plate_number'],
                    'brand': vehicle['brand'],
                    'model': vehicle['model'],
                    'fuel_norm': vehicle.get('fuel_norm', 25),
                    'total_distance': item['total_distance'],
                    'total_fuel': item['total_fuel'],
                    'consumption_per_100km': round(consumption, 2),
                    'waybills_count': item['waybills_count'],
                    'deviation_percent': round(((consumption - vehicle.get('fuel_norm', 25)) / vehicle.get('fuel_norm', 25)) * 100, 2)
                })

    # Сортуємо за перевитратою
    result.sort(key=lambda x: x['deviation_percent'], reverse=True)

    # Загальні показники
    total_fuel = sum(r['total_fuel'] for r in result)
    total_distance = sum(r['total_distance'] for r in result)

    return jsonify({
        'success': True,
        'period': {
            'from': date_from,
            'to': date_to
        },
        'summary': {
            'total_fuel': total_fuel,
            'total_distance': total_distance,
            'avg_consumption': round((total_fuel / total_distance) * 100, 2) if total_distance > 0 else 0
        },
        'by_vehicle': result
    })


@reports_bp.route('/driver-performance', methods=['GET'])
@require_auth
@require_role('manager')
def driver_performance():
    """
    Продуктивність водіїв.
    """
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')

    if not date_from:
        date_from = (datetime.utcnow() - timedelta(days=30)).isoformat()
    if not date_to:
        date_to = datetime.utcnow().isoformat()

    # Статистика по водіях
    pipeline = [
        {
            '$match': {
                'status': 'completed',
                'completed_at': {
                    '$gte': datetime.fromisoformat(date_from),
                    '$lte': datetime.fromisoformat(date_to)
                }
            }
        },
        {
            '$group': {
                '_id': '$driver_id',
                'total_waybills': {'$sum': 1},
                'total_distance': {'$sum': {'$subtract': ['$odometer_end', '$odometer_start']}},
                'total_fuel': {'$sum': {'$ifNull': ['$fuel_used', 0]}}
            }
        }
    ]

    by_driver = list(mongo.db.waybills.aggregate(pipeline))

    result = []
    for item in by_driver:
        if item['_id']:
            driver = mongo.db.users.find_one({'_id': ObjectId(item['_id'])})
            if driver:
                # Кількість несправностей від водія
                faults_count = mongo.db.fault_reports.count_documents({
                    'reported_by': item['_id'],
                    'report_date': {
                        '$gte': datetime.fromisoformat(date_from),
                        '$lte': datetime.fromisoformat(date_to)
                    }
                })

                result.append({
                    'driver_id': item['_id'],
                    'full_name': driver['full_name'],
                    'total_waybills': item['total_waybills'],
                    'total_distance': item['total_distance'],
                    'total_fuel': item['total_fuel'],
                    'faults_reported': faults_count
                })

    # Сортуємо за пробігом
    result.sort(key=lambda x: x['total_distance'], reverse=True)

    return jsonify({
        'success': True,
        'period': {
            'from': date_from,
            'to': date_to
        },
        'drivers': result
    })


@reports_bp.route('/maintenance-schedule', methods=['GET'])
@require_auth
@require_role('manager', 'mechanic')
def maintenance_schedule():
    """
    Графік технічного обслуговування.
    """
    vehicles = list(mongo.db.vehicles.find({'status': {'$ne': 'decommissioned'}}).sort('plate_number', 1))

    result = []
    today = datetime.utcnow().date()
    # Середній добовий пробіг усього автопарку - одним запитом
    rates = daily_mileage(mongo.db)

    for v in vehicles:
        km_remaining = None
        days_remaining = None
        status = 'ok'

        if v.get('next_maintenance_km') and v.get('odometer'):
            km_remaining = v['next_maintenance_km'] - v['odometer']
            if km_remaining <= 0:
                status = 'overdue'
            elif km_remaining <= 1000:
                status = 'warning'

        if v.get('next_maintenance_date'):
            next_date = v['next_maintenance_date']
            # Конвертуємо в date якщо потрібно
            if isinstance(next_date, datetime):
                next_date = next_date.date()
            elif isinstance(next_date, str):
                try:
                    next_date = datetime.fromisoformat(next_date.replace('Z', '+00:00')).date()
                except:
                    next_date = None
            if next_date:
                days_remaining = (next_date - today).days
                if days_remaining <= 0:
                    status = 'overdue'
                elif days_remaining <= 14 and status != 'overdue':
                    status = 'warning'

        result.append({
            '_id': str(v['_id']),
            'plate_number': v['plate_number'],
            'brand': v['brand'],
            'model': v['model'],
            'current_odometer': v.get('odometer', 0),
            'last_maintenance_km': v.get('last_maintenance_km'),
            'last_maintenance_date': v.get('last_maintenance_date'),
            'next_maintenance_km': v.get('next_maintenance_km'),
            'next_maintenance_date': v.get('next_maintenance_date'),
            'km_remaining': km_remaining,
            'days_remaining': days_remaining,
            'status': status,
            'forecast': forecast(v, rates.get(str(v['_id'])), today)
        })

    # Сортуємо: спочатку прострочені, потім попередження
    status_order = {'overdue': 0, 'warning': 1, 'ok': 2}
    result.sort(key=lambda x: (status_order.get(x['status'], 3), x.get('km_remaining') or 999999))

    return jsonify({
        'success': True,
        'schedule': result
    })


@reports_bp.route('/costs-summary', methods=['GET'])
@require_auth
@require_role('manager')
def costs_summary():
    """
    Зведення витрат.
    """
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')

    if not date_from:
        date_from = (datetime.utcnow() - timedelta(days=30)).isoformat()
    if not date_to:
        date_to = datetime.utcnow().isoformat()

    # Витрати на пальне (зовнішні заправки)
    fuel_pipeline = [
        {
            '$match': {
                'record_type': 'external',
                'date': {
                    '$gte': datetime.fromisoformat(date_from),
                    '$lte': datetime.fromisoformat(date_to)
                },
                'total_amount': {'$exists': True}
            }
        },
        {
            '$group': {
                '_id': None,
                'total': {'$sum': '$total_amount'},
                'quantity': {'$sum': '$quantity'}
            }
        }
    ]
    fuel_costs = list(mongo.db.fuel_records.aggregate(fuel_pipeline))

    # Витрати на ремонти
    repair_pipeline = [
        {
            '$match': {
                'status': 'completed',
                'completed_at': {
                    '$gte': datetime.fromisoformat(date_from),
                    '$lte': datetime.fromisoformat(date_to)
                }
            }
        },
        {
            '$group': {
                '_id': '$repair_type',
                'labor_cost': {'$sum': {'$ifNull': ['$labor_cost', 0]}},
                'parts_cost': {'$sum': {'$ifNull': ['$parts_cost', 0]}},
                'count': {'$sum': 1}
            }
        }
    ]
    repair_costs = list(mongo.db.repairs.aggregate(repair_pipeline))

    # Накладні на пальне
    invoice_pipeline = [
        {
            '$match': {
                'date': {
                    '$gte': datetime.fromisoformat(date_from),
                    '$lte': datetime.fromisoformat(date_to)
                },
                'total_amount': {'$exists': True}
            }
        },
        {
            '$group': {
                '_id': '$fuel_type',
                'total': {'$sum': '$total_amount'},
                'quantity': {'$sum': '$quantity'}
            }
        }
    ]
    invoice_costs = list(mongo.db.fuel_invoices.aggregate(invoice_pipeline))

    return jsonify({
        'success': True,
        'period': {
            'from': date_from,
            'to': date_to
        },
        'fuel': {
            'external': fuel_costs[0] if fuel_costs else {'total': 0, 'quantity': 0},
            'invoices': invoice_costs
        },
        'repairs': repair_costs
    })


# ---------------------------------------------------------------------------
# Аналітика для графіків дашборда
# ---------------------------------------------------------------------------
FAULT_CATEGORY_LABELS = {
    'engine': 'Двигун', 'transmission': 'Трансмісія', 'brakes': 'Гальма',
    'electrical': 'Електрика', 'suspension': 'Підвіска', 'body': 'Кузов', 'other': 'Інше'
}
FUEL_TYPE_LABELS = {'diesel': 'Дизель', 'petrol': 'Бензин', 'gas': 'Газ'}
MONTH_LABELS = ['Січ', 'Лют', 'Бер', 'Кві', 'Тра', 'Чер', 'Лип', 'Сер', 'Вер', 'Жов', 'Лис', 'Гру']


def _month_starts(count, now=None):
    """Повертає перші дні останніх count місяців (від найстарішого до поточного)."""
    now = now or datetime.utcnow()
    year, month = now.year, now.month
    result = []
    for _ in range(count):
        result.append(datetime(year, month, 1))
        month -= 1
        if month == 0:
            month, year = 12, year - 1
    return list(reversed(result))


@reports_bp.route('/analytics', methods=['GET'])
@require_auth
@require_role('manager')
def analytics():
    """
    Дані для графіків: витрати по місяцях, несправності за категоріями,
    структура автопарку за типом пального.
    """
    try:
        months = min(max(int(request.args.get('months', 6)), 1), 24)
    except (TypeError, ValueError):
        months = 6
    starts = _month_starts(months)
    period_start = starts[0]

    # Витрати на ремонти/ТО за місяцем завершення
    repair_rows = mongo.db.repairs.aggregate([
        {'$match': {'status': 'completed', 'completed_at': {'$gte': period_start}}},
        {'$group': {
            '_id': {'y': {'$year': '$completed_at'}, 'm': {'$month': '$completed_at'}},
            'total': {'$sum': {'$add': [{'$ifNull': ['$labor_cost', 0]}, {'$ifNull': ['$parts_cost', 0]}]}},
        }},
    ])
    repairs_by_month = {(r['_id']['y'], r['_id']['m']): r['total'] for r in repair_rows}

    # Витрати на пальне: паливні накладні за датою
    fuel_rows = mongo.db.fuel_invoices.aggregate([
        {'$match': {'date': {'$gte': period_start}, 'total_amount': {'$exists': True}}},
        {'$group': {'_id': {'y': {'$year': '$date'}, 'm': {'$month': '$date'}}, 'total': {'$sum': '$total_amount'}}},
    ])
    fuel_by_month = {(r['_id']['y'], r['_id']['m']): r['total'] for r in fuel_rows}

    monthly_costs = [{
        'month': f"{MONTH_LABELS[d.month - 1]} {d.year % 100:02d}",
        'repairs': round(repairs_by_month.get((d.year, d.month), 0), 2),
        'fuel': round(fuel_by_month.get((d.year, d.month), 0), 2),
    } for d in starts]

    # Несправності за категоріями (за той самий період)
    fault_rows = mongo.db.fault_reports.aggregate([
        {'$match': {'report_date': {'$gte': period_start}}},
        {'$group': {'_id': '$category', 'count': {'$sum': 1}}},
    ])
    # Категорії поза довідником об'єднуємо в «Інше»
    fault_counts = {}
    for r in fault_rows:
        key = r['_id'] if r['_id'] in FAULT_CATEGORY_LABELS else 'other'
        fault_counts[key] = fault_counts.get(key, 0) + r['count']
    faults_by_category = sorted(({
        'category': key,
        'label': FAULT_CATEGORY_LABELS[key],
        'count': count,
    } for key, count in fault_counts.items()), key=lambda x: -x['count'])

    # Автопарк за типом пального (без списаних)
    fuel_type_rows = mongo.db.vehicles.aggregate([
        {'$match': {'status': {'$ne': 'decommissioned'}}},
        {'$group': {'_id': {'$ifNull': ['$fuel_type', 'diesel']}, 'count': {'$sum': 1}}},
        {'$sort': {'count': -1}},
    ])
    fleet_by_fuel = [{
        'fuel_type': r['_id'],
        'label': FUEL_TYPE_LABELS.get(r['_id'], r['_id']),
        'count': r['count'],
    } for r in fuel_type_rows]

    return jsonify({
        'success': True,
        'analytics': {
            'monthly_costs': monthly_costs,
            'faults_by_category': faults_by_category,
            'fleet_by_fuel': fleet_by_fuel,
        }
    })


# ---------------------------------------------------------------------------
# Календар ТО і ремонтів
# ---------------------------------------------------------------------------
def _as_datetime(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00')).replace(tzinfo=None)
        except ValueError:
            return None
    return None


@reports_bp.route('/maintenance-calendar', methods=['GET'])
@require_auth
@require_role('manager', 'mechanic')
def maintenance_calendar():
    """
    Події календаря за місяць:
    - planned_maintenance: планова дата наступного ТО автомобіля;
    - repair: заплановані та виконувані ремонти / ТО (за scheduled_date).
    Параметри: year, month (за замовчуванням - поточний місяць).
    """
    now = datetime.utcnow()
    try:
        year = int(request.args.get('year', now.year))
        month = int(request.args.get('month', now.month))
        start = datetime(year, month, 1)
    except (TypeError, ValueError):
        return jsonify({'success': False, 'error': 'Невірний рік або місяць.'}), 400
    end = datetime(year + (month == 12), month % 12 + 1, 1)
    today = now.date()

    events = []

    vehicles = list(mongo.db.vehicles.find({'status': {'$ne': 'decommissioned'}}))
    plates = {str(v['_id']): v['plate_number'] for v in vehicles}
    for v in vehicles:
        due = _as_datetime(v.get('next_maintenance_date'))
        if due and start <= due < end:
            events.append({
                'date': due.strftime('%Y-%m-%d'),
                'type': 'planned_maintenance',
                'status': 'overdue' if due.date() < today else 'planned',
                'title': f"ТО: {v['plate_number']}",
                'vehicle_id': str(v['_id']),
                'plate_number': v['plate_number'],
                'details': f"{v.get('brand', '')} {v.get('model', '')}, план: {v.get('next_maintenance_km', '—')} км",
            })

    repairs = mongo.db.repairs.find({
        'scheduled_date': {'$gte': start, '$lt': end},
        'status': {'$in': ['planned', 'in_progress', 'completed']},
    })
    type_labels = {'maintenance': 'ТО', 'repair': 'Рем.', 'inspection': 'Огл.'}  # короткі підписи для клітинок календаря
    for r in repairs:
        plate = plates.get(r.get('vehicle_id'), '—')
        events.append({
            'date': r['scheduled_date'].strftime('%Y-%m-%d'),
            'type': 'repair',
            'repair_type': r.get('repair_type'),
            'status': r.get('status'),
            'title': f"{type_labels.get(r.get('repair_type'), 'Роботи')}: {plate}",
            'repair_id': str(r['_id']),
            'vehicle_id': r.get('vehicle_id'),
            'plate_number': plate,
            'details': (r.get('description') or '')[:120],
        })

    events.sort(key=lambda e: (e['date'], e['type']))
    return jsonify({
        'success': True,
        'year': year,
        'month': month,
        'events': events,
    })
