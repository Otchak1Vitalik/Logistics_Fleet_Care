"""
Маршрути складу запчастин
"""
import re
from datetime import datetime

from bson import ObjectId
from bson.errors import InvalidId
from flask import Blueprint, request, jsonify, g
from marshmallow import ValidationError

from extensions import mongo
from middleware.auth_middleware import require_auth, require_role
from models.part import PartCreateSchema, PartUpdateSchema, StockInSchema
from services.inventory import receive_part, check_low_stock

parts_bp = Blueprint('parts', __name__)
create_schema = PartCreateSchema()
update_schema = PartUpdateSchema()
stock_schema = StockInSchema()

CATEGORY_LABELS = {
    'brakes': 'Гальма', 'filters': 'Фільтри', 'oils': 'Мастила та рідини', 'engine': 'Двигун',
    'electrical': 'Електрика', 'suspension': 'Підвіска', 'tyres': 'Шини', 'other': 'Інше',
}


def serialize(part):
    part['_id'] = str(part['_id'])
    part['category_display'] = CATEGORY_LABELS.get(part.get('category'), part.get('category'))
    part['is_low'] = part.get('quantity', 0) <= part.get('min_quantity', 0)
    part['stock_value'] = round(part.get('quantity', 0) * part.get('price', 0), 2)
    return part


def find_part(part_id):
    try:
        return mongo.db.parts.find_one({'_id': ObjectId(part_id)})
    except (InvalidId, TypeError):
        return None


@parts_bp.route('', methods=['GET'])
@require_auth
@require_role('manager', 'mechanic')
def get_parts():
    query = {}
    q = (request.args.get('q') or '').strip()
    if q:
        rx = {'$regex': re.escape(q), '$options': 'i'}
        query['$or'] = [{'name': rx}, {'article': rx}]
    if request.args.get('category'):
        query['category'] = request.args['category']
    parts = [serialize(p) for p in mongo.db.parts.find(query).sort('name', 1)]
    if request.args.get('low') == 'true':
        parts = [p for p in parts if p['is_low']]
    return jsonify({
        'success': True,
        'parts': parts,
        'summary': {
            'total': len(parts),
            'low': sum(1 for p in parts if p['is_low']),
            'stock_value': round(sum(p['stock_value'] for p in parts), 2),
        },
    })


@parts_bp.route('', methods=['POST'])
@require_auth
@require_role('manager', 'mechanic')
def create_part():
    try:
        data = create_schema.load(request.get_json() or {})
    except ValidationError as err:
        return jsonify({'success': False, 'error': 'Помилка валідації.', 'details': err.messages}), 400
    if mongo.db.parts.find_one({'name': data['name']}):
        return jsonify({'success': False, 'error': 'Запчастина з такою назвою вже існує.'}), 400
    now = datetime.utcnow()
    doc = {**data, 'created_at': now, 'updated_at': now, 'created_by': g.current_user['_id']}
    result = mongo.db.parts.insert_one(doc)
    if data['quantity'] > 0:
        mongo.db.part_movements.insert_one({
            'part_id': str(result.inserted_id), 'type': 'in', 'quantity': data['quantity'],
            'price': data['price'], 'note': 'Початковий залишок', 'user_id': g.current_user['_id'], 'created_at': now,
        })
    part = mongo.db.parts.find_one({'_id': result.inserted_id})
    check_low_stock(mongo.db, part)
    return jsonify({'success': True, 'message': 'Запчастину додано.', 'part': serialize(part)}), 201


@parts_bp.route('/<part_id>', methods=['PUT'])
@require_auth
@require_role('manager', 'mechanic')
def update_part(part_id):
    part = find_part(part_id)
    if not part:
        return jsonify({'success': False, 'error': 'Запчастину не знайдено.'}), 404
    try:
        data = update_schema.load(request.get_json() or {})
    except ValidationError as err:
        return jsonify({'success': False, 'error': 'Помилка валідації.', 'details': err.messages}), 400
    data['updated_at'] = datetime.utcnow()
    mongo.db.parts.update_one({'_id': part['_id']}, {'$set': data})
    part = mongo.db.parts.find_one({'_id': part['_id']})
    check_low_stock(mongo.db, part)
    return jsonify({'success': True, 'message': 'Запчастину оновлено.', 'part': serialize(part)})


@parts_bp.route('/<part_id>/receive', methods=['POST'])
@require_auth
@require_role('manager', 'mechanic')
def receive(part_id):
    part = find_part(part_id)
    if not part:
        return jsonify({'success': False, 'error': 'Запчастину не знайдено.'}), 404
    try:
        data = stock_schema.load(request.get_json() or {})
    except ValidationError as err:
        return jsonify({'success': False, 'error': 'Помилка валідації.', 'details': err.messages}), 400
    receive_part(mongo.db, part, data['quantity'], data.get('price'), g.current_user['_id'], data.get('note'))
    return jsonify({'success': True, 'message': 'Надходження оформлено.',
                    'part': serialize(mongo.db.parts.find_one({'_id': part['_id']}))})


@parts_bp.route('/<part_id>/movements', methods=['GET'])
@require_auth
@require_role('manager', 'mechanic')
def movements(part_id):
    part = find_part(part_id)
    if not part:
        return jsonify({'success': False, 'error': 'Запчастину не знайдено.'}), 404
    rows = list(mongo.db.part_movements.find({'part_id': str(part['_id'])}).sort('created_at', -1).limit(50))
    repair_ids = [ObjectId(r['repair_id']) for r in rows if r.get('repair_id')]
    repairs = {str(r['_id']): r for r in mongo.db.repairs.find({'_id': {'$in': repair_ids}}, {'number': 1, 'vehicle_id': 1})}
    for r in rows:
        r['_id'] = str(r['_id'])
        if r.get('repair_id') in repairs:
            r['repair_number'] = repairs[r['repair_id']].get('number')
    return jsonify({'success': True, 'part': serialize(part), 'movements': rows})
