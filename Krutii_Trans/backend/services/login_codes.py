"""
Одноразові коди для входу через пошту.
У базі зберігається лише хеш коду; документ автоматично видаляється після закінчення терміну (TTL-індекс).
"""
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta

from flask import current_app


def _hash(user_id, code):
    key = current_app.config['JWT_SECRET_KEY'].encode()
    return hmac.new(key, f'{user_id}:{code}'.encode(), hashlib.sha256).hexdigest()


def seconds_until_resend(db, user_id):
    """Скільки секунд лишилось до можливості надіслати код повторно (0 - можна)."""
    doc = db.login_codes.find_one({'user_id': str(user_id)})
    if not doc:
        return 0
    wait = current_app.config['LOGIN_CODE_RESEND_SECONDS']
    passed = (datetime.utcnow() - doc['created_at']).total_seconds()
    return max(0, int(wait - passed + 0.999))


def create_code(db, user_id):
    """Створює новий 4-значний код (попередній стає недійсним)."""
    code = f'{secrets.randbelow(10000):04d}'
    now = datetime.utcnow()
    db.login_codes.replace_one(
        {'user_id': str(user_id)},
        {'user_id': str(user_id), 'code_hash': _hash(user_id, code), 'attempts': 0, 'created_at': now,
         'expires_at': now + timedelta(minutes=current_app.config['LOGIN_CODE_TTL_MINUTES'])},
        upsert=True)
    return code


def check_code(db, user_id, code):
    """
    Перевіряє код. Повертає (ok, причина, залишок_спроб).
    причина: 'ok' | 'missing' | 'expired' | 'wrong' | 'locked'
    """
    doc = db.login_codes.find_one({'user_id': str(user_id)})
    if not doc:
        return False, 'missing', 0
    if doc['expires_at'] < datetime.utcnow():
        db.login_codes.delete_one({'_id': doc['_id']})
        return False, 'expired', 0
    max_attempts = current_app.config['LOGIN_CODE_MAX_ATTEMPTS']
    if doc['attempts'] >= max_attempts:
        return False, 'locked', 0
    if hmac.compare_digest(doc['code_hash'], _hash(user_id, str(code))):
        db.login_codes.delete_one({'_id': doc['_id']})
        return True, 'ok', max_attempts - doc['attempts']
    db.login_codes.update_one({'_id': doc['_id']}, {'$inc': {'attempts': 1}})
    left = max_attempts - doc['attempts'] - 1
    return False, ('locked' if left <= 0 else 'wrong'), max(0, left)


def mask_email(email):
    name, _, domain = email.partition('@')
    shown = name[:2] if len(name) > 3 else name[:1]
    return f'{shown}{"•" * max(3, len(name) - len(shown))}@{domain}'
