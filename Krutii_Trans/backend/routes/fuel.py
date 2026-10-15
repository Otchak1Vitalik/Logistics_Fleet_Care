"""
Маршрути управління паливом (накладні та записи)
"""
from datetime import datetime
from flask import Blueprint, request, jsonify, g
from bson import ObjectId
from marshmallow import ValidationError

from extensions import mongo
from middleware.auth_middleware import require_auth, require_role
from models.fuel import (
    FuelInvoiceSchema, FuelRecordSchema,
    FuelInvoiceCreateSchema, FuelRecordCreateSchema
)
from services.doc_generator import generate_doc_number
from services.fuel_analyzer import calculate_fuel_consumption, check_overspend

fuel_bp = Blueprint('fuel', __name__)
invoice_schema = FuelInvoiceSchema()
invoices_schema = FuelInvoiceSchema(many=True)
record_schema = FuelRecordSchema()
records_schema = FuelRecordSchema(many=True)
invoice_create_schema = FuelInvoiceCreateSchema()
record_create_schema = FuelRecordCreateSchema()


def enrich_record(record):
    """Додає пов'язані дані до запису."""
    # Нормалізація: source (seed) -> record_type (API)
    if 'source' in record and 'record_type' not in record:
        source_map = {'invoice': 'issue', 'station': 'external'}
        record['record_type'] = source_map.get(record['source'], 'issue')

    if record.get('vehicle_id'):
        vehicle = mongo.db.vehicles.find_one({'_id': ObjectId(record['vehicle_id'])})
        if vehicle:
            vehicle['_id'] = str(vehicle['_id'])
            record['vehicle'] = vehicle

    if record.get('driver_id'):
        driver = mongo.db.users.find_one({'_id': ObjectId(record['driver_id'])})
        if driver:
            driver['_id'] = str(driver['_id'])
            if 'password_hash' in driver:
                del driver['password_hash']
            record['driver'] = driver

    return record


# === Паливні накладні ===

@fuel_bp.route('/invoices', methods=['GET'])
@require_auth
@require_role('manager')
def get_invoices():
    """
    Отримання списку паливних накладних.
    """
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    fuel_type = request.args.get('fuel_type')

    query = {}
    if fuel_type:
        query['fuel_type'] = fuel_type

    if date_from or date_to:
        query['date'] = {}
        if date_from:
            query['date']['$gte'] = datetime.fromisoformat(date_from)
        if date_to:
            query['date']['$lte'] = datetime.fromisoformat(date_to)

    invoices = list(mongo.db.fuel_invoices.find(query).sort('date', -1))

    for inv in invoices:
        inv['_id'] = str(inv['_id'])

    return jsonify({
        'success': True,
        'invoices': invoices,
        'total': len(invoices)
    })


@fuel_bp.route('/invoices/<invoice_id>', methods=['GET'])
@require_auth
@require_role('manager')
def get_invoice(invoice_id):
    """
    Отримання конкретної накладної.
    """
    try:
        invoice = mongo.db.fuel_invoices.find_one({'_id': ObjectId(invoice_id)})
    except:
        return jsonify({
            'success': False,
            'error': 'Невірний формат ID.'
        }), 400

    if not invoice:
        return jsonify({
            'success': False,
            'error': 'Накладну не знайдено.'
        }), 404

    invoice['_id'] = str(invoice['_id'])

    # Отримуємо записи видачі по цій накладній
    records = list(mongo.db.fuel_records.find({'invoice_id': str(invoice['_id'])}))
    for rec in records:
        rec['_id'] = str(rec['_id'])
        enrich_record(rec)

    invoice['records'] = records

    return jsonify({
        'success': True,
        'invoice': invoice
    })


@fuel_bp.route('/invoices', methods=['POST'])
@require_auth
@require_role('manager')
def create_invoice():
    """
    Створення паливної накладної.
    """
    try:
        data = invoice_create_schema.load(request.get_json())
    except ValidationError as err:
        return jsonify({
            'success': False,
            'error': 'Помилка валідації.',
            'details': err.messages
        }), 400

    doc_number = generate_doc_number(mongo.db, 'fuel_invoice')

    total_amount = None
    if data.get('price_per_liter'):
        total_amount = data['quantity'] * data['price_per_liter']

    # Конвертуємо date в datetime для MongoDB
    invoice_date = data['date']
    if hasattr(invoice_date, 'year') and not hasattr(invoice_date, 'hour'):
        invoice_date = datetime(invoice_date.year, invoice_date.month, invoice_date.day)

    invoice_doc = {
        'number': doc_number,
        'date': invoice_date,
        'supplier': data.get('supplier'),
        'fuel_type': data['fuel_type'],
        'quantity': data['quantity'],
        'price_per_liter': data.get('price_per_liter'),
        'total_amount': total_amount,
        'distributed': 0,
        'created_by': g.current_user['_id'],
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow()
    }

    result = mongo.db.fuel_invoices.insert_one(invoice_doc)
    invoice_doc['_id'] = str(result.inserted_id)

    return jsonify({
        'success': True,
        'message': f'Накладну {doc_number} створено.',
        'invoice': invoice_doc
    }), 201


# === Записи видачі пального ===

@fuel_bp.route('/records', methods=['GET'])
@require_auth
def get_records():
    """
    Отримання записів видачі пального.
    Водії бачать тільки свої, інші - всі.
    """
    vehicle_id = request.args.get('vehicle_id')
    driver_id = request.args.get('driver_id')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    record_type = request.args.get('type')

    query = {}

    if g.current_user['role'] == 'driver':
        query['driver_id'] = g.current_user['_id']
    elif driver_id:
        query['driver_id'] = driver_id

    if vehicle_id:
        query['vehicle_id'] = vehicle_id
    if record_type:
        query['record_type'] = record_type

    if date_from or date_to:
        query['date'] = {}
        if date_from:
            query['date']['$gte'] = datetime.fromisoformat(date_from)
        if date_to:
            query['date']['$lte'] = datetime.fromisoformat(date_to)

    records = list(mongo.db.fuel_records.find(query).sort('date', -1))

    for rec in records:
        rec['_id'] = str(rec['_id'])
        enrich_record(rec)

    return jsonify({
        'success': True,
        'records': records,
        'total': len(records)
    })


@fuel_bp.route('/records', methods=['POST'])
@require_auth
@require_role('manager')
def create_record():
    """
    Створення запису видачі пального.
    """
    try:
        data = record_create_schema.load(request.get_json())
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

    # Якщо видача з накладної - перевіряємо залишок
    if data.get('invoice_id'):
        invoice = mongo.db.fuel_invoices.find_one({'_id': ObjectId(data['invoice_id'])})
        if not invoice:
            return jsonify({
                'success': False,
                'error': 'Накладну не знайдено.'
            }), 400

        remaining = invoice['quantity'] - invoice.get('distributed', 0)
        if data['quantity'] > remaining:
            return jsonify({
                'success': False,
                'error': f'Недостатньо пального. Залишок: {remaining} л.'
            }), 400

        # Оновлюємо розподілене
        mongo.db.fuel_invoices.update_one(
            {'_id': ObjectId(data['invoice_id'])},
            {'$inc': {'distributed': data['quantity']}}
        )

    total_amount = None
    if data.get('price_per_liter'):
        total_amount = data['quantity'] * data['price_per_liter']

    record_doc = {
        'invoice_id': data.get('invoice_id'),
        'vehicle_id': data['vehicle_id'],
        'driver_id': data.get('driver_id'),
        'waybill_id': data.get('waybill_id'),
        'date': data['date'],
        'quantity': data['quantity'],
        'odometer': data.get('odometer'),
        'record_type': data['record_type'],
        'station': data.get('station'),
        'price_per_liter': data.get('price_per_liter'),
        'total_amount': total_amount,
        'receipt_number': data.get('receipt_number'),
        'notes': data.get('notes'),
        'created_by': g.current_user['_id'],
        'created_at': datetime.utcnow()
    }

    result = mongo.db.fuel_records.insert_one(record_doc)
    record_doc['_id'] = str(result.inserted_id)
    enrich_record(record_doc)

    return jsonify({
        'success': True,
        'message': 'Запис створено.',
        'record': record_doc
    }), 201


# === Аналітика пального ===

@fuel_bp.route('/analysis/<vehicle_id>', methods=['GET'])
@require_auth
@require_role('manager', 'mechanic')
def analyze_fuel(vehicle_id):
    """
    Аналіз витрат пального для транспортного засобу.
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

    # Останні завершені путівки
    waybills = list(mongo.db.waybills.find({
        'vehicle_id': vehicle_id,
        'status': 'completed',
        'odometer_end': {'$exists': True},
        'fuel_used': {'$exists': True}
    }).sort('completed_at', -1).limit(20))

    analysis = []
    for wb in waybills:
        distance = wb.get('odometer_end', 0) - wb.get('odometer_start', 0)
        if distance > 0 and wb.get('fuel_used'):
            consumption = calculate_fuel_consumption(
                distance,
                wb['fuel_used'],
                vehicle.get('fuel_norm', 25)
            )
            overspend = check_overspend(consumption, vehicle.get('fuel_norm', 25))

            analysis.append({
                'waybill_number': wb['number'],
                'date': wb.get('completed_at'),
                'distance': distance,
                'fuel_used': wb['fuel_used'],
                'consumption_per_100km': round(consumption, 2),
                'norm': vehicle.get('fuel_norm', 25),
                'deviation_percent': round(overspend['deviation_percent'], 2),
                'is_overspend': overspend['is_overspend']
            })

    return jsonify({
        'success': True,
        'vehicle': {
            '_id': str(vehicle['_id']),
            'plate_number': vehicle['plate_number'],
            'fuel_norm': vehicle.get('fuel_norm', 25)
        },
        'analysis': analysis
    })


@fuel_bp.route('/summary', methods=['GET'])
@require_auth
@require_role('manager')
def fuel_summary():
    """
    Загальна статистика по пальному.
    """
    # Загальна кількість по накладним
    pipeline = [
        {
            '$group': {
                '_id': '$fuel_type',
                'total_received': {'$sum': '$quantity'},
                'total_distributed': {'$sum': '$distributed'}
            }
        }
    ]
    by_type = list(mongo.db.fuel_invoices.aggregate(pipeline))

    # Витрати за останній місяць
    # Підтримуємо обидва формати дати: datetime та string ISO
    month_ago_dt = datetime.utcnow().replace(day=1)
    month_ago_str = month_ago_dt.strftime('%Y-%m-%d')
    records_pipeline = [
        {'$match': {
            '$or': [
                {'date': {'$gte': month_ago_dt}},  # datetime формат
                {'date': {'$gte': month_ago_str}}  # string формат
            ]
        }},
        {
            '$group': {
                '_id': None,
                # Підтримуємо обидві схеми: record_type (нова) та source (seed)
                'total_issued': {'$sum': {'$cond': [
                    {'$or': [
                        {'$eq': ['$record_type', 'issue']},
                        {'$eq': ['$source', 'invoice']}
                    ]},
                    '$quantity', 0
                ]}},
                'total_external': {'$sum': {'$cond': [
                    {'$or': [
                        {'$eq': ['$record_type', 'external']},
                        {'$eq': ['$source', 'station']}
                    ]},
                    '$quantity', 0
                ]}}
            }
        }
    ]
    monthly = list(mongo.db.fuel_records.aggregate(records_pipeline))

    return jsonify({
        'success': True,
        'by_fuel_type': by_type,
        'monthly': monthly[0] if monthly else {'total_issued': 0, 'total_external': 0}
    })
