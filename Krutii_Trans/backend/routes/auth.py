"""
Маршрути автентифікації
"""
from datetime import datetime
from flask import Blueprint, request, jsonify, g
from flask_jwt_extended import create_access_token, unset_jwt_cookies, set_access_cookies
import bcrypt
from bson import ObjectId
from marshmallow import ValidationError

from extensions import mongo, limiter
from middleware.auth_middleware import require_auth
from models.user import UserSchema, PasswordChangeSchema

auth_bp = Blueprint('auth', __name__)
user_schema = UserSchema()
password_schema = PasswordChangeSchema()


@auth_bp.route('/login', methods=['POST'])
@limiter.limit("10/minute")
def login():
    """
    Вхід в систему.
    Повертає JWT токен у httpOnly cookie.
    """
    data = request.get_json()

    if not data:
        return jsonify({
            'success': False,
            'error': 'Не надано даних для входу.'
        }), 400

    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({
            'success': False,
            'error': 'Введіть логін та пароль.'
        }), 400

    # Пошук користувача
    user = mongo.db.users.find_one({'username': username})

    if not user:
        return jsonify({
            'success': False,
            'error': 'Невірний логін або пароль.'
        }), 401

    # Перевірка пароля
    if not bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
        return jsonify({
            'success': False,
            'error': 'Невірний логін або пароль.'
        }), 401

    # Перевірка активності
    if not user.get('is_active', True):
        return jsonify({
            'success': False,
            'error': 'Обліковий запис деактивовано. Зверніться до адміністратора.'
        }), 403

    # Оновлення часу останнього входу
    mongo.db.users.update_one(
        {'_id': user['_id']},
        {'$set': {'last_login': datetime.utcnow()}}
    )

    # Створення токена
    access_token = create_access_token(identity=str(user['_id']))

    # Підготовка відповіді
    user_data = user_schema.dump(user)

    response = jsonify({
        'success': True,
        'message': 'Вхід виконано успішно.',
        'user': user_data
    })

    # Встановлення cookie
    set_access_cookies(response, access_token)

    return response


@auth_bp.route('/logout', methods=['POST'])
def logout():
    """
    Вихід з системи.
    Видаляє JWT cookie.
    """
    response = jsonify({
        'success': True,
        'message': 'Вихід виконано успішно.'
    })
    unset_jwt_cookies(response)
    return response


@auth_bp.route('/me', methods=['GET'])
@require_auth
def me():
    """
    Отримання даних поточного користувача.
    """
    return jsonify({
        'success': True,
        'user': user_schema.dump(g.current_user)
    })


@auth_bp.route('/change-password', methods=['POST'])
@require_auth
def change_password():
    """
    Зміна пароля поточного користувача.
    """
    try:
        data = password_schema.load(request.get_json())
    except ValidationError as err:
        return jsonify({
            'success': False,
            'error': 'Помилка валідації.',
            'details': err.messages
        }), 400

    # Отримання поточного користувача з БД (потрібен хеш пароля)
    user = mongo.db.users.find_one({'_id': ObjectId(g.current_user['_id'])})

    # Перевірка поточного пароля
    if not bcrypt.checkpw(
        data['current_password'].encode('utf-8'),
        user['password_hash'].encode('utf-8')
    ):
        return jsonify({
            'success': False,
            'error': 'Поточний пароль невірний.'
        }), 400

    # Хешування нового пароля
    new_hash = bcrypt.hashpw(
        data['new_password'].encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')

    # Оновлення пароля
    mongo.db.users.update_one(
        {'_id': user['_id']},
        {
            '$set': {
                'password_hash': new_hash,
                'updated_at': datetime.utcnow()
            }
        }
    )

    return jsonify({
        'success': True,
        'message': 'Пароль успішно змінено.'
    })
