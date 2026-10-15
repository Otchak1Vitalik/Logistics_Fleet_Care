"""
Схеми путівок (подорожніх листів)
"""
from marshmallow import Schema, fields, validate, validates, ValidationError

from config import Constants


class WaybillSchema(Schema):
    """Схема путівки для відповідей API"""
    _id = fields.String(dump_only=True)
    number = fields.String(required=True)  # Формат: ПЛ-XXXXXX

    # Зв'язки
    vehicle_id = fields.String(required=True)
    vehicle = fields.Nested('VehicleSchema', dump_only=True)
    driver_id = fields.String(required=True)
    driver = fields.Nested('UserSchema', dump_only=True)
    issued_by = fields.String()  # ID керівника, який видав
    issuer = fields.Nested('UserSchema', dump_only=True)

    # Дати та час
    issue_date = fields.Raw()  # datetime або string з MongoDB
    valid_from = fields.Raw()
    valid_until = fields.Raw()

    # Маршрут
    route_from = fields.String()
    route_to = fields.String()
    route_description = fields.String()

    # Пробіг
    odometer_start = fields.Integer()
    odometer_end = fields.Integer()
    distance = fields.Method('get_distance')

    # Пальне
    fuel_issued = fields.Float()  # Видано пального (л)
    fuel_used = fields.Float()    # Фактично витрачено (л)
    fuel_remaining = fields.Float()  # Залишок у баку

    # Статус
    status = fields.String()
    status_display = fields.Method('get_status_display')

    # Примітки
    notes = fields.String()
    completion_notes = fields.String()

    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    completed_at = fields.DateTime()

    def get_status_display(self, obj):
        return Constants.WAYBILL_STATUSES.get(obj.get('status'), obj.get('status'))

    def get_distance(self, obj):
        start = obj.get('odometer_start')
        end = obj.get('odometer_end')
        if start is not None and end is not None:
            return end - start
        return None


class WaybillCreateSchema(Schema):
    """Схема для створення путівки"""
    vehicle_id = fields.String(required=True)
    driver_id = fields.String(required=True)
    issue_date = fields.Date(required=True)
    valid_from = fields.DateTime(required=True)
    valid_until = fields.DateTime(required=True)
    route_from = fields.String(
        validate=validate.Length(max=200, error='Пункт відправлення занадто довгий')
    )
    route_to = fields.String(
        validate=validate.Length(max=200, error='Пункт призначення занадто довгий')
    )
    route_description = fields.String()
    odometer_start = fields.Integer(
        validate=validate.Range(min=0, error='Пробіг не може бути від\'ємним')
    )
    fuel_issued = fields.Float(
        validate=validate.Range(min=0, error='Кількість пального не може бути від\'ємною')
    )
    notes = fields.String()

    @validates('valid_until')
    def validate_dates(self, value):
        # Валідація виконується в route, бо потрібен доступ до valid_from
        pass


class WaybillUpdateSchema(Schema):
    """Схема для оновлення путівки"""
    status = fields.String(
        validate=validate.OneOf(list(Constants.WAYBILL_STATUSES.keys()), error='Невірний статус')
    )
    odometer_end = fields.Integer(
        validate=validate.Range(min=0, error='Пробіг не може бути від\'ємним')
    )
    fuel_used = fields.Float(
        validate=validate.Range(min=0, error='Витрати пального не можуть бути від\'ємними')
    )
    fuel_remaining = fields.Float(
        validate=validate.Range(min=0, error='Залишок пального не може бути від\'ємним')
    )
    completion_notes = fields.String()
    notes = fields.String()
