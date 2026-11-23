"""
Система сповіщень та ескалації
"""
import math
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


def _to_date(value):
    """Приводить дату ТО (datetime або рядок ISO) до типу date."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00')).date()
        except ValueError:
            return None
    return None


def check_vehicle_maintenance(db, vehicle: dict, settings: dict = None, avg_daily_km: float = None):
    """
    Перевіряє один транспортний засіб на потребу ТО і за потреби створює сповіщення.

    Логіка:
    - Попередження: до ТО залишилось <= maintenance_warning_km або <= maintenance_warning_days
    - Критично: ТО прострочено (за пробігом або за датою) -> механікам і керівнику

    Повертає тип створеного сповіщення ('warning' / 'critical') або None.
    """
    if settings is None:
        settings = db.settings.find_one({'_id': 'system'}) or {}

    warning_km = settings.get('maintenance_warning_km', Constants.MAINTENANCE_WARNING_KM)
    warning_days = settings.get('maintenance_warning_days', Constants.MAINTENANCE_WARNING_DAYS)
    today = datetime.utcnow().date()

    vehicle_id = str(vehicle['_id'])
    plate = vehicle['plate_number']
    odometer = vehicle.get('odometer', 0)
    next_km = vehicle.get('next_maintenance_km')
    next_date = _to_date(vehicle.get('next_maintenance_date'))

    needs_warning = False
    needs_critical = False
    reasons = []

    # Перевірка за пробігом
    if next_km:
        km_remaining = next_km - odometer
        if km_remaining <= 0:
            needs_critical = True
            reasons.append(f'перевищено на {abs(km_remaining)} км')
        elif km_remaining <= warning_km:
            needs_warning = True
            reasons.append(f'залишилось {km_remaining} км')

    # Перевірка за датою (некоректна дата не блокує перевірку за пробігом)
    if next_date:
        days_remaining = (next_date - today).days
        if days_remaining <= 0:
            needs_critical = True
            reasons.append(f'прострочено на {abs(days_remaining)} днів')
        elif days_remaining <= warning_days:
            needs_warning = True
            reasons.append(f'залишилось {days_remaining} днів')

    # Прогноз: за середнім добовим пробігом ТО настане раніше, ніж через поріг попередження
    if not needs_warning and not needs_critical and next_km and avg_daily_km:
        km_remaining = next_km - odometer
        forecast_days = math.ceil(km_remaining / avg_daily_km) if km_remaining > 0 else 0
        if forecast_days <= warning_days:
            needs_warning = True
            reasons.append(f'за прогнозом через {forecast_days} дн. (≈{round(avg_daily_km)} км/добу)')

    if not needs_warning and not needs_critical:
        return None

    alert_type = 'critical' if needs_critical else 'warning'

    # Видаляємо застарілі (старші за добу) сповіщення про ТО для цього авто
    db.alerts.delete_many({
        'related_type': 'vehicle',
        'related_id': vehicle_id,
        'category': 'maintenance',
        'is_dismissed': False,
        'created_at': {'$lt': datetime.utcnow() - timedelta(days=1)}
    })

    # Не дублюємо свіже сповіщення того ж рівня
    existing = db.alerts.find_one({
        'related_type': 'vehicle',
        'related_id': vehicle_id,
        'category': 'maintenance',
        'alert_type': alert_type,
        'created_at': {'$gte': datetime.utcnow() - timedelta(days=1)}
    })
    if existing:
        return None

    title = f'{"УВАГА: " if needs_critical else ""}ТО для {plate}'
    message = f'Транспорт {plate} потребує технічного обслуговування: {", ".join(reasons)}.'

    create_alert(db, alert_type=alert_type, category='maintenance', title=title, message=message,
                 recipient_role='mechanic', related_type='vehicle', related_id=vehicle_id)

    # Критичні - також керівнику
    if needs_critical:
        create_alert(db, alert_type='critical', category='maintenance', title=title, message=message,
                     recipient_role='manager', related_type='vehicle', related_id=vehicle_id)

    return alert_type


def check_maintenance_alerts(db, settings: dict = None):
    """
    Періодична перевірка всього автопарку на потребу ТО.

    Args:
        db: MongoDB database instance
        settings: Налаштування системи
    """
    if settings is None:
        settings = db.settings.find_one({'_id': 'system'}) or {}

    from services.maintenance_forecast import daily_mileage
    rates = daily_mileage(db)
    for vehicle in db.vehicles.find({'status': {'$in': ['active', 'repair']}}):
        check_vehicle_maintenance(db, vehicle, settings, rates.get(str(vehicle['_id'])))


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

    # Також запускаємо перевірку ТО при старті (з затримкою).
    # Планувальник працює в локальному часовому поясі, тому використовуємо datetime.now(),
    # а не utcnow() - інакше задача вважається пропущеною і не виконується.
    scheduler.add_job(
        run_maintenance_check,
        'date',
        run_date=datetime.now() + timedelta(seconds=30),
        id='maintenance_check_startup'
    )
