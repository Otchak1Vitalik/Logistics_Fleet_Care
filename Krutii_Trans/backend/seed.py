"""
Seed script - ініціалізація демонстраційних даних
Розширена версія з великою кількістю документів
"""
import bcrypt
import random
from datetime import datetime, timedelta
from pymongo import MongoClient

from config import Config


def seed_database():
    """Заповнює базу даних початковими даними."""
    client = MongoClient(Config.MONGO_URI)
    db = client.get_database()

    print('Початок ініціалізації даних...')

    # Очищення існуючих даних
    collections = ['users', 'vehicles', 'waybills', 'fuel_invoices', 'fuel_records',
                   'fault_reports', 'repairs', 'alerts', 'settings']
    for col in collections:
        db[col].delete_many({})
    print('Очищено існуючі дані.')

    # === Користувачі ===
    def hash_password(password):
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    users = [
        # Керівник (один)
        {
            'username': 'admin',
            'password_hash': hash_password('Admin1234'),
            'full_name': 'Богатир Василь Петрович',
            'role': 'manager',
            'phone': '+380501234567',
            'email': 'admin@bogatur.ua',
            'is_active': True,
            'created_at': datetime.utcnow() - timedelta(days=365),
            'updated_at': datetime.utcnow()
        },
        # Механіки (2)
        {
            'username': 'mech_koval',
            'password_hash': hash_password('Mech1234'),
            'full_name': 'Коваль Олександр Іванович',
            'role': 'mechanic',
            'phone': '+380502345678',
            'email': 'koval@bogatur.ua',
            'is_active': True,
            'created_at': datetime.utcnow() - timedelta(days=300),
            'updated_at': datetime.utcnow()
        },
        {
            'username': 'mech_petruk',
            'password_hash': hash_password('Mech1234'),
            'full_name': 'Петрук Михайло Сергійович',
            'role': 'mechanic',
            'phone': '+380503456789',
            'email': 'petruk@bogatur.ua',
            'is_active': True,
            'created_at': datetime.utcnow() - timedelta(days=280),
            'updated_at': datetime.utcnow()
        },
        # Водії (8)
        {
            'username': 'driver_ivanov',
            'password_hash': hash_password('Driver1234'),
            'full_name': 'Іванов Петро Миколайович',
            'role': 'driver',
            'phone': '+380504567890',
            'license_number': 'АВС123456',
            'license_expiry': (datetime.utcnow() + timedelta(days=365)).isoformat()[:10],
            'is_active': True,
            'created_at': datetime.utcnow() - timedelta(days=250),
            'updated_at': datetime.utcnow()
        },
        {
            'username': 'driver_sydorenko',
            'password_hash': hash_password('Driver1234'),
            'full_name': 'Сидоренко Андрій Васильович',
            'role': 'driver',
            'phone': '+380505678901',
            'license_number': 'ВСА654321',
            'license_expiry': (datetime.utcnow() + timedelta(days=200)).isoformat()[:10],
            'is_active': True,
            'created_at': datetime.utcnow() - timedelta(days=230),
            'updated_at': datetime.utcnow()
        },
        {
            'username': 'driver_kovalchuk',
            'password_hash': hash_password('Driver1234'),
            'full_name': 'Ковальчук Олег Романович',
            'role': 'driver',
            'phone': '+380506789012',
            'license_number': 'САВ111222',
            'license_expiry': (datetime.utcnow() + timedelta(days=500)).isoformat()[:10],
            'is_active': True,
            'created_at': datetime.utcnow() - timedelta(days=200),
            'updated_at': datetime.utcnow()
        },
        {
            'username': 'driver_bondar',
            'password_hash': hash_password('Driver1234'),
            'full_name': 'Бондар Ігор Степанович',
            'role': 'driver',
            'phone': '+380507890123',
            'license_number': 'АСВ333444',
            'license_expiry': (datetime.utcnow() + timedelta(days=100)).isoformat()[:10],
            'is_active': True,
            'created_at': datetime.utcnow() - timedelta(days=180),
            'updated_at': datetime.utcnow()
        },
        {
            'username': 'driver_melnyk',
            'password_hash': hash_password('Driver1234'),
            'full_name': 'Мельник Сергій Олександрович',
            'role': 'driver',
            'phone': '+380508901234',
            'license_number': 'ВАС555666',
            'license_expiry': (datetime.utcnow() + timedelta(days=730)).isoformat()[:10],
            'is_active': True,
            'created_at': datetime.utcnow() - timedelta(days=160),
            'updated_at': datetime.utcnow()
        },
        {
            'username': 'driver_shevchenko',
            'password_hash': hash_password('Driver1234'),
            'full_name': 'Шевченко Віктор Павлович',
            'role': 'driver',
            'phone': '+380509012345',
            'license_number': 'СВА777888',
            'license_expiry': (datetime.utcnow() + timedelta(days=450)).isoformat()[:10],
            'is_active': True,
            'created_at': datetime.utcnow() - timedelta(days=140),
            'updated_at': datetime.utcnow()
        },
        {
            'username': 'driver_tkachenko',
            'password_hash': hash_password('Driver1234'),
            'full_name': 'Ткаченко Роман Ігорович',
            'role': 'driver',
            'phone': '+380501234890',
            'license_number': 'АВС999000',
            'license_expiry': (datetime.utcnow() + timedelta(days=600)).isoformat()[:10],
            'is_active': True,
            'created_at': datetime.utcnow() - timedelta(days=120),
            'updated_at': datetime.utcnow()
        },
        {
            'username': 'driver_moroz',
            'password_hash': hash_password('Driver1234'),
            'full_name': 'Мороз Денис Олегович',
            'role': 'driver',
            'phone': '+380502345890',
            'license_number': 'ВСА112233',
            'license_expiry': (datetime.utcnow() + timedelta(days=300)).isoformat()[:10],
            'is_active': True,
            'created_at': datetime.utcnow() - timedelta(days=100),
            'updated_at': datetime.utcnow()
        }
    ]

    result = db.users.insert_many(users)
    user_ids = {users[i]['username']: str(result.inserted_ids[i]) for i in range(len(users))}
    driver_usernames = [u['username'] for u in users if u['role'] == 'driver']
    mechanic_usernames = [u['username'] for u in users if u['role'] == 'mechanic']
    print(f'Створено {len(users)} користувачів (1 керівник, 2 механіки, 8 водіїв).')

    # === Транспортні засоби (12 одиниць) ===
    vehicles_data = [
        ('AA1234BB', 'MAN', 'TGX 18.440', 2020, 'WMAN05ZZ1LY123456', 28.0, 400, 125000),
        ('AA5678CC', 'Volvo', 'FH 500', 2021, 'YV2RT40A5LB654321', 26.5, 450, 89000),
        ('AA9012DD', 'Scania', 'R 450', 2019, 'YS2R4X20005987654', 27.0, 400, 198000),
        ('AA3456EE', 'DAF', 'XF 480', 2022, 'XLRTE47MS0E111222', 25.5, 380, 45000),
        ('AA7890FF', 'Mercedes-Benz', 'Actros 1845', 2020, 'WDB96340310333444', 24.0, 420, 156000),
        ('BB1234AA', 'MAN', 'TGS 18.320', 2018, 'WMAN05ZZ2JY234567', 30.0, 350, 245000),
        ('BB5678CC', 'Volvo', 'FM 420', 2019, 'YV2RT40A6KB765432', 29.0, 400, 178000),
        ('BB9012DD', 'Scania', 'G 410', 2021, 'YS2R4X20006098765', 26.0, 380, 67000),
        ('CC1234AA', 'DAF', 'CF 450', 2020, 'XLRTE47MS1F222333', 27.5, 400, 112000),
        ('CC5678BB', 'Mercedes-Benz', 'Arocs 1843', 2019, 'WDB96340320444555', 31.0, 450, 189000),
        ('DD1234AA', 'Iveco', 'Stralis 460', 2020, 'WJMM1VPH50C555666', 28.5, 400, 134000),
        ('DD5678BB', 'Renault', 'T 480', 2021, 'VF622GVA000666777', 25.0, 420, 78000),
    ]

    vehicles = []
    statuses = ['active', 'active', 'active', 'active', 'active', 'active',
                'active', 'active', 'repair', 'active', 'inspection', 'active']

    for i, (plate, brand, model, year, vin, norm, tank, odo) in enumerate(vehicles_data):
        last_maint = random.randint(5000, 10000)
        vehicles.append({
            'plate_number': plate,
            'brand': brand,
            'model': model,
            'year': year,
            'vin': vin,
            'status': statuses[i],
            'fuel_type': 'diesel',
            'fuel_norm': norm,
            'tank_capacity': tank,
            'odometer': odo,
            'last_maintenance_km': odo - last_maint,
            'last_maintenance_date': (datetime.utcnow() - timedelta(days=random.randint(20, 90))).isoformat()[:10],
            'next_maintenance_km': odo + (10000 - last_maint),
            'next_maintenance_date': (datetime.utcnow() + timedelta(days=random.randint(10, 90))).isoformat()[:10],
            'inspection_expiry': (datetime.utcnow() + timedelta(days=random.randint(30, 400))).isoformat()[:10],
            'insurance_policy': f'СТР-{str(i+1).zfill(3)}-2024',
            'insurance_expiry': (datetime.utcnow() + timedelta(days=random.randint(100, 400))).isoformat()[:10],
            'created_at': datetime.utcnow() - timedelta(days=random.randint(100, 365)),
            'updated_at': datetime.utcnow()
        })

    result = db.vehicles.insert_many(vehicles)
    vehicle_ids = {vehicles[i]['plate_number']: str(result.inserted_ids[i]) for i in range(len(vehicles))}
    plate_numbers = list(vehicle_ids.keys())
    print(f'Створено {len(vehicles)} транспортних засобів.')

    # === Путівки (30 штук) ===
    routes = [
        ('Київ', 'Львів', 'Доставка будматеріалів'),
        ('Львів', 'Одеса', 'Перевезення продуктів'),
        ('Одеса', 'Харків', 'Доставка обладнання'),
        ('Харків', 'Дніпро', 'Вантаж для заводу'),
        ('Дніпро', 'Запоріжжя', 'Комплектуючі'),
        ('Київ', 'Вінниця', 'Товари для супермаркету'),
        ('Вінниця', 'Житомир', 'Сільгосппродукція'),
        ('Житомир', 'Рівне', 'Меблі'),
        ('Рівне', 'Луцьк', 'Електроніка'),
        ('Луцьк', 'Тернопіль', 'Текстиль'),
        ('Київ', 'Чернігів', 'Будівельні матеріали'),
        ('Київ', 'Полтава', 'Промислове обладнання'),
        ('Полтава', 'Суми', 'Медичне обладнання'),
        ('Суми', 'Київ', 'Порожній рейс'),
        ('Львів', 'Ужгород', 'Експортний вантаж'),
    ]

    waybills = []
    waybill_num = 100001

    for i in range(30):
        days_ago = random.randint(0, 60)
        route = random.choice(routes)
        plate = random.choice(plate_numbers[:8])  # Тільки активні авто
        driver = random.choice(driver_usernames)
        distance = random.randint(200, 800)
        fuel_norm = next(v['fuel_norm'] for v in vehicles if v['plate_number'] == plate)
        fuel_issued = int(distance / 100 * fuel_norm * 1.1)

        if days_ago > 0:
            # Завершена путівка
            fuel_used = int(fuel_issued * random.uniform(0.85, 1.15))
            status = 'completed'
            odo_start = random.randint(50000, 200000)
            odo_end = odo_start + distance
            completed_at = datetime.utcnow() - timedelta(days=days_ago - 1)
        else:
            # Активна або видана
            fuel_used = None
            status = random.choice(['issued', 'active'])
            odo_start = random.randint(50000, 200000)
            odo_end = None
            completed_at = None

        waybills.append({
            'number': f'ПЛ-{waybill_num}',
            'vehicle_id': vehicle_ids[plate],
            'driver_id': user_ids[driver],
            'issued_by': user_ids['admin'],
            'issue_date': (datetime.utcnow() - timedelta(days=days_ago)).isoformat()[:10],
            'valid_from': datetime.utcnow() - timedelta(days=days_ago),
            'valid_until': datetime.utcnow() - timedelta(days=days_ago) + timedelta(hours=24),
            'route_from': route[0],
            'route_to': route[1],
            'route_description': route[2],
            'odometer_start': odo_start,
            'odometer_end': odo_end,
            'fuel_issued': fuel_issued,
            'fuel_used': fuel_used,
            'status': status,
            'notes': None,
            'completion_notes': 'Доставлено вчасно' if status == 'completed' else None,
            'created_at': datetime.utcnow() - timedelta(days=days_ago),
            'updated_at': datetime.utcnow() - timedelta(days=days_ago - 1) if days_ago > 0 else datetime.utcnow(),
            'completed_at': completed_at
        })
        waybill_num += 1

    db.waybills.insert_many(waybills)
    print(f'Створено {len(waybills)} путівок.')

    # === Несправності (15 штук) ===
    fault_categories = ['engine', 'transmission', 'brakes', 'electrical', 'suspension', 'tires', 'cooling', 'fuel_system']
    fault_descriptions = {
        'engine': ['Підвищена температура двигуна', 'Сторонній шум при роботі', 'Втрата потужності', 'Димить вихлопна'],
        'transmission': ['Важко вмикаються передачі', 'Хрускіт при перемиканні', 'Вібрація на швидкості'],
        'brakes': ['Скрип гальмівних колодок', 'Збільшений хід педалі', 'Биття при гальмуванні'],
        'electrical': ['Не працює поворотник', 'Проблеми з акумулятором', 'Збій бортового компютера'],
        'suspension': ['Стукіт в підвісці', 'Просідання на одну сторону', 'Витік амортизатора'],
        'tires': ['Нерівномірний знос шин', 'Пошкодження бокової стінки', 'Биття на швидкості'],
        'cooling': ['Витік антифризу', 'Не працює вентилятор', 'Перегрів двигуна'],
        'fuel_system': ['Підвищена витрата пального', 'Витік палива', 'Проблеми з форсунками']
    }

    faults = []
    fault_num = 200001
    fault_statuses = ['new', 'new', 'acknowledged', 'acknowledged', 'in_repair',
                      'resolved', 'resolved', 'resolved', 'resolved', 'rejected']

    for i in range(15):
        hours_ago = random.randint(2, 200)
        category = random.choice(fault_categories)
        desc = random.choice(fault_descriptions[category])
        plate = random.choice(plate_numbers)
        driver = random.choice(driver_usernames)
        severity = random.choice(['low', 'medium', 'medium', 'high', 'critical'])
        status = random.choice(fault_statuses)

        fault = {
            'number': f'НС-{fault_num}',
            'vehicle_id': vehicle_ids[plate],
            'reported_by': user_ids[driver],
            'report_date': datetime.utcnow() - timedelta(hours=hours_ago),
            'category': category,
            'severity': severity,
            'description': desc,
            'odometer': random.randint(50000, 200000),
            'status': status,
            'created_at': datetime.utcnow() - timedelta(hours=hours_ago),
            'updated_at': datetime.utcnow() - timedelta(hours=max(0, hours_ago - random.randint(1, 10)))
        }

        if status in ['acknowledged', 'in_repair', 'resolved', 'rejected']:
            mechanic = random.choice(mechanic_usernames)
            fault['acknowledged_by'] = user_ids[mechanic]
            fault['acknowledged_at'] = datetime.utcnow() - timedelta(hours=hours_ago - 2)

        if status == 'resolved':
            fault['resolution'] = 'Несправність усунено'
            fault['resolved_at'] = datetime.utcnow() - timedelta(hours=hours_ago - 24)

        if status == 'rejected':
            fault['resolution'] = 'Несправність не підтверджена при огляді'
            fault['resolved_at'] = datetime.utcnow() - timedelta(hours=hours_ago - 4)

        faults.append(fault)
        fault_num += 1

    result = db.fault_reports.insert_many(faults)
    fault_ids = [str(fid) for fid in result.inserted_ids]
    print(f'Створено {len(faults)} звітів про несправності.')

    # === Ремонти (20 штук) ===
    repair_types = ['maintenance', 'repair', 'repair', 'maintenance', 'inspection']
    repair_descriptions = [
        'Планове ТО: заміна масла та фільтрів',
        'Заміна гальмівних колодок',
        'Ремонт системи охолодження',
        'Діагностика електросистеми',
        'Заміна ременя ГРМ',
        'Ремонт підвіски',
        'Заміна шин',
        'Ремонт паливної системи',
        'Технічний огляд',
        'Заміна зчеплення',
        'Ремонт КПП',
        'Заміна акумулятора',
        'Регулювання клапанів',
        'Заміна турбіни',
        'Ремонт пневмосистеми'
    ]

    repairs = []
    repair_num = 300001

    for i in range(20):
        days_ago = random.randint(0, 90)
        plate = random.choice(plate_numbers)
        mechanic = random.choice(mechanic_usernames)
        repair_type = random.choice(repair_types)
        desc = random.choice(repair_descriptions)

        if days_ago > 10:
            status = random.choice(['completed', 'completed', 'completed', 'cancelled'])
            completed_at = datetime.utcnow() - timedelta(days=days_ago - random.randint(1, 5))
            started_at = datetime.utcnow() - timedelta(days=days_ago)
            labor_hours = round(random.uniform(2, 16), 1)
            labor_cost = int(labor_hours * 500)
            parts_cost = random.randint(1000, 25000)
        elif days_ago > 0:
            status = random.choice(['in_progress', 'completed'])
            started_at = datetime.utcnow() - timedelta(days=days_ago)
            completed_at = datetime.utcnow() - timedelta(days=1) if status == 'completed' else None
            labor_hours = round(random.uniform(2, 8), 1) if status == 'completed' else None
            labor_cost = int(labor_hours * 500) if labor_hours else None
            parts_cost = random.randint(1000, 15000) if status == 'completed' else None
        else:
            status = random.choice(['planned', 'in_progress'])
            started_at = datetime.utcnow() if status == 'in_progress' else None
            completed_at = None
            labor_hours = None
            labor_cost = None
            parts_cost = None

        repairs.append({
            'number': f'РМ-{repair_num}',
            'vehicle_id': vehicle_ids[plate],
            'mechanic_id': user_ids[mechanic],
            'fault_id': random.choice(fault_ids) if random.random() > 0.5 else None,
            'repair_type': repair_type,
            'description': desc,
            'scheduled_date': (datetime.utcnow() - timedelta(days=days_ago)).isoformat()[:10],
            'started_at': started_at,
            'completed_at': completed_at,
            'odometer': random.randint(50000, 200000),
            'status': status,
            'work_performed': desc if status == 'completed' else None,
            'parts_used': [],
            'labor_hours': labor_hours,
            'labor_cost': labor_cost,
            'parts_cost': parts_cost,
            'notes': None,
            'created_by': user_ids[mechanic],
            'created_at': datetime.utcnow() - timedelta(days=days_ago + 1),
            'updated_at': datetime.utcnow() - timedelta(days=max(0, days_ago - 5))
        })
        repair_num += 1

    db.repairs.insert_many(repairs)
    print(f'Створено {len(repairs)} ремонтів.')

    # === Паливні накладні (12 штук) ===
    suppliers = ['ОККО', 'WOG', 'Shell', 'БРСМ-Нафта', 'Авіас']
    invoices = []
    invoice_num = 400001

    for i in range(12):
        days_ago = i * 5 + random.randint(0, 3)
        supplier = random.choice(suppliers)
        quantity = random.randint(1500, 5000)
        price = round(random.uniform(48.0, 56.0), 2)
        distributed = int(quantity * random.uniform(0.3, 0.9)) if days_ago > 5 else 0

        invoices.append({
            'number': f'НП-{invoice_num}',
            'date': (datetime.utcnow() - timedelta(days=days_ago)).isoformat()[:10],
            'supplier': supplier,
            'fuel_type': 'diesel',
            'quantity': quantity,
            'price_per_liter': price,
            'total_amount': round(quantity * price, 2),
            'distributed': distributed,
            'created_by': user_ids['admin'],
            'created_at': datetime.utcnow() - timedelta(days=days_ago),
            'updated_at': datetime.utcnow() - timedelta(days=max(0, days_ago - 3))
        })
        invoice_num += 1

    db.fuel_invoices.insert_many(invoices)
    print(f'Створено {len(invoices)} паливних накладних.')

    # === Записи про видачу пального (50 штук) ===
    fuel_records = []
    for i in range(50):
        days_ago = random.randint(0, 60)
        plate = random.choice(plate_numbers[:8])
        driver = random.choice(driver_usernames)
        quantity = random.randint(100, 400)

        fuel_records.append({
            'vehicle_id': vehicle_ids[plate],
            'driver_id': user_ids[driver],
            'date': (datetime.utcnow() - timedelta(days=days_ago)).isoformat()[:10],
            'fuel_type': 'diesel',
            'quantity': quantity,
            'odometer': random.randint(50000, 200000),
            'source': random.choice(['invoice', 'station']),
            'notes': None,
            'created_by': user_ids['admin'],
            'created_at': datetime.utcnow() - timedelta(days=days_ago),
            'updated_at': datetime.utcnow() - timedelta(days=days_ago)
        })

    db.fuel_records.insert_many(fuel_records)
    print(f'Створено {len(fuel_records)} записів про видачу пального.')

    # === Сповіщення (25 штук) ===
    alert_types = ['info', 'warning', 'warning', 'critical']
    alert_categories = ['maintenance', 'fuel', 'fault', 'escalation', 'general']
    alert_titles = {
        'maintenance': ['Наближається ТО', 'Прострочене ТО', 'Закінчується техогляд', 'Потрібна заміна шин'],
        'fuel': ['Перевитрата пального', 'Низький залишок пального', 'Підозріла витрата'],
        'fault': ['Нова несправність', 'Критична несправність', 'Несправність не підтверджена'],
        'escalation': ['Несправність без відповіді', 'Ескалація керівнику', 'Терміновий ремонт'],
        'general': ['Нагадування', 'Системне повідомлення', 'Оновлення даних']
    }

    alerts = []
    for i in range(25):
        hours_ago = random.randint(1, 200)
        alert_type = random.choice(alert_types)
        category = random.choice(alert_categories)
        title = random.choice(alert_titles[category])

        alerts.append({
            'user_id': user_ids['admin'],
            'alert_type': alert_type,
            'category': category,
            'title': title,
            'message': f'{title} - потребує уваги',
            'is_read': random.random() > 0.4,
            'related_entity': random.choice(['vehicle', 'waybill', 'fault', None]),
            'related_id': None,
            'created_at': datetime.utcnow() - timedelta(hours=hours_ago),
            'read_at': datetime.utcnow() - timedelta(hours=hours_ago - 1) if random.random() > 0.5 else None
        })

    # Сповіщення для механіків
    for mechanic in mechanic_usernames:
        for i in range(8):
            hours_ago = random.randint(1, 100)
            category = random.choice(['fault', 'maintenance', 'escalation'])
            title = random.choice(alert_titles[category])

            alerts.append({
                'user_id': user_ids[mechanic],
                'alert_type': random.choice(['warning', 'critical']),
                'category': category,
                'title': title,
                'message': f'{title} - потребує уваги',
                'is_read': random.random() > 0.5,
                'related_entity': 'fault',
                'related_id': None,
                'created_at': datetime.utcnow() - timedelta(hours=hours_ago),
                'read_at': None
            })

    db.alerts.insert_many(alerts)
    print(f'Створено {len(alerts)} сповіщень.')

    # === Налаштування ===
    settings = {
        '_id': 'system',
        'default_fuel_norm': 25.0,
        'overspend_threshold': 10,
        'winter_coefficient': 1.09,
        'maintenance_warning_km': 1000,
        'maintenance_warning_days': 14,
        'maintenance_interval_km': 10000,
        'fault_mechanic_hours': 4,
        'fault_manager_hours': 24,
        'company_name': 'KRUTII TRANS',
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow()
    }

    db.settings.insert_one(settings)
    print('Створено налаштування системи.')

    print('\n' + '=' * 50)
    print('ІНІЦІАЛІЗАЦІЯ ЗАВЕРШЕНА')
    print('=' * 50)
    print(f'\nСтатистика:')
    print(f'  Користувачі: {len(users)} (1 керівник, 2 механіки, 8 водіїв)')
    print(f'  Транспорт: {len(vehicles)} одиниць')
    print(f'  Путівки: {len(waybills)}')
    print(f'  Несправності: {len(faults)}')
    print(f'  Ремонти: {len(repairs)}')
    print(f'  Паливні накладні: {len(invoices)}')
    print(f'  Записи пального: {len(fuel_records)}')
    print(f'  Сповіщення: {len(alerts)}')
    print('\nОблікові записи для входу:')
    print('  Керівник: admin / Admin1234')
    print('  Механік:  mech_koval / Mech1234')
    print('  Водій:    driver_ivanov / Driver1234')


if __name__ == '__main__':
    seed_database()
