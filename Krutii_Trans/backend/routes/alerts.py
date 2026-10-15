"""
Маршрути системи сповіщень
"""
from datetime import datetime
from flask import Blueprint, request, jsonify, g
from bson import ObjectId

from extensions import mongo
from middleware.auth_middleware import require_auth, require_role
from models.alert import AlertSchema

alerts_bp = Blueprint('alerts', __name__)
alert_schema = AlertSchema()
alerts_schema = AlertSchema(many=True)


@alerts_bp.route('', methods=['GET'])
@require_auth
def get_alerts():
    """
    Отримання сповіщень для поточного користувача.
    """
    unread_only = request.args.get('unread_only', 'false').lower() == 'true'
    limit = int(request.args.get('limit', 50))

    query = {
        '$or': [
            {'recipient_id': g.current_user['_id']},
            {'recipient_role': g.current_user['role']}
        ],
        'is_dismissed': False
    }

    if unread_only:
        query['is_read'] = False

    alerts = list(mongo.db.alerts.find(query).sort('created_at', -1).limit(limit))

    for alert in alerts:
        alert['_id'] = str(alert['_id'])

    return jsonify({
        'success': True,
        'alerts': alerts,
        'total': len(alerts)
    })


@alerts_bp.route('/unread-count', methods=['GET'])
@require_auth
def get_unread_count():
    """
    Кількість непрочитаних сповіщень.
    """
    count = mongo.db.alerts.count_documents({
        '$or': [
            {'recipient_id': g.current_user['_id']},
            {'recipient_role': g.current_user['role']}
        ],
        'is_read': False,
        'is_dismissed': False
    })

    return jsonify({
        'success': True,
        'count': count
    })


@alerts_bp.route('/<alert_id>/read', methods=['POST'])
@require_auth
def mark_as_read(alert_id):
    """
    Позначити сповіщення як прочитане.
    """
    try:
        alert = mongo.db.alerts.find_one({'_id': ObjectId(alert_id)})
    except:
        return jsonify({
            'success': False,
            'error': 'Невірний формат ID.'
        }), 400

    if not alert:
        return jsonify({
            'success': False,
            'error': 'Сповіщення не знайдено.'
        }), 404

    # Перевірка доступу
    if (alert.get('recipient_id') != g.current_user['_id'] and
            alert.get('recipient_role') != g.current_user['role']):
        return jsonify({
            'success': False,
            'error': 'Доступ заборонено.'
        }), 403

    mongo.db.alerts.update_one(
        {'_id': ObjectId(alert_id)},
        {
            '$set': {
                'is_read': True,
                'read_at': datetime.utcnow()
            }
        }
    )

    return jsonify({
        'success': True,
        'message': 'Сповіщення прочитано.'
    })


@alerts_bp.route('/mark-all-read', methods=['POST'])
@require_auth
def mark_all_as_read():
    """
    Позначити всі сповіщення як прочитані.
    """
    result = mongo.db.alerts.update_many(
        {
            '$or': [
                {'recipient_id': g.current_user['_id']},
                {'recipient_role': g.current_user['role']}
            ],
            'is_read': False
        },
        {
            '$set': {
                'is_read': True,
                'read_at': datetime.utcnow()
            }
        }
    )

    return jsonify({
        'success': True,
        'message': f'Прочитано {result.modified_count} сповіщень.'
    })


@alerts_bp.route('/<alert_id>/dismiss', methods=['POST'])
@require_auth
def dismiss_alert(alert_id):
    """
    Приховати сповіщення.
    """
    try:
        alert = mongo.db.alerts.find_one({'_id': ObjectId(alert_id)})
    except:
        return jsonify({
            'success': False,
            'error': 'Невірний формат ID.'
        }), 400

    if not alert:
        return jsonify({
            'success': False,
            'error': 'Сповіщення не знайдено.'
        }), 404

    # Перевірка доступу
    if (alert.get('recipient_id') != g.current_user['_id'] and
            alert.get('recipient_role') != g.current_user['role']):
        return jsonify({
            'success': False,
            'error': 'Доступ заборонено.'
        }), 403

    mongo.db.alerts.update_one(
        {'_id': ObjectId(alert_id)},
        {
            '$set': {
                'is_dismissed': True,
                'dismissed_at': datetime.utcnow()
            }
        }
    )

    return jsonify({
        'success': True,
        'message': 'Сповіщення приховано.'
    })


@alerts_bp.route('/all', methods=['GET'])
@require_auth
@require_role('manager')
def get_all_alerts():
    """
    Всі сповіщення системи (для керівника).
    """
    alert_type = request.args.get('type')
    category = request.args.get('category')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    limit = int(request.args.get('limit', 100))

    query = {}

    if alert_type:
        query['alert_type'] = alert_type
    if category:
        query['category'] = category

    if date_from or date_to:
        query['created_at'] = {}
        if date_from:
            query['created_at']['$gte'] = datetime.fromisoformat(date_from)
        if date_to:
            query['created_at']['$lte'] = datetime.fromisoformat(date_to)

    alerts = list(mongo.db.alerts.find(query).sort('created_at', -1).limit(limit))

    for alert in alerts:
        alert['_id'] = str(alert['_id'])

    return jsonify({
        'success': True,
        'alerts': alerts,
        'total': len(alerts)
    })


@alerts_bp.route('/statistics', methods=['GET'])
@require_auth
@require_role('manager')
def alert_statistics():
    """
    Статистика сповіщень.
    """
    # По типах
    by_type = list(mongo.db.alerts.aggregate([
        {'$group': {'_id': '$alert_type', 'count': {'$sum': 1}}}
    ]))

    # По категоріях
    by_category = list(mongo.db.alerts.aggregate([
        {'$group': {'_id': '$category', 'count': {'$sum': 1}}}
    ]))

    # Непрочитані по ролях
    unread_by_role = list(mongo.db.alerts.aggregate([
        {'$match': {'is_read': False, 'is_dismissed': False}},
        {'$group': {'_id': '$recipient_role', 'count': {'$sum': 1}}}
    ]))

    return jsonify({
        'success': True,
        'by_type': by_type,
        'by_category': by_category,
        'unread_by_role': unread_by_role
    })
