"""
Маршрути управління транспортними засобами
"""
from datetime import datetime
from flask import Blueprint, request, jsonify, g
from bson import ObjectId
from marshmallow import ValidationError

from extensions import mongo
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
        'vehicle': vehicle_schema.dump(vehicle)
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
    Отримання історії транспортного засобу (путівки, ремонти, несправності).
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

    # Останні путівки
    waybills = list(mongo.db.waybills.find(
        {'vehicle_id': vehicle_id}
    ).sort('created_at', -1).limit(10))

    # Останні ремонти
    repairs = list(mongo.db.repairs.find(
        {'vehicle_id': vehicle_id}
    ).sort('created_at', -1).limit(10))

    # Останні несправності
    faults = list(mongo.db.fault_reports.find(
        {'vehicle_id': vehicle_id}
    ).sort('created_at', -1).limit(10))

    # Конвертація ObjectId в строки
    for item in waybills + repairs + faults:
        item['_id'] = str(item['_id'])

    return jsonify({
        'success': True,
        'vehicle': vehicle_schema.dump(vehicle),
        'waybills': waybills,
        'repairs': repairs,
        'faults': faults
    })
