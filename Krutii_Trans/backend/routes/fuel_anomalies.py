"""
Аномалії у витраті пального (керівник): перелік, рішення «підтверджено / хибна тривога»,
повторна перевірка, оцінка точності методів, історія витрати авто.
"""
from datetime import datetime

from bson import ObjectId
from flask import Blueprint, request, jsonify, g

from extensions import mongo
from middleware.auth_middleware import require_auth, require_role
from services import fuel_anomalies as fa

fuel_anomalies_bp = Blueprint('fuel_anomalies', __name__)

KINDS = {'trip_overspend', 'over_tank', 'double_refuel', 'price'}


def _out(doc):
    doc['_id'] = str(doc['_id'])
    doc.pop('demo_label', None)          # прихована мітка демоданих - лише для оцінки методів
    for k in ('date', 'detected_at', 'updated_at'):
        if isinstance(doc.get(k), datetime):
            doc[k] = doc[k].isoformat() + 'Z'
    if doc.get('review') and isinstance(doc['review'].get('at'), datetime):
        doc['review']['at'] = doc['review']['at'].isoformat() + 'Z'
    return doc


@fuel_anomalies_bp.route('', methods=['GET'])
@require_auth
@require_role('manager')
def list_anomalies():
    query = {}
    if request.args.get('status') in ('new', 'confirmed', 'dismissed'):
        query['status'] = request.args['status']
    if request.args.get('kind') in KINDS:
        query['kind'] = request.args['kind']
    if request.args.get('level') in ('high', 'medium', 'low'):
        query['level'] = request.args['level']
    if request.args.get('vehicle_id'):
        query['vehicle_id'] = request.args['vehicle_id']
    items = [_out(d) for d in mongo.db.fuel_anomalies.find(query).sort([('score', -1), ('date', -1)]).limit(300)]
    return jsonify({'success': True, 'items': items, 'summary': fa.summary(mongo.db)})


@fuel_anomalies_bp.route('/run', methods=['POST'])
@require_auth
@require_role('manager')
def run():
    result = fa.run_detection(mongo.db, notify=False)
    return jsonify({'success': True, 'message': 'Перевірку виконано.', 'result': result, 'summary': fa.summary(mongo.db)})


@fuel_anomalies_bp.route('/<anomaly_id>', methods=['PUT'])
@require_auth
@require_role('manager')
def review(anomaly_id):
    data = request.get_json() or {}
    status = data.get('status')
    if status not in ('confirmed', 'dismissed', 'new'):
        return jsonify({'success': False, 'error': 'Невірний статус.'}), 400
    try:
        oid = ObjectId(anomaly_id)
    except Exception:  # noqa: BLE001
        return jsonify({'success': False, 'error': 'Невірний формат ID.'}), 400
    comment = (data.get('comment') or '').strip()[:500] or None
    review_doc = None if status == 'new' else {
        'by': str(g.current_user['_id']), 'by_name': g.current_user.get('full_name'), 'at': datetime.utcnow(), 'comment': comment}
    res = mongo.db.fuel_anomalies.update_one({'_id': oid}, {'$set': {'status': status, 'review': review_doc}})
    if not res.matched_count:
        return jsonify({'success': False, 'error': 'Запис не знайдено.'}), 404
    return jsonify({'success': True, 'message': 'Рішення збережено.', 'anomaly': _out(mongo.db.fuel_anomalies.find_one({'_id': oid})),
                    'summary': fa.summary(mongo.db)})


@fuel_anomalies_bp.route('/evaluation', methods=['GET'])
@require_auth
@require_role('manager')
def evaluation():
    return jsonify({'success': True, 'evaluation': fa.evaluate(mongo.db)})


@fuel_anomalies_bp.route('/vehicle/<vehicle_id>', methods=['GET'])
@require_auth
@require_role('manager')
def vehicle(vehicle_id):
    return jsonify({'success': True, 'history': fa.vehicle_history(mongo.db, vehicle_id)})
