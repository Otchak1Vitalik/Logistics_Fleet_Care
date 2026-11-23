"""
Схеми сповіщень (alerts)
"""
from marshmallow import Schema, fields

from config import Constants


class AlertSchema(Schema):
    """Схема сповіщення для відповідей API"""
    _id = fields.String(dump_only=True)

    # Тип та рівень
    alert_type = fields.String(required=True)  # info, warning, critical
    alert_type_display = fields.Method('get_type_display')
    category = fields.String()  # fault, maintenance, fuel, general
    category_display = fields.Method('get_category_display')

    # Контент
    title = fields.String(required=True)
    message = fields.String(required=True)

    # Отримувач
    recipient_id = fields.String()  # Конкретний користувач
    recipient = fields.Nested('UserSchema', dump_only=True)
    recipient_role = fields.String()  # Або роль (всім механікам, всім керівникам)

    # Пов'язані об'єкти
    related_type = fields.String()  # fault, repair, vehicle, waybill
    related_id = fields.String()

    # Статус
    is_read = fields.Boolean(default=False)
    read_at = fields.DateTime()
    is_dismissed = fields.Boolean(default=False)
    dismissed_at = fields.DateTime()

    created_at = fields.DateTime(dump_only=True)

    CATEGORIES = {
        'fault': 'Несправність',
        'maintenance': 'Технічне обслуговування',
        'fuel': 'Паливо',
        'general': 'Загальне',
        'escalation': 'Ескалація'
    }

    def get_type_display(self, obj):
        return Constants.ALERT_TYPES.get(obj.get('alert_type'), obj.get('alert_type'))

    def get_category_display(self, obj):
        return self.CATEGORIES.get(obj.get('category'), obj.get('category'))


class AlertCreateSchema(Schema):
    """Схема для створення сповіщення (внутрішнє використання)"""
    alert_type = fields.String(required=True)
    category = fields.String(required=True)
    title = fields.String(required=True)
    message = fields.String(required=True)
    recipient_id = fields.String()
    recipient_role = fields.String()
    related_type = fields.String()
    related_id = fields.String()
