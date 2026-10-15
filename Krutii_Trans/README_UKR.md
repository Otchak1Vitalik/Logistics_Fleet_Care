# KRUTII TRANS

Система технічного обслуговування автопарку логістичної компанії.

## Технології

- **Backend:** Flask, PyMongo, JWT, APScheduler, Marshmallow
- **Frontend:** React 18, Zustand, Recharts, Vite, React Router
- **Database:** MongoDB
- **UI:** Власна дизайн-система з glassmorphism ефектами

## Можливості

### Керівник (Manager)
- Повне управління користувачами та автопарком
- Створення та контроль путівок
- Паливні накладні та аналітика витрат
- Звіти по витратах, ТО, ефективності
- Налаштування системи (норми пального, категорії)

### Механік (Mechanic)
- Обробка несправностей від водіїв
- Планування та виконання ремонтів
- Контроль графіку технічного обслуговування
- Миттєві сповіщення про нові несправності

### Водій (Driver)
- Перегляд активних путівок
- Звіти про несправності з фото
- Облік заправок на маршруті
- Завершення путівок з фіксацією пробігу

## Встановлення

### Вимоги
- Python 3.9+
- Node.js 18+
- MongoDB 6+

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
python seed.py  # Ініціалізація демо-даних
flask run
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Додаток буде доступний на http://localhost:5173

## Демо-акаунти

| Роль | Логін | Пароль |
|------|-------|--------|
| Керівник | admin | Admin1234 |
| Механік | mech_koval | Mech1234 |
| Водій | driver_ivanov | Driver1234 |

## Структура проекту

```
/backend
  app.py              # Flask entry point
  config.py           # Конфігурація (MongoDB, JWT, rate limits)
  seed.py             # Демо-дані
  /routes             # API endpoints
    auth.py           # Авторизація
    users.py          # Користувачі
    vehicles.py       # Автопарк
    waybills.py       # Путівки
    faults.py         # Несправності
    repairs.py        # Ремонти
    fuel.py           # Паливо
    alerts.py         # Сповіщення
    reports.py        # Звіти
    settings.py       # Налаштування
  /models             # Marshmallow schemas
  /services
    fuel_analyzer.py  # Аналіз перевитрат пального
    alert_engine.py   # Система сповіщень та ескалації
    doc_generator.py  # Генерація номерів документів
  /middleware
    auth_middleware.py # JWT авторизація та ролі

/frontend/src
  /api                # Axios клієнти з interceptors
  /store              # Zustand stores (auth, alerts, vehicles)
  /layouts            # Layouts по ролям
  /pages
    /driver           # Сторінки водія
    /mechanic         # Сторінки механіка
    /manager          # Сторінки керівника
  /components         # UI компоненти (DataTable, StatusBadge, AlertBell)
  /utils              # Форматери, калькулятори
  /styles             # CSS з дизайн-системою
```

## Ключові особливості

### Аутентифікація
- JWT токени в httpOnly cookies
- Автоматичний refresh при закінченні сесії
- Rate limiting на логін (10 req/min)

### Формула витрат пального
```
fuel_recommended = (distance_km / 100) * fuel_norm * season_coefficient
season_coefficient = 1.0 (літо) | 1.09 (зима: листопад-березень)
```

### Система сповіщень
- Ескалація несправностей: 4 години - механіку, 24 години - керівнику
- Попередження про ТО: за 1000 км або 14 днів
- Push-сповіщення в реальному часі

### Нумерація документів
- ПЛ-XXXXXX - путівки
- НС-XXXXXX - несправності
- РМ-XXXXXX - ремонти
- НП-XXXXXX - паливні накладні

## API Endpoints

### Авторизація
- `POST /api/auth/login` - Вхід
- `POST /api/auth/logout` - Вихід
- `GET /api/auth/me` - Поточний користувач

### Ресурси
- `GET/POST /api/users` - Користувачі
- `GET/POST /api/vehicles` - Автопарк
- `GET/POST /api/waybills` - Путівки
- `GET/POST /api/faults` - Несправності
- `GET/POST /api/repairs` - Ремонти
- `GET/POST /api/fuel/invoices` - Паливні накладні
- `GET /api/alerts` - Сповіщення

### Звіти
- `GET /api/reports/fuel` - Звіт по пальному
- `GET /api/reports/maintenance` - Графік ТО
- `GET /api/reports/efficiency` - Ефективність водіїв

## Статуси

| Сутність | Статуси |
|----------|---------|
| Путівки | issued -> active -> completed / cancelled |
| Ремонти | planned -> in_progress -> completed / cancelled |
| Несправності | new -> acknowledged -> in_repair -> resolved / rejected |
| Транспорт | active / repair / inspection / decommissioned |

