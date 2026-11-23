"""
Схеми паливних накладних та записів
"""
from marshmallow import Schema, fields, validate


class FuelInvoiceSchema(Schema):
    """Схема паливної накладної для відповідей API"""
    _id = fields.String(dump_only=True)
    number = fields.String(required=True)  # Формат: НП-XXXXXX

    # Дані накладної
    date = fields.Raw()  # datetime або string з MongoDB
    supplier = fields.String()  # Постачальник
    fuel_type = fields.String()  # diesel, petrol, gas

    # Кількість та ціна
    quantity = fields.Float(required=True)  # Загальна кількість (л)
    price_per_liter = fields.Float()
    total_amount = fields.Float()

    # Хто створив
    created_by = fields.String()
    creator = fields.Nested('UserSchema', dump_only=True)

    # Розподіл
    distributed = fields.Float(default=0)  # Скільки вже розподілено
    remaining = fields.Method('get_remaining')

    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

    def get_remaining(self, obj):
        return obj.get('quantity', 0) - obj.get('distributed', 0)


class FuelInvoiceCreateSchema(Schema):
    """Схема для створення паливної накладної"""
    date = fields.Date(required=True)
    supplier = fields.String(
        validate=validate.Length(max=200, error='Назва постачальника занадто довга')
    )
    fuel_type = fields.String(
        required=True,
        validate=validate.OneOf(['diesel', 'petrol', 'gas'], error='Невірний тип пального')
    )
    quantity = fields.Float(
        required=True,
        validate=validate.Range(min=1, error='Кількість має бути більше 0')
    )
    price_per_liter = fields.Float(
        validate=validate.Range(min=0, error='Ціна не може бути від\'ємною')
    )


class FuelRecordSchema(Schema):
    """Схема запису видачі пального для відповідей API"""
    _id = fields.String(dump_only=True)

    # Зв'язки
    invoice_id = fields.String()  # Може бути None для зовнішніх заправок
    invoice = fields.Nested('FuelInvoiceSchema', dump_only=True)
    vehicle_id = fields.String(required=True)
    vehicle = fields.Nested('VehicleSchema', dump_only=True)
    driver_id = fields.String()
    driver = fields.Nested('UserSchema', dump_only=True)
    waybill_id = fields.String()
    waybill = fields.Nested('WaybillSchema', dump_only=True)

    # Дані заправки
    date = fields.DateTime(required=True)
    quantity = fields.Float(required=True)  # Кількість (л)
    odometer = fields.Integer()  # Пробіг на момент заправки

    # Тип запису
    record_type = fields.String()  # issue (видача), external (зовнішня заправка)

    # Для зовнішніх заправок
    station = fields.String()  # Назва АЗС
    price_per_liter = fields.Float()
    total_amount = fields.Float()
    receipt_number = fields.String()

    # Хто створив запис
    created_by = fields.String()
    creator = fields.Nested('UserSchema', dump_only=True)

    notes = fields.String()

    created_at = fields.DateTime(dump_only=True)


class FuelRecordCreateSchema(Schema):
    """Схема для створення запису видачі пального"""
    invoice_id = fields.String()  # Необов'язково для зовнішніх заправок
    vehicle_id = fields.String(required=True)
    driver_id = fields.String()
    waybill_id = fields.String()
    date = fields.DateTime(required=True)
    quantity = fields.Float(
        required=True,
        validate=validate.Range(min=0.1, error='Кількість має бути більше 0')
    )
    odometer = fields.Integer(
        validate=validate.Range(min=0, error='Пробіг не може бути від\'ємним')
    )
    record_type = fields.String(
        required=True,
        validate=validate.OneOf(['issue', 'external'], error='Невірний тип запису')
    )
    station = fields.String()
    price_per_liter = fields.Float()
    receipt_number = fields.String()
    notes = fields.String()
