"""
Схеми звітів про несправності
"""
from marshmallow import Schema, fields, validate

from config import Constants


class FaultSchema(Schema):
    """Схема звіту про несправність для відповідей API"""
    _id = fields.String(dump_only=True)
    number = fields.String(required=True)  # Формат: НС-XXXXXX

    # Зв'язки
    vehicle_id = fields.String(required=True)
    vehicle = fields.Nested('VehicleSchema', dump_only=True)
    reported_by = fields.String(required=True)  # ID водія
    reporter = fields.Nested('UserSchema', dump_only=True)

    # Дані несправності
    report_date = fields.DateTime(required=True)
    category = fields.String()  # engine, transmission, brakes, electrical, body, other
    category_display = fields.Method('get_category_display')
    severity = fields.String()  # low, medium, high, critical
    severity_display = fields.Method('get_severity_display')
    description = fields.String(required=True)
    odometer = fields.Integer()

    # Статус та обробка
    status = fields.String()
    status_display = fields.Method('get_status_display')
    acknowledged_by = fields.String()  # ID механіка
    mechanic = fields.Nested('UserSchema', dump_only=True)
    acknowledged_at = fields.DateTime()
    resolution = fields.String()  # Опис рішення/виправлення
    resolved_at = fields.DateTime()
    rejection_reason = fields.String()

    # Пов'язаний ремонт
    repair_id = fields.String()

    # Фото несправності (шляхи до файлів)
    photos = fields.List(fields.String(), dump_only=True)

    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

    CATEGORIES = {
        'engine': 'Двигун',
        'transmission': 'Трансмісія',
        'brakes': 'Гальма',
        'electrical': 'Електрика',
        'suspension': 'Підвіска',
        'body': 'Кузов',
        'other': 'Інше'
    }

    SEVERITIES = {
        'low': 'Низька',
        'medium': 'Середня',
        'high': 'Висока',
        'critical': 'Критична'
    }

    def get_category_display(self, obj):
        return self.CATEGORIES.get(obj.get('category'), obj.get('category'))

    def get_severity_display(self, obj):
        return self.SEVERITIES.get(obj.get('severity'), obj.get('severity'))

    def get_status_display(self, obj):
        return Constants.FAULT_STATUSES.get(obj.get('status'), obj.get('status'))


class FaultCreateSchema(Schema):
    """Схема для створення звіту про несправність"""
    vehicle_id = fields.String(required=True)
    category = fields.String(
        required=True,
        validate=validate.OneOf(
            ['engine', 'transmission', 'brakes', 'electrical', 'suspension', 'body', 'other'],
            error='Невірна категорія несправності'
        )
    )
    severity = fields.String(
        required=True,
        validate=validate.OneOf(
            ['low', 'medium', 'high', 'critical'],
            error='Невірний рівень критичності'
        )
    )
    description = fields.String(
        required=True,
        validate=validate.Length(min=10, max=2000, error='Опис має бути від 10 до 2000 символів')
    )
    odometer = fields.Integer(
        allow_none=True,
        validate=validate.Range(min=0, error='Пробіг не може бути від\'ємним')
    )


class FaultUpdateSchema(Schema):
    """Схема для оновлення звіту про несправність"""
    status = fields.String(
        validate=validate.OneOf(list(Constants.FAULT_STATUSES.keys()), error='Невірний статус')
    )
    resolution = fields.String(
        validate=validate.Length(max=2000, error='Опис рішення занадто довгий')
    )
    rejection_reason = fields.String(
        validate=validate.Length(max=500, error='Причина відхилення занадто довга')
    )
    repair_id = fields.String()
