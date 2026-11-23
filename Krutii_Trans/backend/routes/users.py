"""
Маршрути управління користувачами (тільки для керівника)
"""
from datetime import datetime
from flask import Blueprint, request, jsonify, g
import bcrypt
from bson import ObjectId
from marshmallow import ValidationError

from extensions import mongo
from middleware.auth_middleware import require_auth, require_role
from models.user import UserSchema, UserCreateSchema, UserUpdateSchema

users_bp = Blueprint('users', __name__)
user_schema = UserSchema()
users_schema = UserSchema(many=True)
create_schema = UserCreateSchema()
update_schema = UserUpdateSchema()


@users_bp.route('', methods=['GET'])
@require_auth
@require_role('manager')
def get_users():
    """
    Отримання списку користувачів.
    Підтримує фільтрацію за роллю та статусом.
    """
    role = request.args.get('role')
    is_active = request.args.get('is_active')

    query = {}
    if role:
        query['role'] = role
    if is_active is not None:
        query['is_active'] = is_active.lower() == 'true'

    users = list(mongo.db.users.find(query).sort('full_name', 1))

    return jsonify({
        'success': True,
        'users': users_schema.dump(users),
        'total': len(users)
    })


@users_bp.route('/<user_id>', methods=['GET'])
@require_auth
@require_role('manager')
def get_user(user_id):
    """
    Отримання даних конкретного користувача.
    """
    try:
        user = mongo.db.users.find_one({'_id': ObjectId(user_id)})
    except:
        return jsonify({
            'success': False,
            'error': 'Невірний формат ID.'
        }), 400

    if not user:
        return jsonify({
            'success': False,
            'error': 'Користувача не знайдено.'
        }), 404

    return jsonify({
        'success': True,
        'user': user_schema.dump(user)
    })


@users_bp.route('', methods=['POST'])
@require_auth
@require_role('manager')
def create_user():
    """
    Створення нового користувача.
    """
    try:
        data = create_schema.load(request.get_json())
    except ValidationError as err:
        return jsonify({
            'success': False,
            'error': 'Помилка валідації.',
            'details': err.messages
        }), 400

    # Перевірка унікальності логіна
    existing = mongo.db.users.find_one({'username': data['username']})
    if existing:
        return jsonify({
            'success': False,
            'error': f'Користувач з логіном "{data["username"]}" вже існує.'
        }), 400

    # Хешування пароля
    password_hash = bcrypt.hashpw(
        data['password'].encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')

    # Конвертуємо date в datetime для MongoDB
    license_expiry = data.get('license_expiry')
    if license_expiry and hasattr(license_expiry, 'year') and not hasattr(license_expiry, 'hour'):
        license_expiry = datetime(license_expiry.year, license_expiry.month, license_expiry.day)

    # Підготовка документа
    user_doc = {
        'username': data['username'],
        'password_hash': password_hash,
        'full_name': data['full_name'],
        'role': data['role'],
        'phone': data.get('phone'),
        'email': data.get('email'),
        'is_active': True,
        'license_number': data.get('license_number'),
        'license_expiry': license_expiry,
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow(),
        'created_by': g.current_user['_id']
    }

    result = mongo.db.users.insert_one(user_doc)
    user_doc['_id'] = result.inserted_id

    return jsonify({
        'success': True,
        'message': 'Користувача створено успішно.',
        'user': user_schema.dump(user_doc)
    }), 201


@users_bp.route('/<user_id>', methods=['PUT'])
@require_auth
@require_role('manager')
def update_user(user_id):
    """
    Оновлення даних користувача.
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
        user = mongo.db.users.find_one({'_id': ObjectId(user_id)})
    except:
        return jsonify({
            'success': False,
            'error': 'Невірний формат ID.'
        }), 400

    if not user:
        return jsonify({
            'success': False,
            'error': 'Користувача не знайдено.'
        }), 404

    # Не можна деактивувати себе
    if data.get('is_active') is False and user_id == g.current_user['_id']:
        return jsonify({
            'success': False,
            'error': 'Не можна деактивувати власний обліковий запис.'
        }), 400

    # Оновлення
    update_data = {k: v for k, v in data.items() if v is not None}
    update_data['updated_at'] = datetime.utcnow()

    # Конвертуємо date в datetime для MongoDB
    if 'license_expiry' in update_data:
        le = update_data['license_expiry']
        if le and hasattr(le, 'year') and not hasattr(le, 'hour'):
            update_data['license_expiry'] = datetime(le.year, le.month, le.day)

    mongo.db.users.update_one(
        {'_id': ObjectId(user_id)},
        {'$set': update_data}
    )

    updated_user = mongo.db.users.find_one({'_id': ObjectId(user_id)})

    return jsonify({
        'success': True,
        'message': 'Дані користувача оновлено.',
        'user': user_schema.dump(updated_user)
    })


@users_bp.route('/<user_id>/reset-password', methods=['POST'])
@require_auth
@require_role('manager')
def reset_password(user_id):
    """
    Скидання пароля користувача (встановлення нового).
    """
    data = request.get_json()
    new_password = data.get('new_password')

    if not new_password or len(new_password) < 6:
        return jsonify({
            'success': False,
            'error': 'Новий пароль має бути не менше 6 символів.'
        }), 400

    try:
        user = mongo.db.users.find_one({'_id': ObjectId(user_id)})
    except:
        return jsonify({
            'success': False,
            'error': 'Невірний формат ID.'
        }), 400

    if not user:
        return jsonify({
            'success': False,
            'error': 'Користувача не знайдено.'
        }), 404

    # Хешування нового пароля
    password_hash = bcrypt.hashpw(
        new_password.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')

    mongo.db.users.update_one(
        {'_id': ObjectId(user_id)},
        {
            '$set': {
                'password_hash': password_hash,
                'updated_at': datetime.utcnow()
            }
        }
    )

    return jsonify({
        'success': True,
        'message': 'Пароль користувача скинуто.'
    })


@users_bp.route('/drivers', methods=['GET'])
@require_auth
@require_role('manager', 'mechanic')
def get_drivers():
    """
    Отримання списку активних водіїв.
    Доступно для керівників та механіків.
    """
    drivers = list(mongo.db.users.find({
        'role': 'driver',
        'is_active': True
    }).sort('full_name', 1))

    return jsonify({
        'success': True,
        'drivers': users_schema.dump(drivers)
    })


@users_bp.route('/mechanics', methods=['GET'])
@require_auth
@require_role('manager')
def get_mechanics():
    """
    Отримання списку активних механіків.
    """
    mechanics = list(mongo.db.users.find({
        'role': 'mechanic',
        'is_active': True
    }).sort('full_name', 1))

    return jsonify({
        'success': True,
        'mechanics': users_schema.dump(mechanics)
    })
