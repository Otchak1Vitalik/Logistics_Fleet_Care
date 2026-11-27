"""
Маршрути управління путівками (подорожніми листами)
"""
from datetime import datetime
from flask import Blueprint, request, jsonify, g
from bson import ObjectId
from marshmallow import ValidationError

from extensions import mongo
from middleware.auth_middleware import require_auth, require_role
from models.waybill import WaybillSchema, WaybillCreateSchema, WaybillUpdateSchema
from services.doc_generator import generate_doc_number

waybills_bp = Blueprint('waybills', __name__)
waybill_schema = WaybillSchema()
waybills_schema = WaybillSchema(many=True)
create_schema = WaybillCreateSchema()
update_schema = WaybillUpdateSchema()


def enrich_waybill(waybill):
    """Додає пов'язані дані до путівки."""
    if waybill.get('vehicle_id'):
        vehicle = mongo.db.vehicles.find_one({'_id': ObjectId(waybill['vehicle_id'])})
        if vehicle:
            vehicle['_id'] = str(vehicle['_id'])
            waybill['vehicle'] = vehicle

    if waybill.get('driver_id'):
        driver = mongo.db.users.find_one({'_id': ObjectId(waybill['driver_id'])})
        if driver:
            driver['_id'] = str(driver['_id'])
            del driver['password_hash']
            waybill['driver'] = driver

    if waybill.get('issued_by'):
        issuer = mongo.db.users.find_one({'_id': ObjectId(waybill['issued_by'])})
        if issuer:
            issuer['_id'] = str(issuer['_id'])
            del issuer['password_hash']
            waybill['issuer'] = issuer

    return waybill


@waybills_bp.route('', methods=['GET'])
@require_auth
def get_waybills():
    """
    Отримання списку путівок.
    Водії бачать тільки свої, інші - всі.
    """
    status = request.args.get('status')
    vehicle_id = request.args.get('vehicle_id')
    driver_id = request.args.get('driver_id')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')

    query = {}

    # Водії бачать тільки свої путівки
    if g.current_user['role'] == 'driver':
        query['driver_id'] = g.current_user['_id']
    elif driver_id:
        query['driver_id'] = driver_id

    if status:
        query['status'] = status
    if vehicle_id:
        query['vehicle_id'] = vehicle_id

    # Фільтр за датами
    if date_from or date_to:
        query['issue_date'] = {}
        if date_from:
            query['issue_date']['$gte'] = datetime.fromisoformat(date_from)
        if date_to:
            query['issue_date']['$lte'] = datetime.fromisoformat(date_to)

    waybills = list(mongo.db.waybills.find(query).sort('created_at', -1))

    # Збагачення даними
    for wb in waybills:
        wb['_id'] = str(wb['_id'])
        enrich_waybill(wb)

    return jsonify({
        'success': True,
        'waybills': waybills,
        'total': len(waybills)
    })


@waybills_bp.route('/<waybill_id>', methods=['GET'])
@require_auth
def get_waybill(waybill_id):
    """
    Отримання конкретної путівки.
    """
    try:
        waybill = mongo.db.waybills.find_one({'_id': ObjectId(waybill_id)})
    except:
        return jsonify({
            'success': False,
            'error': 'Невірний формат ID.'
        }), 400

    if not waybill:
        return jsonify({
            'success': False,
            'error': 'Путівку не знайдено.'
        }), 404

    # Водій може бачити тільки свої путівки
    if g.current_user['role'] == 'driver' and waybill.get('driver_id') != g.current_user['_id']:
        return jsonify({
            'success': False,
            'error': 'Доступ заборонено.'
        }), 403

    waybill['_id'] = str(waybill['_id'])
    enrich_waybill(waybill)

    return jsonify({
        'success': True,
        'waybill': waybill
    })


@waybills_bp.route('/<waybill_id>/pdf', methods=['GET'])
@require_auth
def waybill_pdf(waybill_id):
    """PDF путівного листа для друку (за зразком типової форми № 1). Доступ - як до самої путівки."""
    from flask import current_app, make_response
    from services.waybill_pdf import build_waybill_pdf
    from services.fuel_analyzer import calculate_fuel_norm

    try:
        waybill = mongo.db.waybills.find_one({'_id': ObjectId(waybill_id)})
    except Exception:  # noqa: BLE001
        return jsonify({'success': False, 'error': 'Невірний формат ID.'}), 400
    if not waybill:
        return jsonify({'success': False, 'error': 'Путівку не знайдено.'}), 404
    if g.current_user['role'] == 'driver' and waybill.get('driver_id') != g.current_user['_id']:
        return jsonify({'success': False, 'error': 'Доступ заборонено.'}), 403

    waybill['_id'] = str(waybill['_id'])
    enrich_waybill(waybill)
    settings = mongo.db.settings.find_one({'_id': 'system'}) or {}
    vehicle = waybill.get('vehicle') or {}
    start, end = waybill.get('odometer_start'), waybill.get('odometer_end')
    norm = None
    if isinstance(start, (int, float)) and isinstance(end, (int, float)) and end > start and vehicle.get('fuel_norm'):
        when = waybill.get('completed_at') or waybill.get('valid_from')
        norm = calculate_fuel_norm(end - start, vehicle['fuel_norm'], when if isinstance(when, datetime) else None, settings)

    pdf = build_waybill_pdf(
        waybill,
        company_name=settings.get('company_name') or 'KRUTII TRANS',
        verify_url=f"{current_app.config['FRONTEND_URL']}/w/{waybill['_id']}",
        norm_liters=norm,
    )
    filename = 'putivka-' + str(waybill.get('number', waybill['_id'])).replace('ПЛ', 'PL') + '.pdf'
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    mode = 'attachment' if request.args.get('download') == '1' else 'inline'   # ?download=1 - одразу зберегти файл
    response.headers['Content-Disposition'] = f'{mode}; filename="{filename}"'
    response.headers['Cache-Control'] = 'no-store'
    return response


@waybills_bp.route('', methods=['POST'])
@require_auth
@require_role('manager')
def create_waybill():
    """
    Створення нової путівки.
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

    if vehicle.get('status') != 'active':
        return jsonify({
            'success': False,
            'error': 'Транспортний засіб недоступний (не активний).'
        }), 400

    # Перевірка існування водія
    driver = mongo.db.users.find_one({
        '_id': ObjectId(data['driver_id']),
        'role': 'driver',
        'is_active': True
    })
    if not driver:
        return jsonify({
            'success': False,
            'error': 'Водія не знайдено або він неактивний.'
        }), 400

    # Перевірка, чи немає активної путівки на це авто
    active_waybill = mongo.db.waybills.find_one({
        'vehicle_id': data['vehicle_id'],
        'status': {'$in': ['issued', 'active']}
    })
    if active_waybill:
        return jsonify({
            'success': False,
            'error': 'На цей транспорт вже є активна путівка.'
        }), 400

    # Генерація номера документа
    doc_number = generate_doc_number(mongo.db, 'waybill')

    # Підготовка документа
    # Конвертуємо date в datetime для MongoDB (BSON не підтримує datetime.date)
    issue_date = data['issue_date']
    if hasattr(issue_date, 'year') and not hasattr(issue_date, 'hour'):
        issue_date = datetime(issue_date.year, issue_date.month, issue_date.day)

    waybill_doc = {
        'number': doc_number,
        'vehicle_id': data['vehicle_id'],
        'driver_id': data['driver_id'],
        'issued_by': g.current_user['_id'],
        'issue_date': issue_date,
        'valid_from': data['valid_from'],
        'valid_until': data['valid_until'],
        'route_from': data.get('route_from'),
        'route_to': data.get('route_to'),
        'route_description': data.get('route_description'),
        'odometer_start': data.get('odometer_start') or vehicle.get('odometer', 0),
        'odometer_end': None,
        'fuel_issued': data.get('fuel_issued', 0),
        'fuel_used': None,
        'fuel_remaining': None,
        'status': 'issued',
        'notes': data.get('notes'),
        'completion_notes': None,
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow(),
        'completed_at': None
    }

    result = mongo.db.waybills.insert_one(waybill_doc)
    waybill_doc['_id'] = str(result.inserted_id)
    enrich_waybill(waybill_doc)

    return jsonify({
        'success': True,
        'message': f'Путівку {doc_number} створено.',
        'waybill': waybill_doc
    }), 201


@waybills_bp.route('/<waybill_id>', methods=['PUT'])
@require_auth
def update_waybill(waybill_id):
    """
    Оновлення путівки.
    Водій може тільки активувати та завершувати свої путівки.
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
        waybill = mongo.db.waybills.find_one({'_id': ObjectId(waybill_id)})
    except:
        return jsonify({
            'success': False,
            'error': 'Невірний формат ID.'
        }), 400

    if not waybill:
        return jsonify({
            'success': False,
            'error': 'Путівку не знайдено.'
        }), 404

    current_status = waybill.get('status')
    new_status = data.get('status')

    # Водій може тільки свої путівки
    if g.current_user['role'] == 'driver':
        if waybill.get('driver_id') != g.current_user['_id']:
            return jsonify({
                'success': False,
                'error': 'Доступ заборонено.'
            }), 403

        # Водій може: issued -> active, active -> completed
        if new_status:
            if current_status == 'issued' and new_status != 'active':
                return jsonify({
                    'success': False,
                    'error': 'Можна тільки активувати путівку.'
                }), 400
            if current_status == 'active' and new_status != 'completed':
                return jsonify({
                    'success': False,
                    'error': 'Можна тільки завершити путівку.'
                }), 400
            if current_status in ['completed', 'cancelled']:
                return jsonify({
                    'success': False,
                    'error': 'Путівка вже завершена або скасована.'
                }), 400

    # Валідація при завершенні
    if new_status == 'completed':
        if not data.get('odometer_end'):
            return jsonify({
                'success': False,
                'error': 'Вкажіть кінцевий пробіг.'
            }), 400
        if data['odometer_end'] < waybill.get('odometer_start', 0):
            return jsonify({
                'success': False,
                'error': 'Кінцевий пробіг не може бути меншим за початковий.'
            }), 400

    # Оновлення
    update_data = {k: v for k, v in data.items() if v is not None}
    update_data['updated_at'] = datetime.utcnow()

    if new_status == 'completed':
        update_data['completed_at'] = datetime.utcnow()

        # Оновлюємо пробіг авто
        mongo.db.vehicles.update_one(
            {'_id': ObjectId(waybill['vehicle_id'])},
            {'$set': {'odometer': data['odometer_end'], 'updated_at': datetime.utcnow()}}
        )

        # Пробіг змінився - одразу перевіряємо потребу в ТО, не чекаючи щоденної перевірки
        from services.alert_engine import check_vehicle_maintenance
        from services.maintenance_forecast import daily_mileage
        vehicle = mongo.db.vehicles.find_one({'_id': ObjectId(waybill['vehicle_id'])})
        if vehicle:
            rate = daily_mileage(mongo.db, vehicle_ids=[waybill['vehicle_id']]).get(waybill['vehicle_id'])
            check_vehicle_maintenance(mongo.db, vehicle, avg_daily_km=rate)

    mongo.db.waybills.update_one(
        {'_id': ObjectId(waybill_id)},
        {'$set': update_data}
    )

    if new_status == 'completed':
        # новий рейс - одразу перевіряємо витрату пального на аномалії
        try:
            from services.fuel_anomalies import run_detection
            run_detection(mongo.db)
        except Exception as exc:  # noqa: BLE001 - аналітика не повинна заважати завершенню путівки
            from flask import current_app
            current_app.logger.warning('Перевірка аномалій пального не виконана: %s', exc)

    updated_waybill = mongo.db.waybills.find_one({'_id': ObjectId(waybill_id)})
    updated_waybill['_id'] = str(updated_waybill['_id'])
    enrich_waybill(updated_waybill)

    return jsonify({
        'success': True,
        'message': 'Путівку оновлено.',
        'waybill': updated_waybill
    })


@waybills_bp.route('/<waybill_id>/cancel', methods=['POST'])
@require_auth
@require_role('manager')
def cancel_waybill(waybill_id):
    """
    Скасування путівки (тільки керівник).
    """
    try:
        waybill = mongo.db.waybills.find_one({'_id': ObjectId(waybill_id)})
    except:
        return jsonify({
            'success': False,
            'error': 'Невірний формат ID.'
        }), 400

    if not waybill:
        return jsonify({
            'success': False,
            'error': 'Путівку не знайдено.'
        }), 404

    if waybill.get('status') == 'completed':
        return jsonify({
            'success': False,
            'error': 'Неможливо скасувати завершену путівку.'
        }), 400

    data = request.get_json() or {}

    mongo.db.waybills.update_one(
        {'_id': ObjectId(waybill_id)},
        {
            '$set': {
                'status': 'cancelled',
                'notes': data.get('reason', waybill.get('notes')),
                'updated_at': datetime.utcnow()
            }
        }
    )

    return jsonify({
        'success': True,
        'message': 'Путівку скасовано.'
    })


@waybills_bp.route('/active', methods=['GET'])
@require_auth
def get_active_waybill():
    """
    Отримання активної путівки поточного водія.
    """
    if g.current_user['role'] != 'driver':
        return jsonify({
            'success': False,
            'error': 'Тільки для водіїв.'
        }), 400

    waybill = mongo.db.waybills.find_one({
        'driver_id': g.current_user['_id'],
        'status': {'$in': ['issued', 'active']}
    })

    if not waybill:
        return jsonify({
            'success': True,
            'waybill': None
        })

    waybill['_id'] = str(waybill['_id'])
    enrich_waybill(waybill)

    return jsonify({
        'success': True,
        'waybill': waybill
    })
