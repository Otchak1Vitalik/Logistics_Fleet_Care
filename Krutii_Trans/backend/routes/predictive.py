"""
Прогноз несправностей (керівник): ризик по автопарку, якість моделі на власних даних,
результати перевірки методів на реальному наборі Scania APS.
"""
import json
import os
from datetime import datetime

from flask import Blueprint, jsonify, request

from extensions import mongo
from middleware.auth_middleware import require_auth, require_role
from services import predictive_maintenance as pm

predictive_bp = Blueprint('predictive', __name__)

SCANIA_REPORT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets', 'ml', 'scania_report.json')


def _iso(value):
    if isinstance(value, datetime):
        return value.isoformat() + 'Z'
    if isinstance(value, dict):
        return {k: _iso(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_iso(v) for v in value]
    return value


@predictive_bp.route('/risk', methods=['GET'])
@require_auth
@require_role('manager', 'mechanic')
def risk():
    return jsonify({'success': True, **_iso(pm.fleet_risk(mongo.db, request.args.get('vehicle_id')))})


@predictive_bp.route('/model', methods=['GET'])
@require_auth
@require_role('manager')
def model():
    state = pm.train(mongo.db)
    if not state.get('ready'):
        return jsonify({'success': True, 'ready': False, 'rows': state.get('rows', 0)})
    return jsonify({'success': True, 'ready': True, 'trained_at': _iso(state['trained_at']),
                    'evaluation': _iso(state['evaluation'])})


@predictive_bp.route('/retrain', methods=['POST'])
@require_auth
@require_role('manager')
def retrain():
    state = pm.train(mongo.db, force=True)
    if not state.get('ready'):
        return jsonify({'success': False, 'error': 'Недостатньо даних для навчання моделі.'}), 400
    return jsonify({'success': True, 'message': 'Модель перенавчено.', 'trained_at': _iso(state['trained_at'])})


@predictive_bp.route('/scania', methods=['GET'])
@require_auth
@require_role('manager')
def scania():
    if not os.path.exists(SCANIA_REPORT):
        return jsonify({'success': True, 'ready': False})
    with open(SCANIA_REPORT, encoding='utf-8') as fh:
        return jsonify({'success': True, 'ready': True, 'report': json.load(fh)})
