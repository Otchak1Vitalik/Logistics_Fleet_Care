"""
Схеми транспортних засобів
"""
from marshmallow import Schema, fields, validate

from config import Constants


class VehicleSchema(Schema):
    """Схема транспортного засобу для відповідей API"""
    _id = fields.String(dump_only=True)
    plate_number = fields.String(required=True)
    brand = fields.String(required=True)
    model = fields.String(required=True)
    year = fields.Integer()
    vin = fields.String()
    status = fields.String()
    status_display = fields.Method('get_status_display')

    # Паливні характеристики
    fuel_type = fields.String()  # diesel, petrol, gas
    fuel_norm = fields.Float()   # л/100км
    tank_capacity = fields.Float()

    # Пробіг та ТО
    odometer = fields.Integer()  # поточний пробіг
    last_maintenance_km = fields.Integer()
    last_maintenance_date = fields.Raw()  # datetime або string
    next_maintenance_km = fields.Integer()
    next_maintenance_date = fields.Raw()  # datetime або string

    # Технічний огляд
    inspection_date = fields.Raw()  # datetime або string
    inspection_expiry = fields.Raw()  # datetime або string

    # Страхування
    insurance_policy = fields.String()
    insurance_expiry = fields.Raw()  # datetime або string

    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

    def get_status_display(self, obj):
        return Constants.VEHICLE_STATUSES.get(obj.get('status'), obj.get('status'))


class VehicleCreateSchema(Schema):
    """Схема для створення транспортного засобу"""
    plate_number = fields.String(
        required=True,
        validate=validate.Length(min=2, max=20, error='Номерний знак має бути від 2 до 20 символів')
    )
    brand = fields.String(
        required=True,
        validate=validate.Length(min=1, max=50, error='Марка має бути від 1 до 50 символів')
    )
    model = fields.String(
        required=True,
        validate=validate.Length(min=1, max=50, error='Модель має бути від 1 до 50 символів')
    )
    year = fields.Integer(
        validate=validate.Range(min=1990, max=2030, error='Рік випуску має бути між 1990 та 2030')
    )
    vin = fields.String(
        validate=validate.Length(equal=17, error='VIN код має бути рівно 17 символів')
    )
    fuel_type = fields.String(
        validate=validate.OneOf(['diesel', 'petrol', 'gas'], error='Невірний тип пального')
    )
    fuel_norm = fields.Float(
        validate=validate.Range(min=1, max=100, error='Норма витрат має бути від 1 до 100 л/100км')
    )
    tank_capacity = fields.Float(
        validate=validate.Range(min=10, max=1000, error='Об\'єм баку має бути від 10 до 1000 л')
    )
    odometer = fields.Integer(
        validate=validate.Range(min=0, error='Пробіг не може бути від\'ємним')
    )
    next_maintenance_km = fields.Integer()
    next_maintenance_date = fields.Date()
    inspection_expiry = fields.Date()
    insurance_policy = fields.String()
    insurance_expiry = fields.Date()


class VehicleUpdateSchema(Schema):
    """Схема для оновлення транспортного засобу"""
    plate_number = fields.String(
        validate=validate.Length(min=2, max=20, error='Номерний знак має бути від 2 до 20 символів')
    )
    brand = fields.String()
    model = fields.String()
    year = fields.Integer()
    vin = fields.String()
    status = fields.String(
        validate=validate.OneOf(list(Constants.VEHICLE_STATUSES.keys()), error='Невірний статус')
    )
    fuel_type = fields.String(
        validate=validate.OneOf(['diesel', 'petrol', 'gas'], error='Невірний тип пального')
    )
    fuel_norm = fields.Float()
    tank_capacity = fields.Float()
    odometer = fields.Integer()
    last_maintenance_km = fields.Integer()
    last_maintenance_date = fields.Date()
    next_maintenance_km = fields.Integer()
    next_maintenance_date = fields.Date()
    inspection_date = fields.Date()
    inspection_expiry = fields.Date()
    insurance_policy = fields.String()
    insurance_expiry = fields.Date()
