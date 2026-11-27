"""
Оптимізований графік ТО (керівник): розрахунок плану на горизонт і затвердження -
створення запланованих ТО в розділі «Ремонти».
"""
from datetime import datetime

from flask import Blueprint, g, jsonify, request

from extensions import mongo
from middleware.auth_middleware import require_auth, require_role
from services import maintenance_optimizer as mo

maintenance_plan_bp = Blueprint('maintenance_plan', __name__)


def _iso(value):
    if isinstance(value, datetime):
        return value.isoformat() + 'Z'
    if isinstance(value, dict):
        return {k: _iso(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_iso(v) for v in value]
    return value


def _int(name, lo, hi):
    try:
        v = int(request.args.get(name))
    except (TypeError, ValueError):
        return None
    return min(hi, max(lo, v))


@maintenance_plan_bp.route('', methods=['GET'])
@require_auth
@require_role('manager')
def get_plan():
    plan = mo.optimize(mongo.db, horizon_days=_int('horizon', 7, 42), bays=_int('bays', 1, 10),
                       failure_cost=_int('failure_cost', 1000, 500000))
    return jsonify({'success': True, **_iso(plan)})


@maintenance_plan_bp.route('/apply', methods=['POST'])
@require_auth
@require_role('manager')
def apply():
    items = (request.get_json() or {}).get('items') or []
    if not isinstance(items, list) or not items:
        return jsonify({'success': False, 'error': 'Не обрано жодного ТО.'}), 400
    created = mo.apply_plan(mongo.db, items[:100], g.current_user)
    if not created:
        return jsonify({'success': False, 'error': 'ТО для цих автомобілів уже заплановано.'}), 400
    return jsonify({'success': True, 'message': f'Заплановано ТО: {len(created)}.', 'created': _iso(created)}), 201
