"""
Схеми ремонтів та технічного обслуговування
"""
from marshmallow import Schema, fields, validate

from config import Constants


class RepairSchema(Schema):
    """Схема ремонту/ТО для відповідей API"""
    _id = fields.String(dump_only=True)
    number = fields.String(required=True)  # Формат: РМ-XXXXXX

    # Зв'язки
    vehicle_id = fields.String(required=True)
    vehicle = fields.Nested('VehicleSchema', dump_only=True)
    mechanic_id = fields.String()  # Відповідальний механік
    mechanic = fields.Nested('UserSchema', dump_only=True)
    fault_id = fields.String()  # Пов'язана несправність (якщо є)
    fault = fields.Nested('FaultSchema', dump_only=True)

    # Тип робіт
    repair_type = fields.String()  # maintenance (ТО), repair (ремонт), inspection (огляд)
    repair_type_display = fields.Method('get_type_display')
    description = fields.String(required=True)

    # Дати
    scheduled_date = fields.Raw()  # datetime або string з MongoDB
    started_at = fields.DateTime()
    completed_at = fields.DateTime()

    # Пробіг
    odometer = fields.Integer()

    # Статус
    status = fields.String()
    status_display = fields.Method('get_status_display')

    # Деталі робіт
    work_performed = fields.String()  # Опис виконаних робіт
    parts_used = fields.List(fields.Dict())  # [{name, quantity, price}]
    labor_hours = fields.Float()
    labor_cost = fields.Float()
    parts_cost = fields.Float()
    total_cost = fields.Method('get_total_cost')

    # Примітки
    notes = fields.String()
    cancellation_reason = fields.String()

    # Хто створив
    created_by = fields.String()
    creator = fields.Nested('UserSchema', dump_only=True)

    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

    REPAIR_TYPES = {
        'maintenance': 'Технічне обслуговування',
        'repair': 'Ремонт',
        'inspection': 'Технічний огляд'
    }

    def get_type_display(self, obj):
        return self.REPAIR_TYPES.get(obj.get('repair_type'), obj.get('repair_type'))

    def get_status_display(self, obj):
        return Constants.REPAIR_STATUSES.get(obj.get('status'), obj.get('status'))

    def get_total_cost(self, obj):
        labor = obj.get('labor_cost') or 0
        parts = obj.get('parts_cost') or 0
        return labor + parts


class RepairCreateSchema(Schema):
    """Схема для створення ремонту/ТО"""
    vehicle_id = fields.String(required=True)
    mechanic_id = fields.String()
    fault_id = fields.String()
    repair_type = fields.String(
        required=True,
        validate=validate.OneOf(
            ['maintenance', 'repair', 'inspection'],
            error='Невірний тип робіт'
        )
    )
    description = fields.String(
        required=True,
        validate=validate.Length(min=5, max=2000, error='Опис має бути від 5 до 2000 символів')
    )
    scheduled_date = fields.Date()
    odometer = fields.Integer(
        validate=validate.Range(min=0, error='Пробіг не може бути від\'ємним')
    )
    notes = fields.String()


class RepairUpdateSchema(Schema):
    """Схема для оновлення ремонту/ТО"""
    mechanic_id = fields.String()
    status = fields.String(
        validate=validate.OneOf(list(Constants.REPAIR_STATUSES.keys()), error='Невірний статус')
    )
    scheduled_date = fields.Date()
    work_performed = fields.String(
        validate=validate.Length(max=2000, error='Опис робіт занадто довгий')
    )
    parts_used = fields.List(fields.Dict())
    labor_hours = fields.Float(
        validate=validate.Range(min=0, error='Години роботи не можуть бути від\'ємними')
    )
    labor_cost = fields.Float(
        validate=validate.Range(min=0, error='Вартість роботи не може бути від\'ємною')
    )
    parts_cost = fields.Float(
        validate=validate.Range(min=0, error='Вартість запчастин не може бути від\'ємною')
    )
    odometer = fields.Integer()
    notes = fields.String()
    cancellation_reason = fields.String()
