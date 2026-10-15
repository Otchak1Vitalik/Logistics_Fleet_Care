"""
Маршрути налаштувань системи
"""
from datetime import datetime
from flask import Blueprint, request, jsonify, g
from marshmallow import ValidationError

from extensions import mongo
from middleware.auth_middleware import require_auth, require_role
from models.settings import SettingsSchema

settings_bp = Blueprint('settings', __name__)
settings_schema = SettingsSchema()


def get_default_settings():
    """Повертає налаштування за замовчуванням."""
    return {
        'default_fuel_norm': 25.0,
        'overspend_threshold': 10,
        'winter_coefficient': 1.09,
        'maintenance_warning_km': 1000,
        'maintenance_warning_days': 14,
        'maintenance_interval_km': 10000,
        'fault_mechanic_hours': 4,
        'fault_manager_hours': 24,
        'company_name': 'KRUTII TRANS'
    }


@settings_bp.route('', methods=['GET'])
@require_auth
@require_role('manager')
def get_settings():
    """
    Отримання налаштувань системи.
    """
    settings = mongo.db.settings.find_one({'_id': 'system'})

    if not settings:
        # Ініціалізуємо налаштування за замовчуванням
        settings = get_default_settings()
        settings['_id'] = 'system'
        settings['created_at'] = datetime.utcnow()
        settings['updated_at'] = datetime.utcnow()
        mongo.db.settings.insert_one(settings)

    settings['_id'] = str(settings['_id'])

    return jsonify({
        'success': True,
        'settings': settings
    })


@settings_bp.route('', methods=['PUT'])
@require_auth
@require_role('manager')
def update_settings():
    """
    Оновлення налаштувань системи.
    """
    try:
        data = settings_schema.load(request.get_json())
    except ValidationError as err:
        return jsonify({
            'success': False,
            'error': 'Помилка валідації.',
            'details': err.messages
        }), 400

    update_data = {k: v for k, v in data.items() if v is not None}
    update_data['updated_at'] = datetime.utcnow()
    update_data['updated_by'] = g.current_user['_id']

    # Upsert - створити або оновити
    mongo.db.settings.update_one(
        {'_id': 'system'},
        {'$set': update_data},
        upsert=True
    )

    settings = mongo.db.settings.find_one({'_id': 'system'})
    settings['_id'] = str(settings['_id'])

    return jsonify({
        'success': True,
        'message': 'Налаштування збережено.',
        'settings': settings
    })


@settings_bp.route('/reset', methods=['POST'])
@require_auth
@require_role('manager')
def reset_settings():
    """
    Скидання налаштувань до значень за замовчуванням.
    """
    default = get_default_settings()
    default['_id'] = 'system'
    default['created_at'] = datetime.utcnow()
    default['updated_at'] = datetime.utcnow()
    default['updated_by'] = g.current_user['_id']

    mongo.db.settings.replace_one(
        {'_id': 'system'},
        default,
        upsert=True
    )

    default['_id'] = str(default['_id'])

    return jsonify({
        'success': True,
        'message': 'Налаштування скинуто до значень за замовчуванням.',
        'settings': default
    })


@settings_bp.route('/fuel-types', methods=['GET'])
@require_auth
def get_fuel_types():
    """
    Отримання типів пального (для форм).
    """
    return jsonify({
        'success': True,
        'fuel_types': [
            {'value': 'diesel', 'label': 'Дизель'},
            {'value': 'petrol', 'label': 'Бензин'},
            {'value': 'gas', 'label': 'Газ'}
        ]
    })


@settings_bp.route('/categories', methods=['GET'])
@require_auth
def get_categories():
    """
    Отримання категорій несправностей (для форм).
    """
    return jsonify({
        'success': True,
        'fault_categories': [
            {'value': 'engine', 'label': 'Двигун'},
            {'value': 'transmission', 'label': 'Трансмісія'},
            {'value': 'brakes', 'label': 'Гальма'},
            {'value': 'electrical', 'label': 'Електрика'},
            {'value': 'suspension', 'label': 'Підвіска'},
            {'value': 'body', 'label': 'Кузов'},
            {'value': 'other', 'label': 'Інше'}
        ],
        'severity_levels': [
            {'value': 'low', 'label': 'Низька'},
            {'value': 'medium', 'label': 'Середня'},
            {'value': 'high', 'label': 'Висока'},
            {'value': 'critical', 'label': 'Критична'}
        ],
        'repair_types': [
            {'value': 'maintenance', 'label': 'Технічне обслуговування'},
            {'value': 'repair', 'label': 'Ремонт'},
            {'value': 'inspection', 'label': 'Технічний огляд'}
        ]
    })
