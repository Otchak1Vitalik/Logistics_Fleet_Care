"""
Телематика: прийом даних від трекерів (ключ пристрою) і дані для карти автопарку.
"""
from bson import ObjectId
from flask import Blueprint, jsonify, request

from extensions import mongo, limiter
from middleware.auth_middleware import require_auth, require_role
from services import telematics as tm

telematics_bp = Blueprint('telematics', __name__)


def _iso(value):
    from datetime import datetime
    if isinstance(value, datetime):
        return value.isoformat() + 'Z'
    if isinstance(value, dict):
        return {k: _iso(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_iso(v) for v in value]
    return value


@telematics_bp.route('/ingest', methods=['POST'])
@limiter.limit('600/minute')
def ingest():
    """Пакет точок від трекера. Автентифікація: заголовок X-Device-Key."""
    vehicle = tm.vehicle_by_key(mongo.db, request.headers.get('X-Device-Key', ''))
    if not vehicle:
        return jsonify({'success': False, 'error': 'Невідомий пристрій.'}), 401
    data = request.get_json(silent=True) or {}
    points = data.get('points') if isinstance(data.get('points'), list) else [data]
    result = tm.ingest(mongo.db, vehicle, points)
    return jsonify({'success': True, **result}), (200 if result['accepted'] else 400)


@telematics_bp.route('/fleet', methods=['GET'])
@require_auth
@require_role('manager', 'mechanic')
def fleet():
    return jsonify({'success': True, **_iso(tm.fleet(mongo.db))})


@telematics_bp.route('/vehicle/<vehicle_id>', methods=['GET'])
@require_auth
@require_role('manager', 'mechanic')
def vehicle(vehicle_id):
    return jsonify({'success': True, **_iso(tm.vehicle_detail(mongo.db, vehicle_id, request.args.get('hours', 3)))})


@telematics_bp.route('/devices/<vehicle_id>', methods=['POST'])
@require_auth
@require_role('manager')
def provision(vehicle_id):
    try:
        oid = ObjectId(vehicle_id)
    except Exception:  # noqa: BLE001
        return jsonify({'success': False, 'error': 'Невірний формат ID.'}), 400
    if not mongo.db.vehicles.find_one({'_id': oid}):
        return jsonify({'success': False, 'error': 'Транспортний засіб не знайдено.'}), 404
    key = tm.provision(mongo.db, vehicle_id)
    return jsonify({'success': True, 'message': 'Ключ трекера створено. Збережіть його - повторно він не показується.',
                    'key': key})
