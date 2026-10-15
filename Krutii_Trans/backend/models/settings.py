"""
Схеми налаштувань системи
"""
from marshmallow import Schema, fields, validate


class SettingsSchema(Schema):
    """Схема налаштувань системи"""
    _id = fields.String(dump_only=True)

    # Паливні налаштування
    default_fuel_norm = fields.Float(
        validate=validate.Range(min=1, max=100, error='Норма витрат має бути від 1 до 100 л/100км')
    )
    overspend_threshold = fields.Float(
        validate=validate.Range(min=1, max=50, error='Поріг перевитрати має бути від 1 до 50%')
    )
    winter_coefficient = fields.Float(
        validate=validate.Range(min=1, max=1.5, error='Зимовий коефіцієнт має бути від 1 до 1.5')
    )

    # Налаштування ТО
    maintenance_warning_km = fields.Integer(
        validate=validate.Range(min=100, max=10000, error='Попередження про ТО має бути від 100 до 10000 км')
    )
    maintenance_warning_days = fields.Integer(
        validate=validate.Range(min=1, max=60, error='Попередження про ТО має бути від 1 до 60 днів')
    )
    maintenance_interval_km = fields.Integer(
        validate=validate.Range(min=1000, max=50000, error='Інтервал ТО має бути від 1000 до 50000 км')
    )

    # Налаштування ескалації
    fault_mechanic_hours = fields.Integer(
        validate=validate.Range(min=1, max=48, error='Час ескалації механіку має бути від 1 до 48 годин')
    )
    fault_manager_hours = fields.Integer(
        validate=validate.Range(min=1, max=72, error='Час ескалації керівнику має бути від 1 до 72 годин')
    )

    # Інші налаштування
    company_name = fields.String(
        validate=validate.Length(max=200, error='Назва компанії занадто довга')
    )

    updated_at = fields.DateTime(dump_only=True)
    updated_by = fields.String()
