"""
Схеми запчастин складу
"""
from marshmallow import Schema, fields, validate

PART_CATEGORIES = ['brakes', 'filters', 'oils', 'engine', 'electrical', 'suspension', 'tyres', 'other']
PART_UNITS = ['шт', 'л', 'компл.']


class PartCreateSchema(Schema):
    name = fields.String(required=True, validate=validate.Length(min=2, max=100, error='Назва має бути від 2 до 100 символів'))
    article = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=50, error='Артикул занадто довгий'))
    category = fields.String(load_default='other', validate=validate.OneOf(PART_CATEGORIES, error='Невірна категорія запчастини'))
    unit = fields.String(load_default='шт', validate=validate.OneOf(PART_UNITS, error='Невірна одиниця виміру'))
    quantity = fields.Float(load_default=0, validate=validate.Range(min=0, error="Кількість не може бути від'ємною"))
    min_quantity = fields.Float(load_default=0, validate=validate.Range(min=0, error="Мінімальний залишок не може бути від'ємним"))
    price = fields.Float(load_default=0, validate=validate.Range(min=0, error="Ціна не може бути від'ємною"))


class PartUpdateSchema(Schema):
    name = fields.String(validate=validate.Length(min=2, max=100, error='Назва має бути від 2 до 100 символів'))
    article = fields.String(allow_none=True, validate=validate.Length(max=50, error='Артикул занадто довгий'))
    category = fields.String(validate=validate.OneOf(PART_CATEGORIES, error='Невірна категорія запчастини'))
    unit = fields.String(validate=validate.OneOf(PART_UNITS, error='Невірна одиниця виміру'))
    min_quantity = fields.Float(validate=validate.Range(min=0, error="Мінімальний залишок не може бути від'ємним"))
    price = fields.Float(validate=validate.Range(min=0, error="Ціна не може бути від'ємною"))


class StockInSchema(Schema):
    quantity = fields.Float(required=True, validate=validate.Range(min=0.01, error='Кількість має бути більше 0'))
    price = fields.Float(load_default=None, allow_none=True, validate=validate.Range(min=0, error="Ціна не може бути від'ємною"))
    note = fields.String(load_default=None, allow_none=True)
