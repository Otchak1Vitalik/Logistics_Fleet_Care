"""
Прогнозне технічне обслуговування: ймовірність несправності автомобіля в найближчі 30 днів.

Дані для навчання - «знімки» стану автомобіля (вік, пробіг, використана частка інтервалу ТО,
нещодавні несправності й ремонти, перевитрата пального ...) і мітка: чи була несправність
протягом HORIZON_DAYS днів після знімка. Знімки зберігаються в колекції maintenance_history:
  - source='synthetic' - трирічна історія, згенерована для демонстрації (seed.py);
  - source='live'      - щомісячні знімки реального автопарку (задача планувальника),
                         мітка для них визначається за журналом несправностей, коли мине 30 днів.

Порівнюються три методи: базове правило ТО (чим ближче до ТО, тим вищий ризик), логістична регресія
і градієнтний бустинг. Модель перевіряється на хронологічному розбитті (навчання - старіші знімки,
перевірка - останні 12 місяців), найкраща за PR-AUC використовується для поточного прогнозу.
"""
import math
import random
from datetime import datetime, timedelta
from statistics import median

from bson import ObjectId

from services import ml_metrics as mm

HORIZON_DAYS = 30
SNAPSHOT_STEP_DAYS = 14
HISTORY_MONTHS = 36
TEST_MONTHS = 12
LEVEL_HIGH, LEVEL_MEDIUM = 0.25, 0.12      # приблизно у 3,5 і 1,7 раза вище за середній рівень відмов
FUEL_WINDOW_DAYS = 14         # відхилення витрати пального - середнє за останні 2 тижні

FEATURES = [
    ('age_years', 'Вік автомобіля'),
    ('odometer_k', 'Загальний пробіг'),
    ('maint_ratio', 'Використано інтервалу ТО'),
    ('days_since_maint', 'Після останнього ТО'),
    ('daily_km', 'Середній добовий пробіг'),
    ('faults_90d', 'Несправностей за 90 днів'),
    ('serious_365d', 'Серйозних несправностей за рік'),
    ('repairs_180d', 'Ремонтів за 180 днів'),
    ('fuel_dev', 'Витрата пального відносно норми'),
    ('heavy', 'Вантажний автомобіль'),
]
# ознаки, для яких може не бути свіжих даних (авто не їздило) - тоді беремо типове значення
IMPUTABLE = ('daily_km', 'fuel_dev')
FEATURE_KEYS = [k for k, _ in FEATURES]
FEATURE_LABELS = dict(FEATURES)
METHODS = {'rule': 'Правило ТО (без ML)', 'logreg': 'Логістична регресія', 'gboost': 'Градієнтний бустинг'}

_CACHE = {}


# --------------------------------------------------------------------------- синтетична історія
def synthetic_history(vehicles, settings, now=None, months=HISTORY_MONTHS, seed=2026):
    """
    Імітує 3 роки експлуатації реальних автомобілів автопарку з кроком в один день.
    Ризик відмови зростає з віком і пробігом, різко - при простроченому ТО; крім того, у авто
    випадково виникає прихований дефект, який підвищує ризик і помітний за зростанням витрати пального.
    Повертає (знімки, події) - події (ТО, несправності) потрібні лише для графіків і тестів.
    """
    rnd = random.Random(seed)
    now = (now or datetime.utcnow()).replace(hour=0, minute=0, second=0, microsecond=0)
    start = now - timedelta(days=months * 30 + HORIZON_DAYS)
    interval_km = float(settings.get('maintenance_interval_km') or 10000)
    interval_days = float(settings.get('maintenance_interval_days') or 180)
    snapshots, events = [], []

    for v in vehicles:
        if v.get('status') == 'decommissioned':
            continue
        vid = str(v['_id'])
        heavy = (v.get('fuel_norm') or 0) >= 20
        days_total = (now - start).days
        build_year = v.get('year') or 2019
        life_days = max(365, (now - datetime(build_year, 1, 1)).days)
        # середній пробіг за день роботи - з фактичного одометра і віку авто
        daily = max(15.0, (v.get('odometer') or 100000) / life_days / 0.85 * rnd.uniform(0.85, 1.15))
        odometer = max(3000.0, (v.get('odometer') or 100000) - daily * 0.85 * days_total)
        discipline = rnd.choices([1.0, 1.2, 1.5], weights=[0.45, 0.3, 0.25])[0]   # наскільки затягують ТО
        fuel_base = rnd.gauss(-4, 3)
        km_log = []
        km_since, days_since = rnd.uniform(0, interval_km * 0.8), rnd.randint(0, int(interval_days * 0.7))
        defect = None                    # прихований дефект: {'day': днів від початку, 'fail_at': через скільки днів відмова, 'fuel': чи видно за пальним}
        faults, repairs, fuel_window = [], [], []

        for d in range(days_total):
            day = start + timedelta(days=d)
            km = daily * rnd.uniform(0.6, 1.4) if rnd.random() < 0.85 else 0.0
            km_log = (km_log + [km])[-90:]
            odometer += km
            km_since += km
            days_since += 1
            if km_since >= interval_km * discipline or days_since >= interval_days * discipline:
                events.append({'vehicle_id': vid, 'date': day, 'type': 'maintenance', 'odometer': round(odometer)})
                repairs.append(day)
                km_since, days_since = 0.0, 0
                if defect and rnd.random() < 0.7:          # більшість дефектів виявляють і усувають на ТО
                    defect = None

            age = (day.year - build_year) + day.timetuple().tm_yday / 365
            ratio = km_since / interval_km
            wear = max(ratio, days_since / interval_days)      # знос з останнього ТО (за пробігом або часом)
            recent = any(0 <= (day - f).days <= 60 for f in faults)
            if defect is None:
                onset = (0.0016 * (1.3 if heavy else 1.0) * (2.0 if recent else 1.0)
                         * math.exp(0.12 * (age - 5) + 0.004 * (odometer / 1000 - 100) + 3.0 * max(0.0, wear - 0.8)))
                if rnd.random() < onset:
                    defect = {'day': 0, 'fail_at': rnd.randint(25, 70), 'fuel': rnd.random() < 0.65}
            else:
                defect['day'] += 1
            fuel_extra = min(12.0, 3 + 0.3 * defect['day']) if defect and defect['fuel'] else 0.0
            fuel_window.append(fuel_base + fuel_extra + rnd.gauss(0, 3) if km else None)
            fuel_window = fuel_window[-14:]
            sudden = rnd.random() < 0.0003                      # раптові відмови, які неможливо передбачити
            if (defect and defect['day'] >= defect['fail_at']) or sudden:
                severity = rnd.choices(['low', 'medium', 'high', 'critical'], weights=[0.25, 0.4, 0.25, 0.1])[0]
                faults.append(day)
                events.append({'vehicle_id': vid, 'date': day, 'type': 'fault', 'severity': severity,
                               'odometer': round(odometer)})
                if severity in ('high', 'critical'):
                    events[-1]['serious'] = True
                repairs.append(day + timedelta(days=rnd.randint(1, 4)))
                defect = None

            if d % SNAPSHOT_STEP_DAYS == 0 and d >= 120 and d + HORIZON_DAYS < days_total:
                fuel_vals = [x for x in fuel_window if x is not None]
                snapshots.append({
                    'source': 'synthetic', 'vehicle_id': vid, 'plate': v.get('plate_number'), 'date': day,
                    'features': {
                        'age_years': round(age, 2), 'odometer_k': round(odometer / 1000, 1),
                        'maint_ratio': round(ratio, 3), 'days_since_maint': days_since,
                        'daily_km': round(sum(km_log) / 90, 1),
                        'faults_90d': sum(1 for f in faults if 0 <= (day - f).days <= 90),
                        'serious_365d': sum(1 for e in events if e['vehicle_id'] == vid and e.get('serious')
                                            and 0 <= (day - e['date']).days <= 365),
                        'repairs_180d': sum(1 for r in repairs if 0 <= (day - r).days <= 180),
                        'fuel_dev': round(sum(fuel_vals) / len(fuel_vals), 1) if fuel_vals else 0.0,
                        'heavy': 1 if heavy else 0,
                    },
                    'label': None,   # визначимо нижче, коли відомі всі майбутні несправності
                })
        own = [e['date'] for e in events if e['vehicle_id'] == vid and e['type'] == 'fault']
        for s in snapshots:
            if s['vehicle_id'] == vid and s['label'] is None:
                s['label'] = int(any(0 < (f - s['date']).days <= HORIZON_DAYS for f in own))
    return snapshots, events


# --------------------------------------------------------------------------- ознаки реального автопарку
def _oid(value):
    try:
        return ObjectId(value)
    except Exception:  # noqa: BLE001
        return None


def current_features(db, vehicles=None, now=None, settings=None):
    """Ознаки для кожного активного автомобіля станом на зараз (з реальних даних системи)."""
    from services.maintenance_forecast import daily_mileage
    from services.fuel_anomalies import trip_dataset
    now = now or datetime.utcnow()
    settings = settings if settings is not None else (db.settings.find_one({'_id': 'system'}) or {})
    interval_km = float(settings.get('maintenance_interval_km') or 10000)
    vehicles = vehicles if vehicles is not None else list(db.vehicles.find({'status': {'$ne': 'decommissioned'}}))
    ids = [str(v['_id']) for v in vehicles]
    daily = daily_mileage(db, vehicle_ids=ids)
    fuel = {}
    for t in trip_dataset(db, since_days=FUEL_WINDOW_DAYS, settings=settings):
        fuel.setdefault(t['vehicle_id'], []).append((t['ratio'] - 1) * 100)
    faults = list(db.fault_reports.find({'vehicle_id': {'$in': ids}, 'report_date': {'$gte': now - timedelta(days=365)}},
                                        {'vehicle_id': 1, 'report_date': 1, 'severity': 1}))
    repairs = list(db.repairs.find({'vehicle_id': {'$in': ids}, 'status': 'completed',
                                    'completed_at': {'$gte': now - timedelta(days=180)}}, {'vehicle_id': 1}))
    out = {}
    for v in vehicles:
        vid = str(v['_id'])
        odometer = v.get('odometer') or 0
        last_km = v.get('last_maintenance_km')
        if last_km is None and v.get('next_maintenance_km'):
            last_km = v['next_maintenance_km'] - interval_km
        last_date = v.get('last_maintenance_date')
        own_faults = [f for f in faults if f['vehicle_id'] == vid and isinstance(f.get('report_date'), datetime)]
        out[vid] = {
            'age_years': round(max(0, now.year - (v.get('year') or now.year)) + now.timetuple().tm_yday / 365, 2),
            'odometer_k': round(odometer / 1000, 1),
            'maint_ratio': round(max(0.0, odometer - (last_km or odometer)) / interval_km, 3),
            'days_since_maint': (now - last_date).days if isinstance(last_date, datetime) else 90,
            'daily_km': round(daily[vid], 1) if daily.get(vid) else None,
            'faults_90d': sum(1 for f in own_faults if (now - f['report_date']).days <= 90),
            'serious_365d': sum(1 for f in own_faults if f.get('severity') in ('high', 'critical')),
            'repairs_180d': sum(1 for r in repairs if r['vehicle_id'] == vid),
            'fuel_dev': round(sum(fuel[vid]) / len(fuel[vid]), 1) if fuel.get(vid) else None,
            'heavy': 1 if (v.get('fuel_norm') or 0) >= 20 else 0,
        }
    return out


def _label_live(db, rows):
    """Мітки для реальних знімків: була несправність протягом 30 днів (лише для знімків, старших за 30 днів)."""
    now = datetime.utcnow()
    out = []
    for r in rows:
        if r.get('label') is None:
            if (now - r['date']).days <= HORIZON_DAYS:
                continue
            r['label'] = int(db.fault_reports.count_documents({
                'vehicle_id': r['vehicle_id'],
                'report_date': {'$gt': r['date'], '$lte': r['date'] + timedelta(days=HORIZON_DAYS)}}) > 0)
            db.maintenance_history.update_one({'_id': r['_id']}, {'$set': {'label': r['label']}})
        out.append(r)
    return out


def take_snapshot(db):
    """Щомісячний знімок реального автопарку (мітка з'явиться через 30 днів)."""
    now = datetime.utcnow()
    feats = current_features(db, now=now)
    plates = {str(v['_id']): v.get('plate_number') for v in db.vehicles.find({}, {'plate_number': 1})}
    docs = [{'source': 'live', 'vehicle_id': vid, 'plate': plates.get(vid), 'date': now, 'features': f, 'label': None}
            for vid, f in feats.items()]
    if docs:
        db.maintenance_history.insert_many(docs)
    return len(docs)


# --------------------------------------------------------------------------- моделі
def _matrix(rows):
    import numpy as np
    X = np.array([[np.nan if r['features'].get(k) is None else float(r['features'][k]) for k in FEATURE_KEYS]
                  for r in rows], dtype=float)
    if np.isnan(X).any():                       # пропуски в реальних знімках - медіаною ознаки
        med = np.nanmedian(X, axis=0)
        X = np.where(np.isnan(X), np.nan_to_num(med)[None, :], X)
    y = np.array([int(r['label']) for r in rows], dtype=int)
    return X, y


def _rule_score(X):
    """Базове правило: ризик зростає, коли наближається ТО; прострочене ТО - найвищий ризик."""
    i = FEATURE_KEYS.index('maint_ratio')
    return (X[:, i] / 1.2).clip(0, 1)


def _models():
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    return {
        'logreg': make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, C=1.0)),
        'gboost': HistGradientBoostingClassifier(max_iter=200, learning_rate=0.05, max_depth=3,
                                                 min_samples_leaf=30, l2_regularization=1.0, random_state=42),
    }


def _predict(key, model, X):
    return _rule_score(X) if key == 'rule' else model.predict_proba(X)[:, 1]


def train(db, force=False):
    """Навчає й оцінює моделі; результат кешується до зміни кількості знімків."""
    import numpy as np
    rows = _label_live(db, list(db.maintenance_history.find({}, {'features': 1, 'label': 1, 'date': 1, 'source': 1,
                                                                 'vehicle_id': 1})))
    sig = (len(rows), sum(r['label'] for r in rows))
    if not force and _CACHE.get('sig') == sig:
        return _CACHE
    if len(rows) < 100 or len({r['label'] for r in rows}) < 2:
        _CACHE.clear()
        _CACHE.update({'sig': sig, 'ready': False, 'rows': len(rows)})
        return _CACHE

    rows.sort(key=lambda r: r['date'])
    split_date = rows[-1]['date'] - timedelta(days=TEST_MONTHS * 30)
    train_rows = [r for r in rows if r['date'] < split_date]
    test_rows = [r for r in rows if r['date'] >= split_date]
    Xtr, ytr = _matrix(train_rows)
    Xte, yte = _matrix(test_rows)

    methods, fitted = [], {}
    for key in ('rule', 'logreg', 'gboost'):
        model = None
        if key != 'rule':
            model = _models()[key].fit(Xtr, ytr)
        p_tr, p_te = _predict(key, model, Xtr), _predict(key, model, Xte)
        thr = mm.best_threshold(ytr, p_tr, objective='f1')           # поріг - лише за навчальними даними
        methods.append({'key': key, 'title': METHODS[key], **mm.summary(yte, p_te, thr), **mm.curves(yte, p_te),
                        'calibration': mm.calibration(yte, p_te, bins=8)})
        fitted[key] = (model, thr)

    best = max((m for m in methods if m['key'] != 'rule'), key=lambda m: m['pr_auc'])['key']

    # важливість ознак для найкращої моделі (перестановочна, на перевірних даних)
    from sklearn.inspection import permutation_importance
    pi = permutation_importance(fitted[best][0], Xte, yte, scoring='average_precision', n_repeats=5, random_state=0)
    importance = sorted([{'feature': k, 'label': FEATURE_LABELS[k], 'value': round(float(v), 4)}
                         for k, v in zip(FEATURE_KEYS, pi.importances_mean)], key=lambda x: -x['value'])

    # фінальні моделі - на всіх даних; логістична регресія - також для пояснення чинників
    X_all, y_all = _matrix(rows)
    final = _models()[best].fit(X_all, y_all)
    explainer = _models()['logreg'].fit(X_all, y_all)
    medians = {k: float(np.median(X_all[:, i])) for i, k in enumerate(FEATURE_KEYS)}

    _CACHE.clear()
    _CACHE.update({
        'sig': sig, 'ready': True, 'best': best, 'model': final, 'threshold': fitted[best][1],
        'explainer': explainer, 'medians': medians, 'trained_at': datetime.utcnow(),
        'evaluation': {
            'rows': len(rows), 'positives': int(y_all.sum()), 'base_rate': round(float(y_all.mean()), 3),
            'synthetic': sum(1 for r in rows if r.get('source') == 'synthetic'),
            'live': sum(1 for r in rows if r.get('source') == 'live'),
            'vehicles': len({r['vehicle_id'] for r in rows}),
            'train': {'n': len(train_rows), 'from': train_rows[0]['date'], 'to': train_rows[-1]['date'], 'positives': int(ytr.sum())},
            'test': {'n': len(test_rows), 'from': test_rows[0]['date'], 'to': test_rows[-1]['date'], 'positives': int(yte.sum())},
            'horizon_days': HORIZON_DAYS, 'best': best, 'methods': methods, 'importance': importance,
            'features': [{'key': k, 'label': lbl} for k, lbl in FEATURES],
        },
    })
    return _CACHE


# --------------------------------------------------------------------------- поточний прогноз
def _level(p):
    return 'high' if p >= LEVEL_HIGH else 'medium' if p >= LEVEL_MEDIUM else 'low'


def _filled(state, feats):
    """Пропущені ознаки (немає свіжих рейсів) замінюються типовими значеннями з історії."""
    return {k: (state['medians'][k] if feats.get(k) is None else feats[k]) for k in FEATURE_KEYS}


def _factors(state, feats):
    """Внесок ознак у ризик за логістичною регресією (стандартизоване значення × коефіцієнт)."""
    import numpy as np
    missing = {k for k in FEATURE_KEYS if feats.get(k) is None}
    feats = _filled(state, feats)
    scaler, lr = state['explainer'].named_steps['standardscaler'], state['explainer'].named_steps['logisticregression']
    x = np.array([[float(feats[k]) for k in FEATURE_KEYS]])
    contrib = ((x - scaler.mean_) / scaler.scale_)[0] * lr.coef_[0]
    out = []
    for i in np.argsort(-contrib):
        k = FEATURE_KEYS[i]
        if contrib[i] <= 0.35 or len(out) >= 3 or k == 'heavy' or k in missing:
            continue
        if k == 'fuel_dev' and feats[k] < 2:            # пальне - чинник лише при реальній перевитраті
            continue
        out.append({'feature': k, 'label': FEATURE_LABELS[k], 'value': feats[k],
                    'typical': round(state['medians'][k], 2), 'weight': round(float(contrib[i]), 2)})
    return out


def _recommendation(feats, factors, level):
    keys = {f['feature'] for f in factors}
    if feats['maint_ratio'] >= 1:
        return 'ТО прострочене - поставити автомобіль на ТО першочергово.'
    if 'fuel_dev' in keys and (feats['fuel_dev'] or 0) >= 5:
        return 'Зросла витрата пального - провести діагностику двигуна й паливної системи.'
    if 'maint_ratio' in keys and feats['maint_ratio'] >= 0.8:
        return 'Наближається ТО - запланувати його найближчим часом.'
    if keys & {'faults_90d', 'serious_365d'}:
        return 'Часті несправності - провести поглиблений огляд вузлів, що ремонтувалися.'
    if level == 'high':
        return 'Провести позаплановий огляд.'
    return None


def fleet_risk(db, vehicle_id=None):
    state = train(db)
    if not state.get('ready'):
        return {'ready': False, 'items': [], 'rows': state.get('rows', 0)}
    import numpy as np
    query = {'status': {'$ne': 'decommissioned'}}
    if vehicle_id:
        oid = _oid(vehicle_id)
        if not oid:
            return {'ready': True, 'items': []}
        query['_id'] = oid
    vehicles = list(db.vehicles.find(query))
    feats = current_features(db, vehicles=vehicles)
    items = []
    for v in vehicles:
        vid = str(v['_id'])
        f = feats[vid]
        filled = _filled(state, f)
        p = float(state['model'].predict_proba(np.array([[float(filled[k]) for k in FEATURE_KEYS]]))[0, 1])
        level = _level(p)
        factors = _factors(state, f)
        items.append({
            'vehicle_id': vid, 'plate': v.get('plate_number'),
            'vehicle_label': f"{v.get('plate_number')} {v.get('brand', '')} {v.get('model', '')}".strip(),
            'status': v.get('status'), 'probability': round(p, 3), 'level': level,
            'features': f, 'factors': factors, 'recommendation': _recommendation(f, factors, level),
            'next_maintenance_km': v.get('next_maintenance_km'), 'next_maintenance_date': v.get('next_maintenance_date'),
        })
    items.sort(key=lambda x: -x['probability'])
    return {
        'ready': True, 'items': items, 'model': METHODS[state['best']], 'model_key': state['best'],
        'trained_at': state['trained_at'], 'horizon_days': HORIZON_DAYS,
        'summary': {
            'high': sum(1 for i in items if i['level'] == 'high'),
            'medium': sum(1 for i in items if i['level'] == 'medium'),
            'low': sum(1 for i in items if i['level'] == 'low'),
            'expected_failures': round(sum(i['probability'] for i in items), 1),
        },
    }


def check_risks(db):
    """Задача планувальника: сповіщення керівнику про авто з високим ризиком (не частіше ніж раз на 7 днів)."""
    from services.alert_engine import create_alert
    result = fleet_risk(db)
    created = 0
    for item in result.get('items', []):
        if item['level'] != 'high' or item['status'] not in ('active', None):
            continue
        recent = db.alerts.find_one({'related_type': 'vehicle_risk', 'related_id': item['vehicle_id'],
                                     'created_at': {'$gte': datetime.utcnow() - timedelta(days=7)}})
        if recent:
            continue
        create_alert(db, alert_type='warning', category='maintenance',
                     title=f"Високий ризик несправності: {item['plate']}",
                     message=f"Ймовірність несправності протягом {HORIZON_DAYS} днів - {round(item['probability'] * 100)} %. "
                             + (item['recommendation'] or ''),
                     recipient_role='manager', related_type='vehicle_risk', related_id=item['vehicle_id'])
        created += 1
    return created


def seed_history(db, now=None):
    """Заповнює колекцію maintenance_history синтетичною історією для демонстрації."""
    settings = db.settings.find_one({'_id': 'system'}) or {}
    vehicles = list(db.vehicles.find())
    snapshots, _ = synthetic_history(vehicles, settings, now=now)
    db.maintenance_history.delete_many({'source': 'synthetic'})
    if snapshots:
        db.maintenance_history.insert_many(snapshots)
    _CACHE.clear()
    return len(snapshots)
