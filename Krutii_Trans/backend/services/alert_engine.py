"""
Система сповіщень та ескалації
"""
from datetime import datetime, timedelta
from bson import ObjectId

from config import Constants


def create_alert(db, alert_type: str, category: str, title: str, message: str,
                 recipient_id: str = None, recipient_role: str = None,
                 related_type: str = None, related_id: str = None) -> str:
    """
    Створює нове сповіщення.

    Args:
        db: MongoDB database instance
        alert_type: Тип сповіщення ('info', 'warning', 'critical')
        category: Категорія ('fault', 'maintenance', 'fuel', 'general', 'escalation')
        title: Заголовок
        message: Текст повідомлення
        recipient_id: ID конкретного отримувача (опціонально)
        recipient_role: Роль отримувачів (опціонально)
        related_type: Тип пов'язаного об'єкта ('fault', 'repair', 'vehicle', 'waybill')
        related_id: ID пов'язаного об'єкта

    Returns:
        ID створеного сповіщення
    """
    alert_doc = {
        'alert_type': alert_type,
        'category': category,
        'title': title,
        'message': message,
        'recipient_id': recipient_id,
        'recipient_role': recipient_role,
        'related_type': related_type,
        'related_id': related_id,
        'is_read': False,
        'read_at': None,
        'is_dismissed': False,
        'dismissed_at': None,
        'created_at': datetime.utcnow()
    }

    result = db.alerts.insert_one(alert_doc)
    return str(result.inserted_id)


def check_fault_escalation(db, settings: dict = None):
    """
    Перевіряє несправності на потребу ескалації.

    Логіка:
    - Нова несправність без відповіді > 4 години -> сповіщення механікам
    - Нова несправність без відповіді > 24 години -> сповіщення керівнику

    Args:
        db: MongoDB database instance
        settings: Налаштування системи (для порогів ескалації)
    """
    if settings is None:
        settings_doc = db.settings.find_one({'_id': 'system'})
        settings = settings_doc if settings_doc else {}

    mechanic_hours = settings.get('fault_mechanic_hours', Constants.FAULT_MECHANIC_ESCALATION)
    manager_hours = settings.get('fault_manager_hours', Constants.FAULT_MANAGER_ESCALATION)

    now = datetime.utcnow()

    # Знаходимо нові несправності
    new_faults = list(db.fault_reports.find({
        'status': 'new',
        'report_date': {'$exists': True}
    }))

    for fault in new_faults:
        report_date = fault.get('report_date')
        if not report_date:
            continue

        hours_passed = (now - report_date).total_seconds() / 3600
        fault_id = str(fault['_id'])

        # Перевіряємо, чи вже є сповіщення про цю несправність
        existing_mechanic_alert = db.alerts.find_one({
            'related_type': 'fault',
            'related_id': fault_id,
            'category': 'escalation',
            'recipient_role': 'mechanic'
        })

        existing_manager_alert = db.alerts.find_one({
            'related_type': 'fault',
            'related_id': fault_id,
            'category': 'escalation',
            'recipient_role': 'manager'
        })

        # Ескалація до механіків (4+ години)
        if hours_passed >= mechanic_hours and not existing_mechanic_alert:
            vehicle = db.vehicles.find_one({'_id': ObjectId(fault['vehicle_id'])})
            plate = vehicle['plate_number'] if vehicle else 'Невідомо'

            create_alert(
                db,
                alert_type='warning',
                category='escalation',
                title=f'Несправність без відповіді: {plate}',
                message=f'Несправність {fault["number"]} чекає на відповідь понад {mechanic_hours} годин. '
                        f'Категорія: {fault.get("category", "Інше")}. '
                        f'Критичність: {fault.get("severity", "Невідома")}.',
                recipient_role='mechanic',
                related_type='fault',
                related_id=fault_id
            )

        # Ескалація до керівника (24+ години)
        if hours_passed >= manager_hours and not existing_manager_alert:
            vehicle = db.vehicles.find_one({'_id': ObjectId(fault['vehicle_id'])})
            plate = vehicle['plate_number'] if vehicle else 'Невідомо'

            create_alert(
                db,
                alert_type='critical',
                category='escalation',
                title=f'УВАГА: Несправність без відповіді 24+ год',
                message=f'Несправність {fault["number"]} ({plate}) не має відповіді понад {manager_hours} годин! '
                        f'Потрібне термінове втручання.',
                recipient_role='manager',
                related_type='fault',
                related_id=fault_id
            )


def check_maintenance_alerts(db, settings: dict = None):
    """
    Перевіряє транспорт на потребу ТО.

    Логіка:
    - Попередження: до ТО залишилось <= 1000 км або <= 14 днів
    - Критично: ТО прострочено

    Args:
        db: MongoDB database instance
        settings: Налаштування системи
    """
    if settings is None:
        settings_doc = db.settings.find_one({'_id': 'system'})
        settings = settings_doc if settings_doc else {}

    warning_km = settings.get('maintenance_warning_km', Constants.MAINTENANCE_WARNING_KM)
    warning_days = settings.get('maintenance_warning_days', Constants.MAINTENANCE_WARNING_DAYS)

    today = datetime.utcnow().date()
    vehicles = list(db.vehicles.find({'status': {'$in': ['active', 'repair']}}))

    for vehicle in vehicles:
        vehicle_id = str(vehicle['_id'])
        plate = vehicle['plate_number']
        odometer = vehicle.get('odometer', 0)
        next_km = vehicle.get('next_maintenance_km')
        next_date = vehicle.get('next_maintenance_date')

        needs_warning = False
        needs_critical = False
        reasons = []

        # Перевірка по кілометражу
        if next_km:
            km_remaining = next_km - odometer
            if km_remaining <= 0:
                needs_critical = True
                reasons.append(f'перевищено на {abs(km_remaining)} км')
            elif km_remaining <= warning_km:
                needs_warning = True
                reasons.append(f'залишилось {km_remaining} км')

        # Перевірка по даті
        if next_date:
            if isinstance(next_date, datetime):
                next_date = next_date.date()
            elif isinstance(next_date, str):
                try:
                    next_date = datetime.fromisoformat(next_date.replace('Z', '+00:00')).date()
                except:
                    next_date = None
            if not next_date:
                continue
            days_remaining = (next_date - today).days
            if days_remaining <= 0:
                needs_critical = True
                reasons.append(f'прострочено на {abs(days_remaining)} днів')
            elif days_remaining <= warning_days:
                needs_warning = True
                reasons.append(f'залишилось {days_remaining} днів')

        if not needs_warning and not needs_critical:
            continue

        # Перевіряємо, чи вже є актуальне сповіщення
        alert_type = 'critical' if needs_critical else 'warning'

        # Видаляємо старі сповіщення про ТО для цього авто
        db.alerts.delete_many({
            'related_type': 'vehicle',
            'related_id': vehicle_id,
            'category': 'maintenance',
            'is_dismissed': False,
            'created_at': {'$lt': datetime.utcnow() - timedelta(days=1)}  # Старші за добу
        })

        # Перевіряємо, чи є свіже сповіщення
        existing = db.alerts.find_one({
            'related_type': 'vehicle',
            'related_id': vehicle_id,
            'category': 'maintenance',
            'alert_type': alert_type,
            'created_at': {'$gte': datetime.utcnow() - timedelta(days=1)}
        })

        if existing:
            continue

        title = f'{"УВАГА: " if needs_critical else ""}ТО для {plate}'
        message = f'Транспорт {plate} потребує технічного обслуговування: {", ".join(reasons)}.'

        create_alert(
            db,
            alert_type=alert_type,
            category='maintenance',
            title=title,
            message=message,
            recipient_role='mechanic',
            related_type='vehicle',
            related_id=vehicle_id
        )

        # Критичні - також керівнику
        if needs_critical:
            create_alert(
                db,
                alert_type='critical',
                category='maintenance',
                title=title,
                message=message,
                recipient_role='manager',
                related_type='vehicle',
                related_id=vehicle_id
            )


def setup_scheduler(scheduler, app):
    """
    Налаштовує планувальник завдань.

    Args:
        scheduler: APScheduler BackgroundScheduler instance
        app: Flask app instance
    """
    def run_fault_check():
        with app.app_context():
            from extensions import mongo
            check_fault_escalation(mongo.db)

    def run_maintenance_check():
        with app.app_context():
            from extensions import mongo
            check_maintenance_alerts(mongo.db)

    # Перевірка несправностей кожні 30 хвилин
    scheduler.add_job(
        run_fault_check,
        'interval',
        minutes=30,
        id='fault_escalation_check',
        replace_existing=True
    )

    # Перевірка ТО щодня о 8:00
    scheduler.add_job(
        run_maintenance_check,
        'cron',
        hour=8,
        minute=0,
        id='maintenance_check',
        replace_existing=True
    )

    # Також запускаємо перевірку ТО при старті (з затримкою)
    scheduler.add_job(
        run_maintenance_check,
        'date',
        run_date=datetime.utcnow() + timedelta(seconds=30),
        id='maintenance_check_startup'
    )
