# KRUTII TRANS

Fleet maintenance management system for a logistics company.

## Technologies

- **Backend:** Flask, PyMongo, JWT, APScheduler, Marshmallow
- **Frontend:** React 18, Zustand, Recharts, Vite, React Router
- **Database:** MongoDB
- **UI:** Custom design system with glassmorphism effects

## Features

### Manager
- Complete user and fleet management
- Creation and control of waybills
- Fuel invoices and expense analytics
- Reports on expenses, maintenance (ТО), and efficiency
- System settings (fuel norms, categories)

### Mechanic
- Handling fault reports from drivers
- Planning and performing repairs
- Maintenance schedule control
- Instant notifications about new faults

### Driver
- Viewing active waybills
- Fault reports with photos
- Tracking refuelings along the route
- Completing waybills with mileage tracking

## Installation

### Prerequisites
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
python seed.py  # Initialize demo data
flask run
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The application will be available at http://localhost:5173

## Demo Accounts

| Role    | Login         | Password  |
|---------|---------------|-----------|
| Manager | admin         | Admin1234 |
| Mechanic| mech_koval    | Mech1234  |
| Driver  | driver_ivanov | Driver1234|

## Project Structure

```
/backend
  app.py              # Flask entry point
  config.py           # Configuration (MongoDB, JWT, rate limits)
  seed.py             # Demo data
  /routes             # API endpoints
    auth.py           # Authentication
    users.py          # Users
    vehicles.py       # Fleet
    waybills.py       # Waybills
    faults.py         # Faults
    repairs.py        # Repairs
    fuel.py           # Fuel
    alerts.py         # Alerts
    reports.py        # Reports
    settings.py       # Settings
  /models             # Marshmallow schemas
  /services
    fuel_analyzer.py  # Fuel overconsumption analysis
    alert_engine.py   # Alert and escalation system
    doc_generator.py  # Document numbering generation
  /middleware
    auth_middleware.py # JWT authorization and roles

/frontend/src
  /api                # Axios clients with interceptors
  /store              # Zustand stores (auth, alerts, vehicles)
  /layouts            # Role-based layouts
  /pages
    /driver           # Driver pages
    /mechanic         # Mechanic pages
    /manager          # Manager pages
  /components         # UI components (DataTable, StatusBadge, AlertBell)
  /utils              # Formatters, calculators
  /styles             # CSS with design system
```

## Key Features

### Authentication
- JWT tokens in httpOnly cookies
- Automatic refresh on session expiration
- Rate limiting on login (10 req/min)

### Fuel Consumption Formula
```
fuel_recommended = (distance_km / 100) * fuel_norm * season_coefficient
season_coefficient = 1.0 (summer) | 1.09 (winter: November–March)
```

### Alert System
- Fault escalation: 4 hours to mechanic, 24 hours to manager
- Maintenance warnings: 1,000 km or 14 days prior
- Real-time push notifications

### Document Numbering
- ПЛ-XXXXXX - Waybills
- НС-XXXXXX - Faults
- РМ-XXXXXX - Repairs
- НП-XXXXXX - Fuel invoices

## API Endpoints

### Authentication
- `POST /api/auth/login` - Login
- `POST /api/auth/logout` - Logout
- `GET /api/auth/me` - Current user

### Resources
- `GET/POST /api/users` - Users
- `GET/POST /api/vehicles` - Fleet
- `GET/POST /api/waybills` - Waybills
- `GET/POST /api/faults` - Faults
- `GET/POST /api/repairs` - Repairs
- `GET/POST /api/fuel/invoices` - Fuel invoices
- `GET /api/alerts` - Alerts

### Reports
- `GET /api/reports/fuel` - Fuel report
- `GET /api/reports/maintenance` - Maintenance schedule
- `GET /api/reports/efficiency` - Driver efficiency

## Statuses

| Entity  | Statuses                                                |
|---------|---------------------------------------------------------|
| Waybills| issued -> active -> completed / cancelled               |
| Repairs | planned -> in_progress -> completed / cancelled         |
| Faults  | new -> acknowledged -> in_repair -> resolved / rejected |
| Vehicles| active / repair / inspection / decommissioned           |
