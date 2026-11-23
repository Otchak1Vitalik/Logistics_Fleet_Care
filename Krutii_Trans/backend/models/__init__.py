# Модуль моделей (Marshmallow schemas)
from .user import UserSchema, UserCreateSchema, UserUpdateSchema, PasswordChangeSchema
from .vehicle import VehicleSchema, VehicleCreateSchema, VehicleUpdateSchema
from .waybill import WaybillSchema, WaybillCreateSchema, WaybillUpdateSchema
from .fuel import FuelInvoiceSchema, FuelRecordSchema, FuelInvoiceCreateSchema, FuelRecordCreateSchema
from .fault import FaultSchema, FaultCreateSchema, FaultUpdateSchema
from .repair import RepairSchema, RepairCreateSchema, RepairUpdateSchema
from .alert import AlertSchema
from .settings import SettingsSchema
