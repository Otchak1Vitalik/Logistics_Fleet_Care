"""
Індекси MongoDB для запитів, які виконуються найчастіше
(фонові перевірки ТО та ескалації, списки, дашборд).
Створення індексу ідемпотентне: повторний виклик нічого не змінює.
"""
from pymongo import ASCENDING, DESCENDING


def ensure_indexes(db):
    db.users.create_index('username', unique=True)
    db.vehicles.create_index('status')
    db.waybills.create_index([('vehicle_id', ASCENDING), ('status', ASCENDING)])
    db.waybills.create_index([('driver_id', ASCENDING), ('status', ASCENDING)])
    db.fault_reports.create_index([('status', ASCENDING), ('report_date', DESCENDING)])
    db.fault_reports.create_index('vehicle_id')
    db.repairs.create_index([('vehicle_id', ASCENDING), ('status', ASCENDING)])
    db.alerts.create_index([('recipient_role', ASCENDING), ('is_read', ASCENDING)])
    db.alerts.create_index([('related_type', ASCENDING), ('related_id', ASCENDING), ('category', ASCENDING)])
    db.parts.create_index('name', unique=True)
    db.part_movements.create_index([('part_id', ASCENDING), ('created_at', DESCENDING)])
    db.waybills.create_index([('status', ASCENDING), ('completed_at', DESCENDING)])
