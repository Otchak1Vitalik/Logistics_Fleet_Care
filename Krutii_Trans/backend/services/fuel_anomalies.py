"""
Виявлення аномалій у витраті пального.

Рейси (завершені путівки) перевіряються трьома методами, результати яких потім порівнюються:
  1) rule  - правило норми: фактична витрата перевищує нормативну (з сезонним коефіцієнтом) більше ніж на поріг;
  2) stat  - робастний z-score: відхилення від ЗВИЧНОЇ витрати цього автомобіля (медіана і MAD,
             метод Іглевича - Гоагліна, поріг 3.5); для авто з малою історією - відносно всього автопарку;
  3) ml    - Isolation Forest (scikit-learn) за кількома ознаками рейсу.
Окремо перевіряються заправки: понад об'єм бака, дві заправки поспіль майже без пробігу, нетипова ціна.

Знайдені випадки зберігаються в колекції fuel_anomalies; керівник позначає їх як «підтверджено»
або «хибна тривога». Ці рішення (а на демонстраційних даних - вбудовані мітки) використовуються
для оцінки точності методів (precision / recall / F1).
"""
import math
from datetime import datetime, timedelta
from statistics import median

from bson import ObjectId

from services.fuel_analyzer import get_season_coefficient

Z_THRESHOLD = 3.5            # поріг робастного z-score (Iglewicz & Hoaglin, 1993)
MIN_VEHICLE_TRIPS = 6        # менше рейсів - порівнюємо з усім автопарком
HISTORY_DAYS = 365
PRICE_DEVIATION = 0.15       # ціна відрізняється від медіанної більше ніж на 15 %
DOUBLE_REFUEL_HOURS = 24
DOUBLE_REFUEL_KM = 150
DEFAULT_PRICES = {'diesel': 54.0, 'petrol': 56.0, 'gas': 30.0}
RECOMPUTED_KINDS = ('trip_overspend', 'over_tank', 'double_refuel', 'price')
METHOD_LABELS = {'rule': 'Правило норми', 'stat': 'Статистика (z-score)', 'ml': 'Isolation Forest'}


def _oid(value):
    try:
        return ObjectId(value)
    except Exception:  # noqa: BLE001
        return None


def _mad(values, med):
    return median(abs(v - med) for v in values) if values else 0.0


def robust_z(value, values):
    """Робастний z-score: 0.6745 * (x - медіана) / MAD."""
    med = median(values)
    mad = max(_mad(values, med), 0.01)
    return 0.6745 * (value - med) / mad, med


def trip_dataset(db, since_days=HISTORY_DAYS, settings=None):
    """Завершені рейси з пробігом і витратою: фактична витрата відносно норми з урахуванням сезону."""
    settings = settings if settings is not None else (db.settings.find_one({'_id': 'system'}) or {})
    since = datetime.utcnow() - timedelta(days=since_days)
    waybills = list(db.waybills.find({
        'status': 'completed', 'completed_at': {'$gte': since},
        'odometer_end': {'$ne': None}, 'fuel_used': {'$ne': None},
    }))
    vehicles = {str(v['_id']): v for v in db.vehicles.find({'_id': {'$in': list({_oid(w['vehicle_id']) for w in waybills} - {None})}})}
    drivers = {str(u['_id']): u for u in db.users.find({'_id': {'$in': list({_oid(w.get('driver_id')) for w in waybills} - {None})}},
                                                       {'full_name': 1})}
    trips = []
    for w in waybills:
        v = vehicles.get(w['vehicle_id'])
        distance = (w.get('odometer_end') or 0) - (w.get('odometer_start') or 0)
        if not v or not v.get('fuel_norm') or distance <= 0 or not w.get('fuel_used'):
            continue
        coef = get_season_coefficient(w['completed_at'], settings)
        expected = distance / 100 * v['fuel_norm'] * coef
        trips.append({
            'waybill_id': str(w['_id']), 'number': w.get('number'), 'date': w['completed_at'],
            'vehicle_id': w['vehicle_id'], 'plate': v.get('plate_number'),
            'vehicle_label': f"{v.get('plate_number')} {v.get('brand', '')} {v.get('model', '')}".strip(),
            'fuel_type': v.get('fuel_type'), 'tank': v.get('tank_capacity'),
            'driver_id': w.get('driver_id'), 'driver_name': (drivers.get(w.get('driver_id')) or {}).get('full_name'),
            'distance': distance, 'fuel_used': float(w['fuel_used']), 'season_coef': coef,
            'norm_l100': v['fuel_norm'] * coef, 'actual_l100': w['fuel_used'] / distance * 100,
            'expected_l': expected, 'ratio': w['fuel_used'] / expected,
            'demo_label': w.get('demo_anomaly'),
        })
    return trips


def score_trips(trips, threshold_pct):
    """Застосовує три методи до кожного рейсу (додає поля в словники рейсів)."""
    if not trips:
        return trips
    fleet = [t['ratio'] for t in trips]
    by_vehicle = {}
    for t in trips:
        by_vehicle.setdefault(t['vehicle_id'], []).append(t['ratio'])

    for t in trips:
        hist = by_vehicle[t['vehicle_id']]
        basis = hist if len(hist) >= MIN_VEHICLE_TRIPS else fleet
        t['z'], t['typical_ratio'] = robust_z(t['ratio'], basis)
        t['z_basis'] = 'vehicle' if basis is hist else 'fleet'
        t['deviation_pct'] = (t['ratio'] - 1) * 100
        t['rule'] = t['deviation_pct'] > threshold_pct
        t['stat'] = t['z'] > Z_THRESHOLD

    # Isolation Forest: аномальність за сукупністю ознак
    try:
        import numpy as np
        from sklearn.ensemble import IsolationForest
        X = np.array([[t['ratio'], t['z'], math.log(t['distance']), t['fuel_used'] / (t['tank'] or 400),
                       t['ratio'] / max(t['typical_ratio'], 0.5)] for t in trips])
        if len(trips) >= 20:
            model = IsolationForest(n_estimators=300, contamination='auto', random_state=42).fit(X)
            raw = -model.decision_function(X)                  # більше - аномальніше
            pred = model.predict(X)
            lo, hi = float(raw.min()), float(raw.max())
            for t, r, p in zip(trips, raw, pred):
                t['ml_score'] = (float(r) - lo) / (hi - lo) if hi > lo else 0.0
                # нас цікавить перевитрата, тому «аномально мала витрата» не позначаємо
                t['ml'] = bool(p == -1 and t['ratio'] > t['typical_ratio'])
        else:
            for t in trips:
                t['ml_score'], t['ml'] = 0.0, False
    except ImportError:            # scikit-learn не встановлено - працюють два інші методи
        for t in trips:
            t['ml_score'], t['ml'] = 0.0, False

    for t in trips:
        t['methods'] = [m for m in ('rule', 'stat', 'ml') if t[m]]
        # система показує випадок, якщо його позначив хоча б один метод і є перевитрата
        # (відносно норми або звичної витрати авто)
        t['flagged'] = bool(t['methods']) and (t['ratio'] > 1.0 or t['stat'])
        # ризик 0..100: відхилення від норми, від звичної витрати авто, оцінка моделі і згода методів
        risk = (35 * min(max(t['deviation_pct'], 0) / 50, 1)
                + 30 * min(max(t['z'], 0) / 12, 1)
                + 25 * t['ml_score'] * (1 if t['ratio'] > t['typical_ratio'] else 0))
        t['score'] = round(min(100, risk + 5 * (len(t['methods']) - 1 if t['methods'] else 0)))
        t['excess_l'] = max(0.0, t['fuel_used'] - t['expected_l'] * min(1.0, t['typical_ratio'] if t['z_basis'] == 'vehicle' else 1.0))
    return trips


def _level(score):
    return 'high' if score >= 65 else 'medium' if score >= 40 else 'low'


def _prices(db):
    since = datetime.utcnow() - timedelta(days=90)
    out = {}
    for ft in ('diesel', 'petrol', 'gas'):
        vals = [r['price_per_liter'] for r in db.fuel_records.find(
            {'fuel_type': ft, 'price_per_liter': {'$gt': 0}, 'date': {'$gte': since}}, {'price_per_liter': 1})]
        vals += [i['price_per_liter'] for i in db.fuel_invoices.find(
            {'fuel_type': ft, 'price_per_liter': {'$gt': 0}}, {'price_per_liter': 1})]
        out[ft] = median(vals) if vals else DEFAULT_PRICES[ft]
    return out


def _trip_reasons(t, threshold_pct):
    r = []
    if t['rule']:
        r.append(f"Витрата {t['actual_l100']:.1f} л/100 км при нормі {t['norm_l100']:.1f} л/100 км "
                 f"(з урахуванням сезону) - на {t['deviation_pct']:.0f} % вище норми (поріг {threshold_pct:.0f} %).")
    if t['stat']:
        who = 'цього автомобіля' if t['z_basis'] == 'vehicle' else 'автопарку'
        r.append(f"Звичайна витрата {who} - близько {t['typical_ratio'] * 100:.0f} % від норми, у цьому рейсі - "
                 f"{t['ratio'] * 100:.0f} % (робастний z = {t['z']:.1f} при порозі {Z_THRESHOLD}).")
    if t['ml']:
        r.append('Модель Isolation Forest визначила рейс як нетиповий за сукупністю ознак '
                 '(витрата, пробіг, обсяг відносно бака, звична поведінка авто).')
    return r


def refuel_findings(db):
    """Перевірки заправок: понад бак, подвійна заправка, нетипова ціна."""
    since = datetime.utcnow() - timedelta(days=HISTORY_DAYS)
    records = list(db.fuel_records.find({'date': {'$gte': since}}).sort('date', 1))
    vehicles = {str(v['_id']): v for v in db.vehicles.find({}, {'plate_number': 1, 'brand': 1, 'model': 1, 'tank_capacity': 1, 'fuel_type': 1})}
    drivers = {str(u['_id']): u.get('full_name') for u in db.users.find({'role': 'driver'}, {'full_name': 1})}
    prices = _prices(db)
    last_by_vehicle = {}
    out = []
    for r in records:
        v = vehicles.get(r.get('vehicle_id'))
        if not v:
            continue
        base = {
            'source_type': 'fuel_record', 'source_id': str(r['_id']), 'vehicle_id': r['vehicle_id'],
            'plate': v.get('plate_number'), 'vehicle_label': f"{v.get('plate_number')} {v.get('brand', '')} {v.get('model', '')}".strip(),
            'driver_id': r.get('driver_id'), 'driver_name': drivers.get(r.get('driver_id')), 'date': r.get('date'),
            'number': r.get('receipt_number') or ('АЗС ' + r['station'] if r.get('station') else 'Видача зі складу'),
            'demo_label': r.get('demo_anomaly'),
        }
        qty, tank = r.get('quantity') or 0, v.get('tank_capacity')
        price = prices.get(v.get('fuel_type'), 54.0)
        if tank and qty > tank * 1.05:
            out.append({**base, 'kind': 'over_tank', 'score': min(100, round(70 + 30 * min((qty / tank - 1) / 0.5, 1))),
                        'metrics': {'quantity': qty, 'tank': tank, 'excess_l': qty - tank, 'cost': round((qty - tank) * price, 2)},
                        'reasons': [f'Заправлено {qty:.0f} л при об’ємі бака {tank:.0f} л - на {qty - tank:.0f} л більше, ніж може вміститися.']})
        prev = last_by_vehicle.get(r['vehicle_id'])
        if prev and r.get('date') and prev.get('date'):
            hours = (r['date'] - prev['date']).total_seconds() / 3600
            km = (r.get('odometer') or 0) - (prev.get('odometer') or 0)
            if 0 <= hours <= DOUBLE_REFUEL_HOURS and 0 <= km < DOUBLE_REFUEL_KM and qty > 0.3 * (tank or 400):
                out.append({**base, 'kind': 'double_refuel', 'score': 72,
                            'metrics': {'quantity': qty, 'hours': round(hours, 1), 'km': km, 'excess_l': qty, 'cost': round(qty * price, 2)},
                            'reasons': [f'Повторна заправка {qty:.0f} л через {hours:.0f} год після попередньої, '
                                        f'пробіг між ними лише {km:.0f} км.']})
        last_by_vehicle[r['vehicle_id']] = r
        p = r.get('price_per_liter')
        med = prices.get(v.get('fuel_type'))
        if p and med and abs(p - med) / med > PRICE_DEVIATION:
            dev = (p - med) / med * 100
            out.append({**base, 'kind': 'price', 'score': min(90, round(45 + abs(dev))),
                        'metrics': {'price': p, 'median_price': round(med, 2), 'deviation_pct': round(dev, 1),
                                    'cost': round(max(0, p - med) * qty, 2), 'excess_l': 0},
                        'reasons': [f'Ціна {p:.2f} грн/л відрізняється від звичної ({med:.2f} грн/л) на {dev:+.0f} %.']})
    return out


def run_detection(db, notify=True):
    """Повна перевірка: оновлює колекцію fuel_anomalies, зберігаючи рішення керівника. Повертає підсумок."""
    settings = db.settings.find_one({'_id': 'system'}) or {}
    threshold = float(settings.get('overspend_threshold') or 10)
    trips = score_trips(trip_dataset(db, settings=settings), threshold)
    prices = _prices(db)
    now = datetime.utcnow()
    found = []
    for t in trips:
        if not t['flagged']:
            continue
        cost = round(t['excess_l'] * prices.get(t['fuel_type'], 54.0), 2)
        found.append({
            'kind': 'trip_overspend', 'source_type': 'waybill', 'source_id': t['waybill_id'], 'number': t['number'],
            'vehicle_id': t['vehicle_id'], 'plate': t['plate'], 'vehicle_label': t['vehicle_label'],
            'driver_id': t['driver_id'], 'driver_name': t['driver_name'], 'date': t['date'],
            'score': t['score'], 'methods': t['methods'], 'reasons': _trip_reasons(t, threshold),
            'metrics': {'distance': t['distance'], 'fuel_used': round(t['fuel_used'], 1), 'actual_l100': round(t['actual_l100'], 2),
                        'norm_l100': round(t['norm_l100'], 2), 'deviation_pct': round(t['deviation_pct'], 1),
                        'typical_pct': round(t['typical_ratio'] * 100, 1), 'z': round(t['z'], 2), 'z_basis': t['z_basis'],
                        'ml_score': round(t['ml_score'], 3), 'excess_l': round(t['excess_l'], 1), 'cost': cost},
            'demo_label': t['demo_label'],
        })
    for f in refuel_findings(db):
        f['methods'] = ['check']
        found.append(f)

    keys = set()
    new_high = []
    for f in found:
        f['level'] = _level(f['score'])
        key = {'kind': f['kind'], 'source_type': f['source_type'], 'source_id': f['source_id']}
        keys.add((f['kind'], f['source_id']))
        existing = db.fuel_anomalies.find_one(key, {'status': 1})
        doc = {**f, 'updated_at': now}
        demo = doc.pop('demo_label', None)
        if existing:
            db.fuel_anomalies.update_one({'_id': existing['_id']}, {'$set': doc})
        else:
            db.fuel_anomalies.insert_one({**doc, 'demo_label': demo, 'status': 'new', 'review': None, 'detected_at': now})
            if f['level'] == 'high':
                new_high.append(f)
    # випадки, які після перерахунку вже не вважаються аномаліями і ще не розглянуті, - прибираємо
    # (зливи, зафіксовані телематикою, цим перерахунком не перевіряються - їх не чіпаємо)
    for doc in db.fuel_anomalies.find({'status': 'new', 'kind': {'$in': list(RECOMPUTED_KINDS)}}, {'kind': 1, 'source_id': 1}):
        if (doc['kind'], doc['source_id']) not in keys:
            db.fuel_anomalies.delete_one({'_id': doc['_id']})

    if notify and new_high:
        from services.alert_engine import create_alert
        if len(new_high) == 1:
            f = new_high[0]
            create_alert(db, alert_type='critical', category='fuel',
                         title=f"Підозріла витрата пального: {f['plate']}",
                         message=' '.join(f['reasons'][:1]) + ' Перевірте на сторінці «Аномалії витрати пального».',
                         recipient_role='manager', related_type='fuel_anomaly', related_id=f['source_id'])
        else:
            create_alert(db, alert_type='warning', category='fuel',
                         title=f'Нові підозрілі випадки витрати пального: {len(new_high)}',
                         message='Система виявила рейси або заправки з високим ризиком. Перевірте на сторінці «Аномалії витрати пального».',
                         recipient_role='manager', related_type='fuel_anomaly', related_id=None)
    return {'trips_checked': len(trips), 'found': len(found), 'new_high': len(new_high)}


def summary(db):
    agg = {s: db.fuel_anomalies.count_documents({'status': s}) for s in ('new', 'confirmed', 'dismissed')}
    loss = list(db.fuel_anomalies.aggregate([
        {'$match': {'status': {'$in': ['new', 'confirmed']}}},
        {'$group': {'_id': None, 'liters': {'$sum': '$metrics.excess_l'}, 'cost': {'$sum': '$metrics.cost'}}},
    ]))
    agg['loss_liters'] = round(loss[0]['liters'], 1) if loss else 0
    agg['loss_cost'] = round(loss[0]['cost'], 2) if loss else 0
    agg['high_new'] = db.fuel_anomalies.count_documents({'status': 'new', 'level': 'high'})
    return agg


def _metrics(tp, fp, fn, tn):
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {'tp': tp, 'fp': fp, 'fn': fn, 'tn': tn, 'precision': round(precision, 3),
            'recall': round(recall, 3), 'f1': round(f1, 3)}


def evaluate(db):
    """
    Точність методів на рейсах з відомою відповіддю.
    Еталон: рішення керівника (підтверджено / хибна тривога), а для решти рейсів демонстраційних даних -
    вбудовані мітки (demo_anomaly). Рейси без мітки вважаються нормальними лише на демонстраційних даних.
    """
    settings = db.settings.find_one({'_id': 'system'}) or {}
    threshold = float(settings.get('overspend_threshold') or 10)
    trips = score_trips(trip_dataset(db, settings=settings), threshold)
    reviewed = {d['source_id']: d['status'] for d in db.fuel_anomalies.find(
        {'source_type': 'waybill', 'status': {'$in': ['confirmed', 'dismissed']}}, {'source_id': 1, 'status': 1})}
    has_demo = any(t['demo_label'] for t in trips)
    labeled = []
    for t in trips:
        if t['waybill_id'] in reviewed:
            truth = reviewed[t['waybill_id']] == 'confirmed'
        elif has_demo:
            truth = bool(t['demo_label'])
        else:
            continue
        labeled.append((t, truth))
    result = {'labeled': len(labeled), 'positives': sum(1 for _, y in labeled if y),
              'source': 'demo' if has_demo else ('review' if reviewed else 'none'), 'methods': []}
    for key, title in [('rule', METHOD_LABELS['rule']), ('stat', METHOD_LABELS['stat']), ('ml', METHOD_LABELS['ml']),
                       ('any', 'Будь-який метод (система)'), ('vote', 'Щонайменше два методи')]:
        tp = fp = fn = tn = 0
        for t, y in labeled:
            p = (t['flagged'] if key == 'any' else t['flagged'] and len(t['methods']) >= 2 if key == 'vote' else t[key])
            tp += p and y
            fp += p and not y
            fn += (not p) and y
            tn += (not p) and not y
        result['methods'].append({'key': key, 'title': title, **_metrics(tp, fp, fn, tn)})
    # чутливість правила норми до порогу
    result['rule_thresholds'] = []
    for thr in (5, 10, 15, 20, 25, 30):
        tp = sum(1 for t, y in labeled if t['deviation_pct'] > thr and y)
        fp = sum(1 for t, y in labeled if t['deviation_pct'] > thr and not y)
        fn = sum(1 for t, y in labeled if t['deviation_pct'] <= thr and y)
        tn = len(labeled) - tp - fp - fn
        result['rule_thresholds'].append({'threshold': thr, **_metrics(tp, fp, fn, tn)})
    return result


def vehicle_history(db, vehicle_id):
    """Рейси одного авто для графіка: відсоток від норми по датах і позначені аномалії."""
    settings = db.settings.find_one({'_id': 'system'}) or {}
    trips = [t for t in trip_dataset(db, settings=settings) if t['vehicle_id'] == vehicle_id]
    trips.sort(key=lambda t: t['date'])
    flagged = {d['source_id'] for d in db.fuel_anomalies.find({'vehicle_id': vehicle_id, 'source_type': 'waybill'}, {'source_id': 1})}
    ratios = [t['ratio'] for t in trips]
    typical = median(ratios) * 100 if ratios else 100
    return {
        'typical_pct': round(typical, 1),
        'points': [{'date': t['date'].isoformat() + 'Z', 'number': t['number'], 'pct': round(t['ratio'] * 100, 1),
                    'actual_l100': round(t['actual_l100'], 2), 'norm_l100': round(t['norm_l100'], 2),
                    'flagged': t['waybill_id'] in flagged, 'waybill_id': t['waybill_id']} for t in trips],
    }
