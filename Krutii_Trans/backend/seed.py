"""
Seed script - ініціалізація демонстраційних даних
Розширена версія з великою кількістю документів
"""
import bcrypt
import random
from datetime import datetime, timedelta
from pymongo import MongoClient

from config import Config


def day_start(dt):
    """Дата без часу у форматі datetime (MongoDB коректно порівнює лише однакові типи)."""
    return datetime(dt.year, dt.month, dt.day)


def seed_database():
    """Заповнює базу даних початковими даними."""
    client = MongoClient(Config.MONGO_URI)
    db = client.get_database()

    print('Початок ініціалізації даних...')

    # Очищення існуючих даних
    collections = ['users', 'vehicles', 'waybills', 'fuel_invoices', 'fuel_records',
                   'fault_reports', 'repairs', 'alerts', 'settings', 'audit_log', 'login_codes']
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
            'full_name': 'Литвиненко Василь Петрович',
            'role': 'manager',
            'phone': '+380501234567',
            'email': 'admin@krutiitrans.ua',
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
            'email': 'koval@krutiitrans.ua',
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
            'email': 'petruk@krutiitrans.ua',
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
            'license_expiry': day_start(datetime.utcnow() + timedelta(days=20)),  # спливає скоро - видно в профілі
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
            'license_expiry': day_start(datetime.utcnow() + timedelta(days=200)),
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
            'license_expiry': day_start(datetime.utcnow() + timedelta(days=500)),
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
            'license_expiry': day_start(datetime.utcnow() + timedelta(days=100)),
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
            'license_expiry': day_start(datetime.utcnow() + timedelta(days=730)),
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
            'license_expiry': day_start(datetime.utcnow() + timedelta(days=450)),
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
            'license_expiry': day_start(datetime.utcnow() + timedelta(days=600)),
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
            'license_expiry': day_start(datetime.utcnow() + timedelta(days=300)),
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

    # === Транспортні засоби (31 одиниця: дизель, бензин, газ; різні статуси) ===
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
        # Легкі фургони на бензині
        ('KA1122AB', 'Toyota', 'Hiace 2.7', 2019, 'JTFSS22P900123456', 13.5, 70, 98000, 'petrol'),
        ('KA3344CD', 'Volkswagen', 'Transporter T6 2.0 TSI', 2020, 'WV1ZZZ7HZLH012345', 12.0, 80, 64000, 'petrol'),
        ('KA5566EF', 'Renault', 'Kangoo 1.6', 2021, 'VF1KW0BB565123456', 8.5, 60, 41000, 'petrol'),
        # Авто на газу (метан, CNG)
        ('KB1122AB', 'Iveco', 'Daily 35S14 CNG', 2021, 'ZCFC135D005654321', 14.0, 220, 72000, 'gas'),
        ('KB3344CD', 'Mercedes-Benz', 'Sprinter 316 NGT', 2018, 'WDB9066331S765432', 15.5, 200, 154000, 'gas'),
        ('KB5566EF', 'Scania', 'G 340 CNG', 2020, 'YS2G4X20005876543', 30.0, 500, 118000, 'gas'),
        # Ще бензинові: 1 в експлуатації, 2 в ремонті, 2 на огляді
        ('KA7788GH', 'Citroen', 'Berlingo 1.2 PureTech', 2021, 'VR7EFHNSMMJ123456', 7.5, 50, 38000, 'petrol', 'active'),
        ('KA9900IK', 'Peugeot', 'Partner 1.2 PureTech', 2020, 'VR3EFHNSMLJ234567', 7.8, 50, 57000, 'petrol', 'repair'),
        ('KA2233LM', 'Fiat', 'Doblo 1.4', 2018, 'ZFA26300006345678', 8.9, 60, 132000, 'petrol', 'repair'),
        ('KA4455NO', 'Opel', 'Combo 1.2 Turbo', 2022, 'VXEEFHNSMNJ456789', 7.2, 50, 26000, 'petrol', 'inspection'),
        ('KA6677PR', 'Volkswagen', 'Caddy 1.5 TSI', 2021, 'WV1ZZZSKZMX567890', 7.9, 50, 49000, 'petrol', 'inspection'),
        # Ще газові: 1 в експлуатації, 2 в ремонті, 2 на огляді
        ('KB7788GH', 'Fiat', 'Doblo 1.4 Natural Power', 2019, 'ZFA26300006678901', 9.5, 120, 87000, 'gas', 'active'),
        ('KB9900IK', 'Volkswagen', 'Caddy 1.4 TGI', 2020, 'WV1ZZZSKZLX789012', 9.0, 130, 64000, 'gas', 'repair'),
        ('KB2233LM', 'Iveco', 'Eurocargo 120E CNG', 2019, 'ZCFA1ED0102890123', 22.0, 400, 141000, 'gas', 'repair'),
        ('KB4455NO', 'Mercedes-Benz', 'Econic 1830 NGT', 2018, 'WDB9570311L901234', 33.0, 600, 176000, 'gas', 'inspection'),
        ('KB6677PR', 'Opel', 'Combo 1.4 CNG', 2017, 'W0L0XCF0612012345', 9.8, 110, 158000, 'gas', 'inspection'),
        # Списані (по одному на кожен тип пального)
        ('KC1100AA', 'MAN', 'TGA 18.430', 2008, 'WMAH05ZZZ8M123456', 34.0, 400, 812000, 'diesel', 'decommissioned'),
        ('KC2200BB', 'Iveco', 'Daily 35C14 CNG', 2010, 'ZCFC35A1005234567', 16.0, 180, 503000, 'gas', 'decommissioned'),
        ('KC3300CC', 'Ford', 'Transit 2.3', 2009, 'WF0XXXTTFX9345678', 14.5, 80, 467000, 'petrol', 'decommissioned'),
    ]

    vehicles = []
    statuses = ['active', 'active', 'active', 'active', 'active', 'active',
                'active', 'active', 'repair', 'active', 'inspection', 'active',
                'active', 'active', 'active', 'active', 'active', 'active']

    for i, (plate, brand, model, year, vin, norm, tank, odo, *rest) in enumerate(vehicles_data):
        fuel_type = rest[0] if rest else 'diesel'
        status = rest[1] if len(rest) > 1 else statuses[i]
        last_maint = random.randint(5000, 10000)
        vehicles.append({
            'plate_number': plate,
            'brand': brand,
            'model': model,
            'year': year,
            'vin': vin,
            'status': status,
            'fuel_type': fuel_type,
            'fuel_norm': norm,
            'tank_capacity': tank,
            'odometer': odo,
            'last_maintenance_km': odo - last_maint,
            'last_maintenance_date': day_start(datetime.utcnow() - timedelta(days=random.randint(20, 90))),
            'next_maintenance_km': odo + (10000 - last_maint),
            'next_maintenance_date': day_start(datetime.utcnow() + timedelta(days=random.randint(10, 90))),
            'inspection_expiry': day_start(datetime.utcnow() + timedelta(days=random.randint(30, 400))),
            'insurance_policy': f'СТР-{str(i+1).zfill(3)}-2024',
            'insurance_expiry': day_start(datetime.utcnow() + timedelta(days=random.randint(100, 400))),
            'created_at': datetime.utcnow() - timedelta(days=random.randint(100, 365)),
            'updated_at': datetime.utcnow()
        })

    result = db.vehicles.insert_many(vehicles)
    vehicle_ids = {vehicles[i]['plate_number']: str(result.inserted_ids[i]) for i in range(len(vehicles))}
    plate_numbers = list(vehicle_ids.keys())
    active_plates = [v['plate_number'] for v in vehicles if v['status'] == 'active']
    vehicle_fuel = {v['plate_number']: v['fuel_type'] for v in vehicles}
    print(f'Створено {len(vehicles)} транспортних засобів.')

    # === Путівки (90 завершених за 60 днів + 3 активні) ===
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

    # Достатньо путівок, щоб середній добовий пробіг (прогноз ТО) був реалістичним.
    # Активні путівки - на різних авто; одна з них у демо-водія driver_ivanov.
    plan = [(random.randint(1, 60), None) for _ in range(90)] + [(0, 'driver_ivanov'), (0, None), (0, None)]
    busy_plates = set()
    for days_ago, fixed_driver in plan:
        route = random.choice(routes)
        if days_ago == 0:
            plate = random.choice([p for p in active_plates if p not in busy_plates])
            busy_plates.add(plate)
        else:
            plate = random.choice(active_plates)  # Тільки активні авто
        driver = fixed_driver or random.choice(driver_usernames)
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
            'issue_date': day_start(datetime.utcnow() - timedelta(days=days_ago)),
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
            # Категорії шин, охолодження і паливної системи зводимо до довідника системи
            'category': {'tires': 'suspension', 'cooling': 'engine', 'fuel_system': 'engine'}.get(category, category),
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

    for i in range(30):
        days_ago = random.randint(0, 170)  # близько півроку історії для графіків витрат
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
            'scheduled_date': day_start(datetime.utcnow() - timedelta(days=days_ago)),
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

    # Заплановані на найближчі тижні роботи (для календаря ТО)
    for days_ahead in (2, 5, 9, 13, 18, 24):
        plate = random.choice(active_plates)
        repair_type = random.choice(['maintenance', 'maintenance', 'repair', 'inspection'])
        desc = 'Планове ТО-1' if repair_type == 'maintenance' else random.choice(repair_descriptions)
        repairs.append({
            'number': f'РМ-{repair_num}',
            'vehicle_id': vehicle_ids[plate],
            'mechanic_id': user_ids[random.choice(mechanic_usernames)],
            'fault_id': None,
            'repair_type': repair_type,
            'description': desc,
            'scheduled_date': day_start(datetime.utcnow() + timedelta(days=days_ahead)),
            'started_at': None,
            'completed_at': None,
            'odometer': random.randint(50000, 200000),
            'status': 'planned',
            'work_performed': None,
            'parts_used': [],
            'labor_hours': None,
            'labor_cost': None,
            'parts_cost': None,
            'notes': None,
            'created_by': user_ids['admin'],
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        })
        repair_num += 1

    # Поточні роботи для авто, які зараз у ремонті або на огляді (узгоджено зі статусом авто)
    current_work = {
        'repair': ['Ремонт паливної системи', 'Заміна зчеплення', 'Ремонт КПП', 'Ремонт пневмосистеми'],
        'inspection': ['Технічний огляд', 'Діагностика ходової частини', 'Перевірка гальмівної системи'],
    }
    for v in vehicles:
        if v['status'] not in current_work:
            continue
        days_ago = random.randint(1, 4)
        repairs.append({
            'number': f'РМ-{repair_num}',
            'vehicle_id': vehicle_ids[v['plate_number']],
            'mechanic_id': user_ids[random.choice(mechanic_usernames)],
            'fault_id': None,
            'repair_type': 'repair' if v['status'] == 'repair' else 'inspection',
            'description': random.choice(current_work[v['status']]),
            'scheduled_date': day_start(datetime.utcnow() - timedelta(days=days_ago)),
            'started_at': datetime.utcnow() - timedelta(days=days_ago),
            'completed_at': None,
            'odometer': v['odometer'],
            'status': 'in_progress',
            'work_performed': None,
            'parts_used': [],
            'labor_hours': None,
            'labor_cost': None,
            'parts_cost': None,
            'notes': None,
            'created_by': user_ids['admin'],
            'created_at': datetime.utcnow() - timedelta(days=days_ago),
            'updated_at': datetime.utcnow() - timedelta(days=days_ago)
        })
        repair_num += 1

    db.repairs.insert_many(repairs)
    print(f'Створено {len(repairs)} ремонтів.')

    # === Паливні накладні (24 штуки, близько півроку) ===
    suppliers = ['ОККО', 'WOG', 'Shell', 'БРСМ-Нафта', 'Авіас']
    invoices = []
    invoice_num = 400001

    for i in range(24):
        days_ago = i * 7 + random.randint(0, 3)
        supplier = random.choice(suppliers)
        quantity = random.randint(1500, 5000)
        price = round(random.uniform(48.0, 56.0), 2)
        distributed = int(quantity * random.uniform(0.3, 0.9)) if days_ago > 5 else 0

        invoices.append({
            'number': f'НП-{invoice_num}',
            'date': day_start(datetime.utcnow() - timedelta(days=days_ago)),
            'supplier': supplier,
            'fuel_type': random.choice(['diesel', 'diesel', 'diesel', 'petrol', 'gas']),
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
        plate = random.choice(active_plates)
        driver = random.choice(driver_usernames)
        quantity = random.randint(100, 400)
        # Частина записів - зовнішні заправки на АЗС з ціною і сумою, решта - видача з накладної
        is_external = random.random() < 0.35
        price = round(random.uniform(50.0, 58.0), 2) if is_external else None

        fuel_records.append({
            'vehicle_id': vehicle_ids[plate],
            'driver_id': user_ids[driver],
            'date': day_start(datetime.utcnow() - timedelta(days=days_ago)),
            'fuel_type': vehicle_fuel[plate],
            'quantity': quantity,
            'odometer': random.randint(50000, 200000),
            'record_type': 'external' if is_external else 'issue',
            'station': random.choice(suppliers) if is_external else None,
            'price_per_liter': price,
            'total_amount': round(quantity * price, 2) if is_external else None,
            'notes': None,
            'created_by': user_ids['admin'],
            'created_at': datetime.utcnow() - timedelta(days=days_ago),
            'updated_at': datetime.utcnow() - timedelta(days=days_ago)
        })

    db.fuel_records.insert_many(fuel_records)
    print(f'Створено {len(fuel_records)} записів про видачу пального.')

    # === Сповіщення ===
    # Формат збігається з тим, що створює сама система (recipient_role / recipient_id, is_dismissed),
    # інакше сповіщення не відображаються на сторінках.
    now = datetime.utcnow()
    plate_by_id = {vid: plate for plate, vid in vehicle_ids.items()}
    severity_labels = {'low': 'низька', 'medium': 'середня', 'high': 'висока', 'critical': 'критична'}

    def make_alert(alert_type, category, title, message, role=None, recipient=None,
                   related_type=None, related_id=None, hours_ago=1, read=False):
        created = now - timedelta(hours=hours_ago)
        return {
            'alert_type': alert_type,
            'category': category,
            'title': title,
            'message': message,
            'recipient_id': recipient,
            'recipient_role': role,
            'related_type': related_type,
            'related_id': related_id,
            'is_read': read,
            'read_at': created + timedelta(minutes=30) if read else None,
            'is_dismissed': False,
            'dismissed_at': None,
            'created_at': created,
        }

    alerts = []
    for fault in faults:
        fid = str(fault['_id'])
        plate = plate_by_id.get(fault['vehicle_id'], '—')
        hours = max(1, int((now - fault['report_date']).total_seconds() // 3600))
        sev = fault['severity']
        alert_type = 'critical' if sev == 'critical' else 'warning' if sev == 'high' else 'info'
        is_open = fault['status'] in ('new', 'acknowledged')
        # Сповіщення механікам про кожну несправність
        alerts.append(make_alert(alert_type, 'fault', f'Нова несправність: {plate}',
                                 f'Серйозність: {severity_labels[sev]}. {fault["description"]}',
                                 role='mechanic', related_type='fault', related_id=fid,
                                 hours_ago=hours, read=not is_open))
        # Критичні відкриті несправності - також керівнику
        if sev == 'critical' and is_open:
            alerts.append(make_alert('critical', 'fault', f'Критична несправність: {plate}',
                                     f'{fault["number"]}: {fault["description"]}. Потрібне термінове рішення.',
                                     role='manager', related_type='fault', related_id=fid, hours_ago=hours))
        # Ескалація нових несправностей без відповіді
        if fault['status'] == 'new' and hours >= 4:
            alerts.append(make_alert('warning', 'escalation', f'Несправність без відповіді: {plate}',
                                     f'Несправність {fault["number"]} чекає на відповідь понад 4 години.',
                                     role='mechanic', related_type='fault', related_id=fid, hours_ago=hours - 4))
        if fault['status'] == 'new' and hours >= 24:
            alerts.append(make_alert('critical', 'escalation', 'УВАГА: Несправність без відповіді 24+ год',
                                     f'Несправність {fault["number"]} ({plate}) не має відповіді понад 24 години!',
                                     role='manager', related_type='fault', related_id=fid, hours_ago=hours - 24))

    # Перевитрата пального за завершеними путівками - керівнику
    for wb in [w for w in waybills if w['status'] == 'completed' and w.get('fuel_used')][:6]:
        distance = wb['odometer_end'] - wb['odometer_start']
        vehicle = next(v for v in vehicles if vehicle_ids[v['plate_number']] == wb['vehicle_id'])
        actual = wb['fuel_used'] / distance * 100
        deviation = (actual - vehicle['fuel_norm']) / vehicle['fuel_norm'] * 100
        if deviation > 10:
            alerts.append(make_alert('warning', 'fuel', f'Перевитрата пального: {vehicle["plate_number"]}',
                                     f'Путівка {wb["number"]}: {actual:.1f} л/100 км при нормі '
                                     f'{vehicle["fuel_norm"]} л/100 км (+{deviation:.1f}%).',
                                     role='manager', related_type='waybill',
                                     hours_ago=random.randint(5, 120), read=random.random() > 0.5))

    # Документи, термін дії яких спливає (страховка, техогляд) - керівнику
    for v in vehicles:
        if v['status'] == 'decommissioned':
            continue
        for field, label in (('insurance_expiry', 'страховий поліс'), ('inspection_expiry', 'техогляд')):
            days_left = (v[field] - day_start(now)).days
            if days_left <= 45:
                alerts.append(make_alert('warning', 'general', f'Закінчується {label}: {v["plate_number"]}',
                                         f'Термін дії спливає через {days_left} дн.',
                                         role='manager', related_type='vehicle',
                                         related_id=vehicle_ids[v['plate_number']], hours_ago=random.randint(2, 48)))

    if alerts:
        db.alerts.insert_many(alerts)
    # Сповіщення про ТО формує сама система - запускаємо ту саму перевірку, що й планувальник
    from services.alert_engine import check_maintenance_alerts
    check_maintenance_alerts(db)
    print(f'Створено {db.alerts.count_documents({})} сповіщень.')

    # === Склад запчастин ===
    from services.inventory import check_low_stock
    parts_data = [
        # назва, артикул, категорія, од., залишок, мінімум, ціна
        ('Колодки гальмівні передні', 'BP-1021', 'brakes', 'компл.', 2, 4, 3200),
        ('Колодки гальмівні задні', 'BP-1022', 'brakes', 'компл.', 6, 3, 2900),
        ('Диск гальмівний', 'BD-330', 'brakes', 'шт', 4, 2, 5400),
        ('Фільтр масляний', 'OF-210', 'filters', 'шт', 18, 6, 480),
        ('Фільтр паливний', 'FF-118', 'filters', 'шт', 3, 5, 950),
        ('Фільтр повітряний', 'AF-402', 'filters', 'шт', 9, 4, 1350),
        ('Олива моторна 10W-40', 'OIL-1040', 'oils', 'л', 120, 40, 210),
        ('Антифриз G12', 'CL-G12', 'oils', 'л', 35, 20, 120),
        ('Рідина гальмівна DOT-4', 'BF-DOT4', 'oils', 'л', 8, 5, 260),
        ('Ремінь ГРМ', 'TB-77', 'engine', 'шт', 2, 2, 2600),
        ('Свічка запалювання', 'SP-14', 'engine', 'шт', 24, 8, 220),
        ('Акумулятор 12В 190Аг', 'BAT-190', 'electrical', 'шт', 3, 2, 7800),
        ('Лампа H7 24В', 'LMP-H7', 'electrical', 'шт', 20, 10, 150),
        ('Амортизатор', 'SH-552', 'suspension', 'шт', 4, 2, 4300),
        ('Шина 315/80 R22.5', 'TYR-315', 'tyres', 'шт', 6, 4, 16500),
        ('Щітка склоочисника', 'WB-600', 'other', 'шт', 10, 6, 320),
    ]
    db.parts.delete_many({})
    db.part_movements.delete_many({})
    parts = [{
        'name': n, 'article': a, 'category': c, 'unit': u, 'quantity': q, 'min_quantity': mq, 'price': pr,
        'created_at': now - timedelta(days=120), 'updated_at': now,
    } for n, a, c, u, q, mq, pr in parts_data]
    db.parts.insert_many(parts)
    # Історія руху: початкове надходження і списання в кількох завершених ремонтах
    movements = [{'part_id': str(p['_id']), 'type': 'in', 'quantity': p['quantity'] + random.randint(2, 10),
                  'price': p['price'], 'note': 'Початковий залишок', 'user_id': user_ids['admin'],
                  'created_at': now - timedelta(days=120)} for p in parts]
    for r in [r for r in db.repairs.find({'status': 'completed'})][:8]:
        part = random.choice(parts)
        qty = 1 if part['unit'] != 'л' else random.randint(4, 12)
        used = {'part_id': str(part['_id']), 'name': part['name'], 'unit': part['unit'], 'quantity': qty,
                'price': part['price'], 'cost': qty * part['price']}
        db.repairs.update_one({'_id': r['_id']}, {'$set': {'parts_used': [used]}})
        movements.append({'part_id': str(part['_id']), 'type': 'out', 'quantity': qty, 'price': part['price'],
                          'repair_id': str(r['_id']), 'user_id': r.get('mechanic_id'),
                          'created_at': r.get('completed_at') or now})
    db.part_movements.insert_many(movements)
    for p in parts:
        check_low_stock(db, p)
    print(f'Створено {len(parts)} позицій складу запчастин.')

    # === Налаштування ===
    settings = {
        '_id': 'system',
        'default_fuel_norm': 25.0,
        'overspend_threshold': 10,
        'winter_coefficient': 1.09,
        'maintenance_warning_km': 1000,
        'maintenance_warning_days': 14,
        'maintenance_interval_km': 10000,
        'maintenance_interval_days': 180,
        'fault_mechanic_hours': 4,
        'fault_manager_hours': 24,
        'company_name': 'KRUTII TRANS',
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow()
    }

    db.settings.insert_one(settings)
    print('Створено налаштування системи.')

    # =============================================
    # ЖУРНАЛ ДІЙ (демонстраційна історія за 14 днів)
    # =============================================
    seed_audit_log(db, users, vehicles, waybills, faults, repairs, parts)
    print(f'Створено {db.audit_log.count_documents({})} записів журналу дій.')

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
    print(f'  Сповіщення: {db.alerts.count_documents({})}')
    print('\nОблікові записи для входу:')
    print('  Керівник: admin / Admin1234')
    print('  Механік:  mech_koval / Mech1234')
    print('  Водій:    driver_ivanov / Driver1234')


def seed_audit_log(db, users, vehicles, waybills, faults, repairs, parts):
    """Реалістична історія дій: входи (зокрема невдалі), видача путівок, ремонти, зміни довідників."""
    rnd = random.Random(42)
    now = datetime.utcnow()
    by_name = {u['username']: u for u in users}
    office_ip = ['192.168.1.10', '192.168.1.14', '192.168.1.21']
    agents = {'manager': 'Chrome · Windows', 'mechanic': 'Edge · Windows', 'driver': 'Chrome · Android'}
    entries = []

    def add(days_ago, hour, minute, username, category, action, endpoint, method='PUT', entity=None,
            changes=None, status='success', error=None, ip=None, agent=None):
        u = by_name.get(username, {})
        ts = day_start(now - timedelta(days=days_ago)) + timedelta(hours=hour, minutes=minute, seconds=rnd.randint(0, 59))
        if ts > now:
            return
        etype, eid, label = entity or (None, None, None)
        entries.append({
            'ts': ts, 'user_id': str(u['_id']) if u.get('_id') else None, 'username': username,
            'full_name': u.get('full_name'), 'role': u.get('role'), 'category': category, 'action': action,
            'endpoint': endpoint, 'method': method, 'entity_type': etype or category, 'entity_id': eid,
            'entity_label': label, 'changes': changes or [], 'status': status,
            'http_status': 200 if status == 'success' else 401, 'error': error,
            'ip': ip or (rnd.choice(office_ip) if u.get('role') != 'driver' else f'46.211.{rnd.randint(2, 250)}.{rnd.randint(2, 250)}'),
            'agent': agent or agents.get(u.get('role'), 'Chrome · Windows'),
        })

    def ent(kind, doc):
        if kind == 'vehicle':
            return ('vehicle', str(doc['_id']), f"{doc['plate_number']} {doc['brand']} {doc['model']}")
        return (kind, str(doc['_id']), doc.get('number') or doc.get('name') or doc.get('full_name'))

    drivers = [u['username'] for u in users if u['role'] == 'driver']
    mechanics = [u['username'] for u in users if u['role'] == 'mechanic']
    for d in range(14, -1, -1):
        if (now - timedelta(days=d)).weekday() >= 5:
            continue
        add(d, 6, rnd.randint(0, 20), 'admin', 'login', 'Вхід у систему', 'auth.login', 'POST')
        for m in mechanics:
            add(d, 6, rnd.randint(20, 50), m, 'login', 'Вхід у систему', 'auth.login', 'POST')
        for drv in rnd.sample(drivers, 4):
            add(d, 5, rnd.randint(0, 59), drv, 'login', 'Вхід у систему', 'auth.login', 'POST')
        wb = rnd.choice(waybills)
        add(d, 7, rnd.randint(0, 50), 'admin', 'waybill', 'Видача путівки', 'waybills.create_waybill', 'POST', ent('waybill', wb))
        add(d, 15, rnd.randint(0, 50), 'admin', 'logout', 'Вихід із системи', 'auth.logout', 'POST')

    # ремонти: механіки змінюють статуси
    for i, rep in enumerate(rnd.sample(repairs, min(10, len(repairs)))):
        d = rnd.randint(0, 13)
        mech = rnd.choice(mechanics)
        add(d, 8, rnd.randint(0, 59), mech, 'repair', 'Зміна ремонту / ТО', 'repairs.update_repair', 'PUT', ent('repair', rep),
            [{'field': 'status', 'old': 'planned', 'new': 'in_progress'}])
        add(d, 12 + i % 4, rnd.randint(0, 59), mech, 'repair', 'Зміна ремонту / ТО', 'repairs.update_repair', 'PUT', ent('repair', rep),
            [{'field': 'status', 'old': 'in_progress', 'new': 'completed'},
             {'field': 'labor_hours', 'old': '—', 'new': str(rnd.choice([1.5, 2, 3, 4.5]))}])
    # несправності: водії повідомляють, механіки приймають
    for f in rnd.sample(faults, min(8, len(faults))):
        d = rnd.randint(0, 13)
        add(d, 9, rnd.randint(0, 59), rnd.choice(drivers), 'fault', 'Повідомлення про несправність', 'faults.create_fault', 'POST', ent('fault', f))
        add(d, 10, rnd.randint(0, 59), rnd.choice(mechanics), 'fault', 'Обробка несправності', 'faults.update_fault', 'PUT', ent('fault', f),
            [{'field': 'status', 'old': 'new', 'new': 'acknowledged'}])
    # керівник змінює довідники
    v1, v2 = vehicles[2], vehicles[8]
    add(11, 9, 12, 'admin', 'vehicle', 'Зміна автомобіля', 'vehicles.update_vehicle', 'PUT', ent('vehicle', v1),
        [{'field': 'status', 'old': 'active', 'new': 'repair'}])
    add(6, 10, 3, 'admin', 'vehicle', 'Зміна автомобіля', 'vehicles.update_vehicle', 'PUT', ent('vehicle', v2),
        [{'field': 'fuel_norm', 'old': '26.0', 'new': '27.5'}, {'field': 'insurance_policy', 'old': 'АР-1042233', 'new': 'АР-2210457'}])
    add(9, 11, 40, 'admin', 'settings', 'Зміна налаштувань системи', 'settings.update_settings', 'PUT',
        ('settings', None, 'Налаштування системи'), [{'field': 'maintenance_warning_km', 'old': '800', 'new': '1000'}])
    drv = by_name[drivers[3]]
    add(5, 14, 25, 'admin', 'user', 'Зміна користувача', 'users.update_user', 'PUT',
        ('user', str(drv['_id']), f"{drv['full_name']} ({drv['username']})"),
        [{'field': 'phone', 'old': '+380671112233', 'new': drv.get('phone') or '+380501230000'}])
    add(4, 16, 5, 'admin', 'security', 'Скидання пароля користувача', 'users.reset_password', 'POST',
        ('user', str(drv['_id']), f"{drv['full_name']} ({drv['username']})"), [{'field': 'password', 'old': '•••', 'new': 'змінено'}])
    for p in rnd.sample(parts, 4):
        add(rnd.randint(0, 12), 13, rnd.randint(0, 59), rnd.choice(mechanics), 'part', 'Надходження запчастин', 'parts.receive', 'POST',
            ('part', str(p['_id']), p['name']), [{'field': 'quantity', 'old': str(p.get('quantity', 0)), 'new': str(p.get('quantity', 0) + 10)}])

    # невдалі входи: водій помилився з паролем, і підозріла серія спроб на обліковий запис керівника
    add(3, 5, 41, 'driver_bondar', 'login', 'Вхід у систему', 'auth.login', 'POST', status='fail', error='Невірний логін або пароль.')
    add(3, 5, 42, 'driver_bondar', 'login', 'Вхід у систему', 'auth.login', 'POST')
    for k in range(5):
        add(2, 23, 10 + k, 'admin', 'login', 'Вхід у систему', 'auth.login', 'POST', status='fail',
            error='Невірний логін або пароль.', ip='185.220.101.47', agent='Firefox · Linux')
    if entries:
        db.audit_log.insert_many(entries)
    # відповідне сповіщення безпеки керівнику
    db.alerts.insert_one({
        'alert_type': 'critical', 'category': 'security', 'title': 'Підозріла активність: вхід «admin»',
        'message': '5 невдалих спроб входу для облікового запису «admin» за 15 хв. Остання спроба з адреси 185.220.101.47.',
        'recipient_id': None, 'recipient_role': 'manager', 'related_type': 'audit', 'related_id': 'admin',
        'is_read': False, 'read_at': None, 'is_dismissed': False, 'dismissed_at': None,
        'created_at': day_start(now - timedelta(days=2)) + timedelta(hours=23, minutes=14),
    })


if __name__ == '__main__':
    seed_database()
