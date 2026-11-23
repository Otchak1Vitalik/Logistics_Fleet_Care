"""
Middleware для авторизації та перевірки ролей
"""
from functools import wraps
from flask import jsonify, g
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from bson import ObjectId

from extensions import mongo


def require_auth(f):
    """
    Декоратор для перевірки авторизації.
    Встановлює g.current_user з даними поточного користувача.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        from flask_jwt_extended.exceptions import NoAuthorizationError, InvalidHeaderError
        from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

        try:
            verify_jwt_in_request()
            user_id = get_jwt_identity()

            user = mongo.db.users.find_one({'_id': ObjectId(user_id)})
            if not user:
                return jsonify({
                    'success': False,
                    'error': 'Користувача не знайдено.'
                }), 401

            if not user.get('is_active', True):
                return jsonify({
                    'success': False,
                    'error': 'Обліковий запис деактивовано.'
                }), 403

            # Зберігаємо користувача в контексті запиту
            g.current_user = user
            g.current_user['_id'] = str(user['_id'])

            return f(*args, **kwargs)
        except NoAuthorizationError:
            return jsonify({
                'success': False,
                'error': 'Токен авторизації не надано.'
            }), 401
        except ExpiredSignatureError:
            return jsonify({
                'success': False,
                'error': 'Токен авторизації прострочено.'
            }), 401
        except (InvalidHeaderError, InvalidTokenError):
            return jsonify({
                'success': False,
                'error': 'Недійсний токен авторизації.'
            }), 401
        except Exception as e:
            # Логуємо несподівані помилки
            import traceback
            print(f"[AUTH ERROR] {str(e)}")
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': 'Помилка авторизації.'
            }), 401

    return decorated


def require_role(*allowed_roles):
    """
    Декоратор для перевірки ролі користувача.
    Використовується після @require_auth.

    Приклад:
        @require_auth
        @require_role('manager')
        def admin_only():
            pass

        @require_auth
        @require_role('manager', 'mechanic')
        def managers_and_mechanics():
            pass
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not hasattr(g, 'current_user') or not g.current_user:
                return jsonify({
                    'success': False,
                    'error': 'Необхідна авторизація.'
                }), 401

            user_role = g.current_user.get('role')
            if user_role not in allowed_roles:
                return jsonify({
                    'success': False,
                    'error': f'Доступ заборонено. Потрібна роль: {", ".join(allowed_roles)}.'
                }), 403

            return f(*args, **kwargs)
        return decorated
    return decorator


def require_owner_or_role(*allowed_roles):
    """
    Декоратор для перевірки власника ресурсу або ролі.
    Корисно для випадків, коли водій може бачити тільки свої дані,
    але механік/керівник можуть бачити всі.

    Очікує, що функція приймає user_id як аргумент або в kwargs.
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not hasattr(g, 'current_user') or not g.current_user:
                return jsonify({
                    'success': False,
                    'error': 'Необхідна авторизація.'
                }), 401

            user_role = g.current_user.get('role')
            current_user_id = g.current_user.get('_id')

            # Якщо користувач має дозволену роль - пропускаємо
            if user_role in allowed_roles:
                return f(*args, **kwargs)

            # Інакше перевіряємо власника
            resource_user_id = kwargs.get('user_id') or (args[0] if args else None)
            if resource_user_id and str(resource_user_id) == str(current_user_id):
                return f(*args, **kwargs)

            return jsonify({
                'success': False,
                'error': 'Доступ заборонено. Ви не є власником цього ресурсу.'
            }), 403

        return decorated
    return decorator
