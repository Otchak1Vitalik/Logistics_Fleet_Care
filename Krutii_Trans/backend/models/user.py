"""
Схеми користувачів
"""
from marshmallow import Schema, fields, validate, validates, ValidationError

from config import Constants


class UserSchema(Schema):
    """Схема користувача для відповідей API"""
    _id = fields.String(dump_only=True)
    username = fields.String(required=True)
    full_name = fields.String(required=True)
    role = fields.String(required=True)
    role_display = fields.Method('get_role_display')
    phone = fields.String(allow_none=True)
    email = fields.String(allow_none=True)
    is_active = fields.Boolean(default=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

    # Для водіїв
    license_number = fields.String(allow_none=True)
    license_expiry = fields.String(allow_none=True)  # Зберігається як ISO string

    def get_role_display(self, obj):
        return Constants.ROLES.get(obj.get('role'), obj.get('role'))


class UserCreateSchema(Schema):
    """Схема для створення користувача"""
    username = fields.String(
        required=True,
        validate=[
            validate.Length(min=3, max=50, error='Логін має бути від 3 до 50 символів'),
            validate.Regexp(r'^[a-zA-Z0-9_]+$', error='Логін може містити лише латинські літери, цифри та _')
        ]
    )
    password = fields.String(
        required=True,
        load_only=True,
        validate=validate.Length(min=6, error='Пароль має бути не менше 6 символів')
    )
    full_name = fields.String(
        required=True,
        validate=validate.Length(min=2, max=100, error='ПІБ має бути від 2 до 100 символів')
    )
    role = fields.String(
        required=True,
        validate=validate.OneOf(list(Constants.ROLES.keys()), error='Невірна роль користувача')
    )
    phone = fields.String(
        allow_none=True,
        validate=validate.Regexp(r'^\+?[\d\s\-()]+$', error='Невірний формат телефону')
    )
    email = fields.Email(allow_none=True, error_messages={'invalid': 'Невірний формат email'})
    license_number = fields.String(allow_none=True)
    license_expiry = fields.Date(allow_none=True)


class UserUpdateSchema(Schema):
    """Схема для оновлення користувача"""
    full_name = fields.String(
        validate=validate.Length(min=2, max=100, error='ПІБ має бути від 2 до 100 символів')
    )
    phone = fields.String(
        allow_none=True,
        validate=validate.Regexp(r'^\+?[\d\s\-()]+$', error='Невірний формат телефону')
    )
    email = fields.Email(allow_none=True, error_messages={'invalid': 'Невірний формат email'})
    is_active = fields.Boolean()
    license_number = fields.String(allow_none=True)
    license_expiry = fields.Date(allow_none=True)


class PasswordChangeSchema(Schema):
    """Схема для зміни пароля"""
    current_password = fields.String(
        required=True,
        load_only=True
    )
    new_password = fields.String(
        required=True,
        load_only=True,
        validate=validate.Length(min=6, error='Новий пароль має бути не менше 6 символів')
    )

    @validates('new_password')
    def validate_new_password(self, value):
        if not any(c.isupper() for c in value):
            raise ValidationError('Пароль має містити хоча б одну велику літеру')
        if not any(c.isdigit() for c in value):
            raise ValidationError('Пароль має містити хоча б одну цифру')
