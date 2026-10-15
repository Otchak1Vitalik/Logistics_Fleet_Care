"""
Маршрути звітів для керівника
"""
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, g
from bson import ObjectId

from extensions import mongo
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
            'status': status
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
