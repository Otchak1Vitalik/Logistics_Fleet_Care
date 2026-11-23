"""
Маршрути управління ремонтами та ТО
"""
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, g
from bson import ObjectId
from marshmallow import ValidationError

from config import Constants
from extensions import mongo
from middleware.auth_middleware import require_auth, require_role
from models.repair import RepairSchema, RepairCreateSchema, RepairUpdateSchema
from services.doc_generator import generate_doc_number
from services.lookup import fetch_by_ids

repairs_bp = Blueprint('repairs', __name__)
repair_schema = RepairSchema()
repairs_schema = RepairSchema(many=True)
create_schema = RepairCreateSchema()
update_schema = RepairUpdateSchema()


def enrich_repair(repair, cache=None):
    """
    Додає пов'язані дані до ремонту.
    cache - попередньо завантажені документи (для списків, щоб уникнути N+1 запитів).
    """
    if cache is not None:
        for key, field, target in (('vehicles', 'vehicle_id', 'vehicle'),
                                   ('users', 'mechanic_id', 'mechanic'),
                                   ('faults', 'fault_id', 'fault')):
            doc = cache[key].get(repair.get(field))
            if doc:
                repair[target] = doc
        return repair

    if repair.get('vehicle_id'):
        vehicle = mongo.db.vehicles.find_one({'_id': ObjectId(repair['vehicle_id'])})
        if vehicle:
            vehicle['_id'] = str(vehicle['_id'])
            repair['vehicle'] = vehicle

    if repair.get('mechanic_id'):
        mechanic = mongo.db.users.find_one({'_id': ObjectId(repair['mechanic_id'])})
        if mechanic:
            mechanic['_id'] = str(mechanic['_id'])
            if 'password_hash' in mechanic:
                del mechanic['password_hash']
            repair['mechanic'] = mechanic

    if repair.get('fault_id'):
        fault = mongo.db.fault_reports.find_one({'_id': ObjectId(repair['fault_id'])})
        if fault:
            fault['_id'] = str(fault['_id'])
            repair['fault'] = fault

    return repair


def build_repair_cache(repairs):
    """Пакетно завантажує авто, механіків і несправності для списку ремонтів."""
    return {
        'vehicles': fetch_by_ids(mongo.db.vehicles, {r.get('vehicle_id') for r in repairs}),
        'users': fetch_by_ids(mongo.db.users, {r.get('mechanic_id') for r in repairs}),
        'faults': fetch_by_ids(mongo.db.fault_reports, {r.get('fault_id') for r in repairs}),
    }


def release_vehicle_if_free(vehicle_id, closing_repair_id):
    """
    Переводить авто в статус active, лише якщо для нього немає інших ремонтів у роботі.
    """
    other_active = mongo.db.repairs.count_documents({
        'vehicle_id': vehicle_id,
        'status': 'in_progress',
        '_id': {'$ne': ObjectId(closing_repair_id)}
    })
    if other_active == 0:
        mongo.db.vehicles.update_one(
            {'_id': ObjectId(vehicle_id), 'status': 'repair'},
            {'$set': {'status': 'active', 'updated_at': datetime.utcnow()}}
        )


def schedule_next_maintenance(vehicle_id):
    """
    Автоматичне планування наступного ТО після виконання поточного.
    Інтервали (км і дні) беруться з налаштувань системи, які задає керівник.
    """
    settings = mongo.db.settings.find_one({'_id': 'system'}) or {}
    interval_km = settings.get('maintenance_interval_km', Constants.MAINTENANCE_INTERVAL_KM)
    interval_days = settings.get('maintenance_interval_days', Constants.MAINTENANCE_INTERVAL_DAYS)

    vehicle = mongo.db.vehicles.find_one({'_id': ObjectId(vehicle_id)})
    odometer = vehicle.get('odometer', 0)
    now = datetime.utcnow()
    mongo.db.vehicles.update_one(
        {'_id': ObjectId(vehicle_id)},
        {
            '$set': {
                'last_maintenance_km': odometer,
                'last_maintenance_date': now,
                'next_maintenance_km': odometer + interval_km,
                'next_maintenance_date': now + timedelta(days=interval_days),
                'updated_at': now
            }
        }
    )
    # Знімаємо застарілі сповіщення про ТО для цього авто
    mongo.db.alerts.update_many(
        {'related_type': 'vehicle', 'related_id': vehicle_id, 'category': 'maintenance', 'is_dismissed': False},
        {'$set': {'is_dismissed': True, 'dismissed_at': now}}
    )


@repairs_bp.route('', methods=['GET'])
@require_auth
@require_role('mechanic', 'manager')
def get_repairs():
    """
    Отримання списку ремонтів/ТО.
    """
    status = request.args.get('status')
    vehicle_id = request.args.get('vehicle_id')
    mechanic_id = request.args.get('mechanic_id')
    repair_type = request.args.get('type')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')

    query = {}

    if status:
        query['status'] = status
    if vehicle_id:
        query['vehicle_id'] = vehicle_id
    if mechanic_id:
        query['mechanic_id'] = mechanic_id
    if repair_type:
        query['repair_type'] = repair_type

    if date_from or date_to:
        query['scheduled_date'] = {}
        if date_from:
            query['scheduled_date']['$gte'] = datetime.fromisoformat(date_from)
        if date_to:
            query['scheduled_date']['$lte'] = datetime.fromisoformat(date_to)

    repairs = list(mongo.db.repairs.find(query).sort('scheduled_date', -1))

    cache = build_repair_cache(repairs)
    for repair in repairs:
        repair['_id'] = str(repair['_id'])
        enrich_repair(repair, cache)

    return jsonify({
        'success': True,
        'repairs': repairs,
        'total': len(repairs)
    })


@repairs_bp.route('/<repair_id>', methods=['GET'])
@require_auth
@require_role('mechanic', 'manager')
def get_repair(repair_id):
    """
    Отримання конкретного ремонту.
    """
    try:
        repair = mongo.db.repairs.find_one({'_id': ObjectId(repair_id)})
    except:
        return jsonify({
            'success': False,
            'error': 'Невірний формат ID.'
        }), 400

    if not repair:
        return jsonify({
            'success': False,
            'error': 'Ремонт не знайдено.'
        }), 404

    repair['_id'] = str(repair['_id'])
    enrich_repair(repair)

    return jsonify({
        'success': True,
        'repair': repair
    })


@repairs_bp.route('', methods=['POST'])
@require_auth
@require_role('mechanic', 'manager')
def create_repair():
    """
    Створення ремонту/ТО.
    """
    try:
        data = create_schema.load(request.get_json())
    except ValidationError as err:
        return jsonify({
            'success': False,
            'error': 'Помилка валідації.',
            'details': err.messages
        }), 400

    # Перевірка існування авто
    vehicle = mongo.db.vehicles.find_one({'_id': ObjectId(data['vehicle_id'])})
    if not vehicle:
        return jsonify({
            'success': False,
            'error': 'Транспортний засіб не знайдено.'
        }), 400

    # Якщо вказана несправність - перевіряємо її
    if data.get('fault_id'):
        fault = mongo.db.fault_reports.find_one({'_id': ObjectId(data['fault_id'])})
        if not fault:
            return jsonify({
                'success': False,
                'error': 'Несправність не знайдено.'
            }), 400

    doc_number = generate_doc_number(mongo.db, 'repair')

    # Конвертуємо date в datetime для MongoDB
    scheduled_date = data.get('scheduled_date')
    if scheduled_date and hasattr(scheduled_date, 'year') and not hasattr(scheduled_date, 'hour'):
        scheduled_date = datetime(scheduled_date.year, scheduled_date.month, scheduled_date.day)

    repair_doc = {
        'number': doc_number,
        'vehicle_id': data['vehicle_id'],
        'mechanic_id': data.get('mechanic_id') or g.current_user['_id'],
        'fault_id': data.get('fault_id'),
        'repair_type': data['repair_type'],
        'description': data['description'],
        'scheduled_date': scheduled_date,
        'started_at': None,
        'completed_at': None,
        'odometer': data.get('odometer') or vehicle.get('odometer'),
        'status': 'planned',
        'work_performed': None,
        'parts_used': [],
        'labor_hours': None,
        'labor_cost': None,
        'parts_cost': None,
        'notes': data.get('notes'),
        'cancellation_reason': None,
        'created_by': g.current_user['_id'],
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow()
    }

    result = mongo.db.repairs.insert_one(repair_doc)
    repair_doc['_id'] = str(result.inserted_id)

    # Оновлюємо статус несправності
    if data.get('fault_id'):
        mongo.db.fault_reports.update_one(
            {'_id': ObjectId(data['fault_id'])},
            {
                '$set': {
                    'status': 'in_repair',
                    'repair_id': str(result.inserted_id),
                    'updated_at': datetime.utcnow()
                }
            }
        )

    enrich_repair(repair_doc)

    return jsonify({
        'success': True,
        'message': f'Ремонт {doc_number} створено.',
        'repair': repair_doc
    }), 201


@repairs_bp.route('/<repair_id>', methods=['PUT'])
@require_auth
@require_role('mechanic', 'manager')
def update_repair(repair_id):
    """
    Оновлення ремонту.
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
        repair = mongo.db.repairs.find_one({'_id': ObjectId(repair_id)})
    except:
        return jsonify({
            'success': False,
            'error': 'Невірний формат ID.'
        }), 400

    if not repair:
        return jsonify({
            'success': False,
            'error': 'Ремонт не знайдено.'
        }), 404

    new_status = data.get('status')
    current_status = repair.get('status')

    # Допустимі переходи статусів ремонту (скінченний автомат)
    allowed_transitions = {
        'planned': {'in_progress', 'cancelled'},
        'in_progress': {'completed', 'cancelled'},
        'completed': set(),
        'cancelled': set(),
    }
    if new_status and new_status != current_status and \
            new_status not in allowed_transitions.get(current_status, set()):
        return jsonify({
            'success': False,
            'error': f'Неможливо змінити статус ремонту з «{current_status}» на «{new_status}».'
        }), 400
    if new_status and new_status == current_status and current_status in ('completed', 'cancelled'):
        return jsonify({
            'success': False,
            'error': 'Ремонт вже закрито, повторна зміна статусу неможлива.'
        }), 400

    update_data = {k: v for k, v in data.items() if v is not None}
    update_data['updated_at'] = datetime.utcnow()

    # Конвертуємо date в datetime для MongoDB
    if 'scheduled_date' in update_data:
        sd = update_data['scheduled_date']
        if sd and hasattr(sd, 'year') and not hasattr(sd, 'hour'):
            update_data['scheduled_date'] = datetime(sd.year, sd.month, sd.day)

    # Логіка переходів статусів
    if new_status == 'in_progress' and current_status == 'planned':
        update_data['started_at'] = datetime.utcnow()
        # Ставимо авто в ремонт
        mongo.db.vehicles.update_one(
            {'_id': ObjectId(repair['vehicle_id'])},
            {'$set': {'status': 'repair', 'updated_at': datetime.utcnow()}}
        )

    if new_status == 'completed':
        if not data.get('work_performed'):
            return jsonify({
                'success': False,
                'error': 'Вкажіть виконані роботи.'
            }), 400
        update_data['completed_at'] = datetime.utcnow()

        # Повертаємо авто в активний статус, якщо немає інших ремонтів у роботі
        release_vehicle_if_free(repair['vehicle_id'], repair_id)

        # Якщо це ТО - автоматично плануємо наступне ТО за інтервалами з налаштувань
        if repair.get('repair_type') == 'maintenance':
            schedule_next_maintenance(repair['vehicle_id'])

        # Закриваємо пов'язану несправність
        if repair.get('fault_id'):
            mongo.db.fault_reports.update_one(
                {'_id': ObjectId(repair['fault_id'])},
                {
                    '$set': {
                        'status': 'resolved',
                        'resolution': data.get('work_performed'),
                        'resolved_at': datetime.utcnow(),
                        'updated_at': datetime.utcnow()
                    }
                }
            )

    if new_status == 'cancelled':
        if not data.get('cancellation_reason'):
            return jsonify({
                'success': False,
                'error': 'Вкажіть причину скасування.'
            }), 400
        # Повертаємо авто в активний статус, якщо було в ремонті і немає інших ремонтів
        if current_status == 'in_progress':
            release_vehicle_if_free(repair['vehicle_id'], repair_id)

    mongo.db.repairs.update_one(
        {'_id': ObjectId(repair_id)},
        {'$set': update_data}
    )

    updated_repair = mongo.db.repairs.find_one({'_id': ObjectId(repair_id)})
    updated_repair['_id'] = str(updated_repair['_id'])
    enrich_repair(updated_repair)

    return jsonify({
        'success': True,
        'message': 'Ремонт оновлено.',
        'repair': updated_repair
    })


@repairs_bp.route('/scheduled', methods=['GET'])
@require_auth
@require_role('mechanic', 'manager')
def get_scheduled_repairs():
    """
    Заплановані ремонти/ТО.
    """
    repairs = list(mongo.db.repairs.find({
        'status': {'$in': ['planned', 'in_progress']}
    }).sort('scheduled_date', 1))

    cache = build_repair_cache(repairs)
    for repair in repairs:
        repair['_id'] = str(repair['_id'])
        enrich_repair(repair, cache)

    return jsonify({
        'success': True,
        'repairs': repairs,
        'total': len(repairs)
    })


@repairs_bp.route('/statistics', methods=['GET'])
@require_auth
@require_role('manager')
def repair_statistics():
    """
    Статистика по ремонтах.
    """
    # По статусах
    by_status = list(mongo.db.repairs.aggregate([
        {'$group': {'_id': '$status', 'count': {'$sum': 1}}}
    ]))

    # По типах
    by_type = list(mongo.db.repairs.aggregate([
        {'$group': {'_id': '$repair_type', 'count': {'$sum': 1}}}
    ]))

    # Витрати за останній місяць
    month_ago = datetime.utcnow().replace(day=1)
    costs = list(mongo.db.repairs.aggregate([
        {'$match': {'completed_at': {'$gte': month_ago}, 'status': 'completed'}},
        {
            '$group': {
                '_id': None,
                'total_labor': {'$sum': {'$ifNull': ['$labor_cost', 0]}},
                'total_parts': {'$sum': {'$ifNull': ['$parts_cost', 0]}},
                'count': {'$sum': 1}
            }
        }
    ]))

    return jsonify({
        'success': True,
        'by_status': by_status,
        'by_type': by_type,
        'monthly_costs': costs[0] if costs else {'total_labor': 0, 'total_parts': 0, 'count': 0}
    })
