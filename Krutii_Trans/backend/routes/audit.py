"""
Журнал дій (лише перегляд, лише для керівника).
Змінювати чи видаляти записи журналу через API не можна.
"""
import re
from datetime import datetime, timedelta

from flask import Blueprint, request, jsonify

from extensions import mongo
from middleware.auth_middleware import require_auth, require_role
from services.audit import summary, ACTIONS

audit_bp = Blueprint('audit', __name__)

CATEGORIES = sorted({c for c, _ in ACTIONS.values()})


def _parse_date(value, end=False):
    try:
        d = datetime.strptime(value, '%Y-%m-%d')
        return d + timedelta(days=1) if end else d
    except (TypeError, ValueError):
        return None


@audit_bp.route('', methods=['GET'])
@require_auth
@require_role('manager')
def list_events():
    query = {}
    if request.args.get('username'):
        query['username'] = request.args['username']
    if request.args.get('category') in CATEGORIES:
        query['category'] = request.args['category']
    if request.args.get('status') in ('success', 'fail'):
        query['status'] = request.args['status']
    date_from, date_to = _parse_date(request.args.get('date_from')), _parse_date(request.args.get('date_to'), end=True)
    if date_from or date_to:
        query['ts'] = {k: v for k, v in (('$gte', date_from), ('$lt', date_to)) if v}
    q = (request.args.get('q') or '').strip()
    if q:
        rx = {'$regex': re.escape(q), '$options': 'i'}
        query['$or'] = [{'action': rx}, {'entity_label': rx}, {'username': rx}, {'full_name': rx}, {'ip': rx}]

    try:
        page = max(1, int(request.args.get('page', 1)))
        limit = min(100, max(1, int(request.args.get('limit', 50))))
    except ValueError:
        page, limit = 1, 50
    total = mongo.db.audit_log.count_documents(query)
    items = []
    for doc in mongo.db.audit_log.find(query).sort('ts', -1).skip((page - 1) * limit).limit(limit):
        doc['_id'] = str(doc['_id'])
        doc['ts'] = doc['ts'].isoformat() + 'Z'
        items.append(doc)
    return jsonify({
        'success': True, 'items': items, 'total': total, 'page': page,
        'pages': max(1, -(-total // limit)), 'summary': summary(mongo.db),
        'users': sorted(u for u in mongo.db.audit_log.distinct('username') if u),
        'categories': CATEGORIES,
    })
