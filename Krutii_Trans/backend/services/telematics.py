"""
Телематика: прийом даних від GPS-трекерів автомобілів і правила реагування.

Трекер (або симулятор simulator.py) кожні кілька секунд надсилає на POST /api/telematics/ingest
пакет точок: координати, швидкість, одометр, рівень пального, температуру двигуна, напругу бортової
мережі, оберти, стан запалювання й коди помилок OBD. Пристрій автентифікується ключем
(у базі зберігається лише його SHA-256).

Сирі точки зберігаються в колекції telemetry (автоматично видаляються через 90 днів),
останній стан кожного авто - у telematics_state, події - у telematics_events.
Правила (на кожну точку, з урахуванням попереднього стану):
  - перегрів двигуна        - температура >= 105 °C;
  - низька напруга          - < 23.0 В (24-вольтова мережа вантажівок) / < 11.6 В (12 В);
  - новий код помилки OBD;
  - злив пального           - рівень у баку різко впав, а машина стоїть (потрапляє в «Аномалії пального»);
  - заправка                - рівень зріс на стоянці (подія без сповіщення);
  - рух без путівки         - автомобіль їде, а активної путівки немає.
Сповіщення одного типу для одного авто - не частіше ніж раз на 2 години.
"""
import hashlib
import secrets
from datetime import datetime, timedelta

from bson import ObjectId

RETENTION_DAYS = 90
OFFLINE_SECONDS = 300
OVERHEAT_C = 105.0
BATTERY_MIN = {True: 23.0, False: 11.6}          # вантажівка (24 В) / легковий (12 В)
DRAIN_MIN_SHARE, DRAIN_MIN_L = 0.08, 15.0
REFUEL_MIN_L = 20.0
STOPPED_KMH = 3.0
COOLDOWN = timedelta(hours=2)
MAX_POINTS = 500

DTC = {
    'P0217': 'Перегрів двигуна (датчик температури ОР)',
    'P0300': 'Пропуски запалювання в циліндрах',
    'P0087': 'Низький тиск палива в рампі',
    'P0401': 'Недостатня рециркуляція відпрацьованих газів (EGR)',
    'P2463': 'Надмірне накопичення сажі в сажовому фільтрі (DPF)',
    'P0562': 'Низька напруга бортової мережі',
    'P0128': 'Двигун не прогрівається до робочої температури (термостат)',
    'U0100': 'Втрата зв’язку з блоком керування двигуном',
}
EVENT_LABELS = {
    'overheat': 'Перегрів двигуна', 'low_battery': 'Низька напруга', 'dtc': 'Код помилки',
    'fuel_drain': 'Злив пального', 'refuel': 'Заправка', 'no_waybill': 'Рух без путівки',
}
TECH_EVENTS = {'overheat', 'low_battery', 'dtc'}
FIELDS = {  # поле: (мін, макс)
    'lat': (44.0, 53.0), 'lon': (21.0, 41.0), 'speed': (0, 200), 'odometer': (0, 5_000_000),
    'fuel_level': (0, 2000), 'engine_temp': (-40, 150), 'battery_v': (0, 40), 'rpm': (0, 8000),
}


# --------------------------------------------------------------------------- пристрої
def _hash(key):
    return hashlib.sha256(key.encode()).hexdigest()


def provision(db, vehicle_id):
    """Новий ключ трекера для автомобіля (показується один раз, у базі - лише хеш)."""
    key = 'kt_' + secrets.token_urlsafe(24)
    db.vehicles.update_one({'_id': ObjectId(vehicle_id)}, {'$set': {
        'telematics': {'key_hash': _hash(key), 'key_hint': key[-4:], 'provisioned_at': datetime.utcnow()}}})
    return key


def vehicle_by_key(db, key):
    if not key or len(key) > 100:
        return None
    return db.vehicles.find_one({'telematics.key_hash': _hash(key)})


# --------------------------------------------------------------------------- прийом
def _parse_ts(value, now):
    if isinstance(value, (int, float)):
        ts = datetime.utcfromtimestamp(value / 1000 if value > 1e11 else value)
    elif isinstance(value, str):
        try:
            ts = datetime.fromisoformat(value.replace('Z', '+00:00')).replace(tzinfo=None)
        except ValueError:
            return None
    else:
        ts = now
    if ts > now + timedelta(minutes=5) or ts < now - timedelta(days=7):
        return None
    return ts


def clean_point(raw, now):
    """Перевіряє й нормалізує точку; None - якщо точка некоректна."""
    if not isinstance(raw, dict):
        return None
    ts = _parse_ts(raw.get('ts'), now)
    if ts is None:
        return None
    p = {'ts': ts}
    for k, (lo, hi) in FIELDS.items():
        v = raw.get(k)
        if v is None:
            continue
        try:
            v = float(v)
        except (TypeError, ValueError):
            return None
        if not lo <= v <= hi:
            return None
        p[k] = v
    if 'lat' not in p or 'lon' not in p:
        return None
    p['ignition'] = bool(raw.get('ignition', p.get('speed', 0) > 0))
    p['dtc'] = sorted({str(c).upper()[:8] for c in (raw.get('dtc') or []) if str(c).strip()})[:10]
    if raw.get('heading') is not None:
        try:
            p['heading'] = float(raw['heading']) % 360
        except (TypeError, ValueError):
            pass
    return p


def _label(v):
    return f"{v.get('plate_number')} {v.get('brand', '')} {v.get('model', '')}".strip()


def _fuel_price(db, fuel_type):
    from services.fuel_anomalies import _prices
    return _prices(db).get(fuel_type, 54.0)


def _active_waybill(db, vid):
    return db.waybills.find_one({'vehicle_id': vid, 'status': 'active'}, {'number': 1, 'driver_id': 1,
                                                                          'route_from': 1, 'route_to': 1})


def ingest(db, vehicle, raw_points):
    """Обробляє пакет точок від трекера. Повертає {'accepted', 'rejected', 'events'}."""
    now = datetime.utcnow()
    vid = str(vehicle['_id'])
    heavy = (vehicle.get('fuel_norm') or 0) >= 20
    tank = vehicle.get('tank_capacity') or (400 if heavy else 70)
    points = [p for p in (clean_point(r, now) for r in (raw_points or [])[:MAX_POINTS]) if p]
    rejected = min(len(raw_points or []), MAX_POINTS) - len(points)
    if not points:
        return {'accepted': 0, 'rejected': rejected, 'events': []}
    points.sort(key=lambda p: p['ts'])

    state = db.telematics_state.find_one({'_id': vid}) or {'_id': vid, 'flags': {}, 'last_alert': {}}
    flags, last_alert = state.get('flags') or {}, state.get('last_alert') or {}
    prev = state if state.get('ts') else None
    waybill = _active_waybill(db, vid) if any(p.get('speed', 0) > 10 for p in points) else None
    events = []

    def event(kind, p, message, value=None, code=None):
        events.append({'vehicle_id': vid, 'plate': vehicle.get('plate_number'), 'ts': p['ts'], 'type': kind,
                       'value': value, 'code': code, 'message': message, 'lat': p['lat'], 'lon': p['lon']})

    for p in points:
        if prev and prev.get('ts') and p['ts'] <= prev['ts']:
            continue                                            # дублікати / застарілі точки
        temp, volts, fuel, speed = p.get('engine_temp'), p.get('battery_v'), p.get('fuel_level'), p.get('speed', 0)
        if temp is not None:
            if temp >= OVERHEAT_C and not flags.get('overheat'):
                flags['overheat'] = True
                event('overheat', p, f'Температура двигуна {temp:.0f} °C (норма до {OVERHEAT_C:.0f} °C).', temp)
            elif temp < OVERHEAT_C - 8:
                flags['overheat'] = False
        if volts is not None:
            limit = BATTERY_MIN[heavy]
            if volts < limit and not flags.get('low_battery'):
                flags['low_battery'] = True
                event('low_battery', p, f'Напруга бортової мережі {volts:.1f} В (мінімум {limit:.1f} В).', volts)
            elif volts >= limit + 0.6:
                flags['low_battery'] = False
        for code in p['dtc']:
            if code not in (prev or {}).get('dtc', []):
                event('dtc', p, f"{code}: {DTC.get(code, 'невідомий код')}.", code=code)
        if prev and fuel is not None and prev.get('fuel_level') is not None \
                and (p['ts'] - prev['ts']) <= timedelta(minutes=30):
            delta = fuel - prev['fuel_level']
            stopped = speed <= STOPPED_KMH and prev.get('speed', 0) <= STOPPED_KMH
            if stopped and -delta >= max(DRAIN_MIN_L, DRAIN_MIN_SHARE * tank):
                event('fuel_drain', p, f"Рівень пального впав на {-delta:.0f} л за "
                                       f"{max(1, (p['ts'] - prev['ts']).seconds // 60)} хв на стоянці.", -delta)
            elif stopped and delta >= REFUEL_MIN_L:
                event('refuel', p, f'Заправка {delta:.0f} л.', delta)
        if speed > 10 and not waybill and not flags.get('no_waybill'):
            flags['no_waybill'] = True
            event('no_waybill', p, f'Автомобіль рухається зі швидкістю {speed:.0f} км/год без активної путівки.', speed)
        elif speed <= STOPPED_KMH and flags.get('no_waybill'):
            flags['no_waybill'] = False
        if prev and 'heading' not in p and speed > 3:
            from services.geo_ukraine import bearing
            if (prev['lat'], prev['lon']) != (p['lat'], p['lon']):
                p['heading'] = bearing((prev['lat'], prev['lon']), (p['lat'], p['lon']))
        if 'heading' not in p and prev and prev.get('heading') is not None:
            p['heading'] = prev['heading']
        prev = {**(prev or {}), **p}

    db.telemetry.insert_many([{'vehicle_id': vid, **p} for p in points])
    last = prev
    db.telematics_state.update_one({'_id': vid}, {'$set': {
        **{k: last.get(k) for k in ('ts', 'lat', 'lon', 'speed', 'odometer', 'fuel_level', 'engine_temp',
                                    'battery_v', 'rpm', 'ignition', 'dtc', 'heading')},
        'flags': flags, 'last_alert': last_alert, 'tank': tank}}, upsert=True)
    if last.get('odometer'):
        db.vehicles.update_one({'_id': vehicle['_id'], 'odometer': {'$lt': int(last['odometer'])}},
                               {'$set': {'odometer': int(last['odometer']), 'updated_at': now}})

    if events:
        res = db.telematics_events.insert_many(events)
        for e, eid in zip(events, res.inserted_ids):
            e['_id'] = eid
            _react(db, vehicle, e, last_alert, waybill)
        db.telematics_state.update_one({'_id': vid}, {'$set': {'last_alert': last_alert}})
    return {'accepted': len(points), 'rejected': rejected, 'events': [e['type'] for e in events]}


def _react(db, vehicle, e, last_alert, waybill):
    """Сповіщення і запис у «Аномалії пального» для подій телематики."""
    from services.alert_engine import create_alert
    if e['type'] == 'refuel':
        return
    if e['type'] == 'fuel_drain':
        _fuel_drain_anomaly(db, vehicle, e)
    key = e['type'] + (':' + e['code'] if e.get('code') else '')
    prev = last_alert.get(key)
    if prev and e['ts'] - prev < COOLDOWN:
        return
    last_alert[key] = e['ts']
    plate = vehicle.get('plate_number')
    titles = {
        'overheat': f'Перегрів двигуна: {plate}', 'low_battery': f'Низька напруга акумулятора: {plate}',
        'dtc': f"Код помилки {e.get('code')}: {plate}", 'fuel_drain': f'Можливий злив пального: {plate}',
        'no_waybill': f'Рух без путівки: {plate}',
    }
    critical = e['type'] in ('overheat', 'fuel_drain', 'no_waybill')
    roles = ['manager', 'mechanic'] if e['type'] in TECH_EVENTS else ['manager']
    for role in roles:
        create_alert(db, alert_type='critical' if critical else 'warning', category='telematics',
                     title=titles[e['type']], message=e['message'], recipient_role=role,
                     related_type='vehicle', related_id=str(vehicle['_id']))


def _fuel_drain_anomaly(db, vehicle, e):
    liters = float(e.get('value') or 0)
    price = _fuel_price(db, vehicle.get('fuel_type'))
    wb = db.waybills.find_one({'vehicle_id': str(vehicle['_id']), 'status': {'$in': ['active', 'issued']}},
                              {'number': 1, 'driver_id': 1})
    driver = db.users.find_one({'_id': ObjectId(wb['driver_id'])}, {'full_name': 1}) if wb and wb.get('driver_id') else None
    db.fuel_anomalies.update_one(
        {'kind': 'fuel_drain', 'source_type': 'telemetry', 'source_id': str(e['_id'])},
        {'$setOnInsert': {
            'vehicle_id': str(vehicle['_id']), 'plate': vehicle.get('plate_number'), 'vehicle_label': _label(vehicle),
            'driver_id': wb.get('driver_id') if wb else None, 'driver_name': (driver or {}).get('full_name'),
            'date': e['ts'], 'number': wb['number'] if wb else 'Телематика',
            'score': 92, 'level': 'high', 'methods': ['telematics'],
            'reasons': [e['message'] + ' Зафіксовано датчиком рівня пального (телематика).'],
            'metrics': {'liters': round(liters, 1), 'excess_l': round(liters, 1), 'cost': round(liters * price, 2),
                        'lat': e['lat'], 'lon': e['lon']},
            'status': 'new', 'review': None, 'detected_at': datetime.utcnow(), 'updated_at': datetime.utcnow(),
        }}, upsert=True)


# --------------------------------------------------------------------------- читання
def connection(state, now=None):
    now = now or datetime.utcnow()
    if not state or not state.get('ts'):
        return 'none'
    if (now - state['ts']).total_seconds() > OFFLINE_SECONDS:
        return 'offline'
    return 'moving' if (state.get('speed') or 0) > STOPPED_KMH else 'idle'


def fleet(db):
    """Останній стан кожного автомобіля для карти."""
    from services.geo_ukraine import route_points
    now = datetime.utcnow()
    vehicles = list(db.vehicles.find({'status': {'$ne': 'decommissioned'}}))
    states = {s['_id']: s for s in db.telematics_state.find()}
    waybills = {w['vehicle_id']: w for w in db.waybills.find({'status': 'active'})}
    drivers = {str(u['_id']): u.get('full_name') for u in db.users.find({'role': 'driver'}, {'full_name': 1})}
    since = now - timedelta(hours=24)
    counts = {}
    for row in db.telematics_events.aggregate([
            {'$match': {'ts': {'$gte': since}, 'type': {'$ne': 'refuel'}}},
            {'$group': {'_id': '$vehicle_id', 'n': {'$sum': 1}}}]):
        counts[row['_id']] = row['n']
    items = []
    for v in vehicles:
        vid = str(v['_id'])
        s = states.get(vid)
        w = waybills.get(vid)
        route, route_km = (route_points(w.get('route_from'), w.get('route_to')) if w else (None, 0))
        items.append({
            'vehicle_id': vid, 'plate': v.get('plate_number'), 'label': _label(v), 'vehicle_status': v.get('status'),
            'heavy': (v.get('fuel_norm') or 0) >= 20, 'tank': v.get('tank_capacity'),
            'tracker': bool(v.get('telematics')), 'key_hint': (v.get('telematics') or {}).get('key_hint'),
            'connection': connection(s, now),
            'state': {k: s.get(k) for k in ('ts', 'lat', 'lon', 'speed', 'heading', 'odometer', 'fuel_level',
                                            'engine_temp', 'battery_v', 'rpm', 'ignition', 'dtc')} if s else None,
            'alarms': [k for k, on in ((s or {}).get('flags') or {}).items() if on],
            'events_24h': counts.get(vid, 0),
            'waybill': {'id': str(w['_id']), 'number': w.get('number'), 'from': w.get('route_from'), 'to': w.get('route_to'),
                        'driver': drivers.get(w.get('driver_id')), 'route': route, 'route_km': route_km} if w else None,
        })
    summary = {k: sum(1 for i in items if i['connection'] == k) for k in ('moving', 'idle', 'offline', 'none')}
    summary['alarms'] = sum(1 for i in items if i['alarms'])
    from services.geo_ukraine import CITIES, MAJOR
    cities = [{'name': c, 'lat': xy[0], 'lon': xy[1], 'major': c in MAJOR} for c, xy in CITIES.items()]
    return {'items': items, 'summary': summary, 'server_time': now, 'cities': cities}


def vehicle_detail(db, vehicle_id, hours=3):
    hours = max(1, min(int(hours or 3), 48))
    since = datetime.utcnow() - timedelta(hours=hours)
    points = list(db.telemetry.find({'vehicle_id': vehicle_id, 'ts': {'$gte': since}},
                                    {'_id': 0, 'vehicle_id': 0}).sort('ts', 1))
    step = max(1, len(points) // 400)                 # для графіків і треку досить ~400 точок
    thin = points[::step] + ([points[-1]] if points and len(points) % step != 1 and step > 1 else [])
    events = list(db.telematics_events.find({'vehicle_id': vehicle_id}, {'vehicle_id': 0}).sort('ts', -1).limit(30))
    for e in events:
        e['_id'] = str(e['_id'])
    first, last = (points[0], points[-1]) if points else (None, None)
    distance = (last.get('odometer', 0) - first.get('odometer', 0)) if points and first.get('odometer') and last.get('odometer') else 0
    return {'hours': hours, 'points': thin, 'events': events,
            'distance_km': round(distance, 1), 'points_total': len(points)}


def signals(db, vehicle_ids=None, days=14):
    """Кількість технічних подій телематики за період - додаткові сигнали для прогнозу несправностей."""
    match = {'ts': {'$gte': datetime.utcnow() - timedelta(days=days)}, 'type': {'$in': ['overheat', 'low_battery', 'dtc']}}
    if vehicle_ids is not None:
        match['vehicle_id'] = {'$in': list(vehicle_ids)}
    out = {}
    for row in db.telematics_events.aggregate([{'$match': match},
                                               {'$group': {'_id': {'v': '$vehicle_id', 't': '$type'}, 'n': {'$sum': 1},
                                                           'codes': {'$addToSet': '$code'}}}]):
        d = out.setdefault(row['_id']['v'], {'overheat': 0, 'low_battery': 0, 'dtc': 0, 'codes': []})
        d[row['_id']['t']] = row['n']
        d['codes'] = sorted(set(d['codes']) | {c for c in row['codes'] if c})
    return out
