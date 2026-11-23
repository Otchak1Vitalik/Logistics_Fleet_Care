"""
Маршрути управління транспортними засобами
"""
from datetime import datetime
from flask import Blueprint, request, jsonify, g
from bson import ObjectId
from marshmallow import ValidationError

from extensions import mongo
from services.lookup import fetch_by_ids
from services.maintenance_forecast import forecast_for_vehicle
from middleware.auth_middleware import require_auth, require_role
from models.vehicle import VehicleSchema, VehicleCreateSchema, VehicleUpdateSchema

vehicles_bp = Blueprint('vehicles', __name__)
vehicle_schema = VehicleSchema()
vehicles_schema = VehicleSchema(many=True)
create_schema = VehicleCreateSchema()
update_schema = VehicleUpdateSchema()


@vehicles_bp.route('', methods=['GET'])
@require_auth
def get_vehicles():
    """
    Отримання списку транспортних засобів.
    Водії бачать тільки авто, на які мають активну путівку.
    Механіки та керівники бачать всі.
    """
    status = request.args.get('status')
    fuel_type = request.args.get('fuel_type')

    # Водії бачать тільки своє закріплене авто
    if g.current_user['role'] == 'driver':
        # Знаходимо активні путівки водія
        active_waybills = list(mongo.db.waybills.find({
            'driver_id': g.current_user['_id'],
            'status': {'$in': ['issued', 'active']}
        }))
        vehicle_ids = [ObjectId(wb['vehicle_id']) for wb in active_waybills]

        if not vehicle_ids:
            return jsonify({
                'success': True,
                'vehicles': [],
                'total': 0
            })

        vehicles = list(mongo.db.vehicles.find({'_id': {'$in': vehicle_ids}}).sort('plate_number', 1))
    else:
        query = {}
        if status:
            query['status'] = status
        if fuel_type:
            query['fuel_type'] = fuel_type
        vehicles = list(mongo.db.vehicles.find(query).sort('plate_number', 1))

    return jsonify({
        'success': True,
        'vehicles': vehicles_schema.dump(vehicles),
        'total': len(vehicles)
    })


@vehicles_bp.route('/<vehicle_id>', methods=['GET'])
@require_auth
def get_vehicle(vehicle_id):
    """
    Отримання даних конкретного транспортного засобу.
    """
    try:
        vehicle = mongo.db.vehicles.find_one({'_id': ObjectId(vehicle_id)})
    except:
        return jsonify({
            'success': False,
            'error': 'Невірний формат ID.'
        }), 400

    if not vehicle:
        return jsonify({
            'success': False,
            'error': 'Транспортний засіб не знайдено.'
        }), 404

    return jsonify({
        'success': True,
        'vehicle': vehicle_schema.dump(vehicle),
        'maintenance_forecast': forecast_for_vehicle(mongo.db, vehicle)
    })


@vehicles_bp.route('', methods=['POST'])
@require_auth
@require_role('manager')
def create_vehicle():
    """
    Створення нового транспортного засобу.
    """
    try:
        data = create_schema.load(request.get_json())
    except ValidationError as err:
        return jsonify({
            'success': False,
            'error': 'Помилка валідації.',
            'details': err.messages
        }), 400

    # Перевірка унікальності номерного знаку
    existing = mongo.db.vehicles.find_one({'plate_number': data['plate_number'].upper()})
    if existing:
        return jsonify({
            'success': False,
            'error': f'Транспорт з номером "{data["plate_number"]}" вже існує.'
        }), 400

    # Допоміжна функція для конвертації date в datetime
    def to_datetime(d):
        if d and hasattr(d, 'year') and not hasattr(d, 'hour'):
            return datetime(d.year, d.month, d.day)
        return d

    # Підготовка документа
    vehicle_doc = {
        'plate_number': data['plate_number'].upper(),
        'brand': data['brand'],
        'model': data['model'],
        'year': data.get('year'),
        'vin': data.get('vin', '').upper() if data.get('vin') else None,
        'status': 'active',
        'fuel_type': data.get('fuel_type', 'diesel'),
        'fuel_norm': data.get('fuel_norm', 25.0),
        'tank_capacity': data.get('tank_capacity'),
        'odometer': data.get('odometer', 0),
        'last_maintenance_km': data.get('odometer', 0),
        'last_maintenance_date': datetime.utcnow(),
        'next_maintenance_km': data.get('next_maintenance_km'),
        'next_maintenance_date': to_datetime(data.get('next_maintenance_date')),
        'inspection_expiry': to_datetime(data.get('inspection_expiry')),
        'insurance_policy': data.get('insurance_policy'),
        'insurance_expiry': to_datetime(data.get('insurance_expiry')),
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow(),
        'created_by': g.current_user['_id']
    }

    result = mongo.db.vehicles.insert_one(vehicle_doc)
    vehicle_doc['_id'] = result.inserted_id

    return jsonify({
        'success': True,
        'message': 'Транспортний засіб додано.',
        'vehicle': vehicle_schema.dump(vehicle_doc)
    }), 201


@vehicles_bp.route('/<vehicle_id>', methods=['PUT'])
@require_auth
@require_role('manager', 'mechanic')
def update_vehicle(vehicle_id):
    """
    Оновлення даних транспортного засобу.
    Керівник може все, механік - тільки статус та дані ТО.
    """
    try:
        data = update_schema.load(request.get_json())
    except ValidationError as err:
        return jsonify({
            'success': False,
            'error': 'Помилка валідації.',
            'details': err.messages
        }), 400

    try:
        vehicle = mongo.db.vehicles.find_one({'_id': ObjectId(vehicle_id)})
    except:
        return jsonify({
            'success': False,
            'error': 'Невірний формат ID.'
        }), 400

    if not vehicle:
        return jsonify({
            'success': False,
            'error': 'Транспортний засіб не знайдено.'
        }), 404

    # Механік може змінювати тільки певні поля
    if g.current_user['role'] == 'mechanic':
        allowed_fields = ['status', 'odometer', 'last_maintenance_km', 'last_maintenance_date',
                          'next_maintenance_km', 'next_maintenance_date', 'inspection_date', 'inspection_expiry']
        data = {k: v for k, v in data.items() if k in allowed_fields}

    # Перевірка унікальності номерного знаку при зміні
    if 'plate_number' in data:
        existing = mongo.db.vehicles.find_one({
            'plate_number': data['plate_number'].upper(),
            '_id': {'$ne': ObjectId(vehicle_id)}
        })
        if existing:
            return jsonify({
                'success': False,
                'error': f'Транспорт з номером "{data["plate_number"]}" вже існує.'
            }), 400
        data['plate_number'] = data['plate_number'].upper()

    # Оновлення
    update_data = {k: v for k, v in data.items() if v is not None}
    update_data['updated_at'] = datetime.utcnow()

    # Конвертуємо date в datetime для MongoDB
    date_fields = ['next_maintenance_date', 'last_maintenance_date', 'inspection_date',
                   'inspection_expiry', 'insurance_expiry']
    for field in date_fields:
        if field in update_data:
            val = update_data[field]
            if val and hasattr(val, 'year') and not hasattr(val, 'hour'):
                update_data[field] = datetime(val.year, val.month, val.day)

    mongo.db.vehicles.update_one(
        {'_id': ObjectId(vehicle_id)},
        {'$set': update_data}
    )

    updated_vehicle = mongo.db.vehicles.find_one({'_id': ObjectId(vehicle_id)})

    return jsonify({
        'success': True,
        'message': 'Дані транспортного засобу оновлено.',
        'vehicle': vehicle_schema.dump(updated_vehicle)
    })


@vehicles_bp.route('/<vehicle_id>/odometer', methods=['PUT'])
@require_auth
def update_odometer(vehicle_id):
    """
    Оновлення пробігу транспортного засобу.
    Доступно всім (водії оновлюють при завершенні путівки).
    """
    data = request.get_json()
    new_odometer = data.get('odometer')

    if new_odometer is None or new_odometer < 0:
        return jsonify({
            'success': False,
            'error': 'Невірне значення пробігу.'
        }), 400

    try:
        vehicle = mongo.db.vehicles.find_one({'_id': ObjectId(vehicle_id)})
    except:
        return jsonify({
            'success': False,
            'error': 'Невірний формат ID.'
        }), 400

    if not vehicle:
        return jsonify({
            'success': False,
            'error': 'Транспортний засіб не знайдено.'
        }), 404

    # Пробіг не може зменшуватися
    if new_odometer < vehicle.get('odometer', 0):
        return jsonify({
            'success': False,
            'error': 'Новий пробіг не може бути меншим за поточний.'
        }), 400

    mongo.db.vehicles.update_one(
        {'_id': ObjectId(vehicle_id)},
        {
            '$set': {
                'odometer': new_odometer,
                'updated_at': datetime.utcnow()
            }
        }
    )

    return jsonify({
        'success': True,
        'message': 'Пробіг оновлено.',
        'odometer': new_odometer
    })


@vehicles_bp.route('/<vehicle_id>/history', methods=['GET'])
@require_auth
@require_role('manager', 'mechanic')
def get_vehicle_history(vehicle_id):
    """
    Повна історія транспортного засобу («медична карта»): хронологія путівок,
    несправностей, ремонтів і заправок, підсумки витрат і прогноз ТО.
    """
    try:
        vehicle = mongo.db.vehicles.find_one({'_id': ObjectId(vehicle_id)})
    except Exception:
        return jsonify({'success': False, 'error': 'Невірний формат ID.'}), 400
    if not vehicle:
        return jsonify({'success': False, 'error': 'Транспортний засіб не знайдено.'}), 404

    waybills = list(mongo.db.waybills.find({'vehicle_id': vehicle_id}).sort('created_at', -1))
    repairs = list(mongo.db.repairs.find({'vehicle_id': vehicle_id}).sort('created_at', -1))
    faults = list(mongo.db.fault_reports.find({'vehicle_id': vehicle_id}).sort('report_date', -1))
    fuel = list(mongo.db.fuel_records.find({'vehicle_id': vehicle_id}).sort('date', -1))
    for item in waybills + repairs + faults + fuel:
        item['_id'] = str(item['_id'])

    users = fetch_by_ids(mongo.db.users, {w.get('driver_id') for w in waybills} |
                         {f.get('reported_by') for f in faults} | {r.get('mechanic_id') for r in repairs})
    name = lambda uid: (users.get(uid) or {}).get('full_name')

    timeline = []
    for w in waybills:
        distance = (w['odometer_end'] - w['odometer_start']) if w.get('odometer_end') else None
        timeline.append({
            'type': 'waybill', 'id': w['_id'], 'date': w.get('completed_at') or w.get('issue_date') or w.get('created_at'),
            'number': w.get('number'), 'status': w.get('status'),
            'title': ' → '.join(x for x in (w.get('route_from'), w.get('route_to')) if x) or w.get('route_description'),
            'person': name(w.get('driver_id')), 'distance': distance, 'fuel': w.get('fuel_used'),
        })
    for f in faults:
        timeline.append({
            'type': 'fault', 'id': f['_id'], 'date': f.get('report_date'), 'number': f.get('number'),
            'status': f.get('status'), 'title': f.get('description'),
            'severity': f.get('severity'), 'person': name(f.get('reported_by')),
        })
    for r in repairs:
        cost = (r.get('labor_cost') or 0) + (r.get('parts_cost') or 0)
        timeline.append({
            'type': 'repair', 'id': r['_id'], 'date': r.get('completed_at') or r.get('started_at') or r.get('scheduled_date'),
            'number': r.get('number'), 'status': r.get('status'), 'repair_type': r.get('repair_type'),
            'title': r.get('work_performed') or r.get('description'), 'person': name(r.get('mechanic_id')),
            'cost': cost or None, 'parts': [p.get('name') for p in r.get('parts_used') or [] if p.get('name')],
        })
    for x in fuel:
        timeline.append({
            'type': 'fuel', 'id': x['_id'], 'date': x.get('date'), 'record_type': x.get('record_type'),
            'title': x.get('station'), 'fuel': x.get('quantity'), 'cost': x.get('total_amount'),
        })
    timeline = [t for t in timeline if t.get('date')]
    timeline.sort(key=lambda t: t['date'], reverse=True)

    completed_waybills = [w for w in waybills if w.get('status') == 'completed' and w.get('odometer_end')]
    completed_repairs = [r for r in repairs if r.get('status') == 'completed']
    totals = {
        'waybills': len(waybills),
        'distance': sum(max(0, w['odometer_end'] - w['odometer_start']) for w in completed_waybills),
        'fuel_used': round(sum(w.get('fuel_used') or 0 for w in completed_waybills), 1),
        'faults': len(faults),
        'open_faults': sum(1 for f in faults if f.get('status') in ('new', 'acknowledged', 'in_repair')),
        'repairs': len(completed_repairs),
        'repairs_cost': round(sum((r.get('labor_cost') or 0) + (r.get('parts_cost') or 0) for r in completed_repairs), 2),
        'fuel_cost': round(sum(x.get('total_amount') or 0 for x in fuel), 2),
    }

    return jsonify({
        'success': True,
        'vehicle': vehicle_schema.dump(vehicle),
        'maintenance_forecast': forecast_for_vehicle(mongo.db, vehicle),
        'totals': totals,
        'timeline': timeline,
        # Попередній формат (останні 10 записів) - для сумісності
        'waybills': waybills[:10],
        'repairs': repairs[:10],
        'faults': faults[:10],
    })
