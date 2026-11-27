"""
Оптимізація графіка технічного обслуговування.

Задача: розподілити ТО автомобілів по днях планового горизонту (2-4 тижні) так, щоб мінімізувати
очікувані витрати автопарку з урахуванням обмежень:
  - місткість сервісу: не більше N автомобілів на день (кількість постів / механіків), неділя - вихідний;
  - автомобіль не можна ставити на ТО в дні, на які йому видано путівку (рейс);
  - ризик відмови кожного авто - з моделі прогнозу несправностей.

Вартість призначення автомобіля i на день d:
    C(i, d) = P_відм(i, d) * C_відм                   - відмова до ТО (ремонт, евакуація, простій)
            + max(0, T_i - d) / T_інт * C_ТО          - «недовикористаний» ресурс при надто ранньому ТО
            + max(0, d - T_i) * C_простр              - кожен день прострочення ТО
де T_i - день, на який припадає ТО за календарем/пробігом, P_відм - імовірність відмови до дня d
(інтенсивність відмов з ML-прогнозу, яка зростає після строку ТО).

Мінімум суми C(i, d) з обмеженням місткості - це задача про призначення: кожен день розбивається
на N «місць», додається варіант «перенести за межі горизонту». Розв'язується точно угорським
алгоритмом (scipy.optimize.linear_sum_assignment). Для порівняння будується «наївний» план:
автомобілі ставляться на ТО в порядку строку, на перший вільний день не раніше строку.
"""
import math
from datetime import datetime, timedelta

from bson import ObjectId

DEFAULTS = {'horizon_days': 21, 'failure_cost': 30000, 'maintenance_cost': 6000, 'overdue_day_cost': 400}
OVERDUE_HAZARD_GROWTH = 0.05      # +5 % до інтенсивності відмов за кожен день прострочення
FRESH_RISK_30D = 0.03             # ризик відмови за 30 днів одразу після ТО (ТО не робить авто «вічним»)
WORKSHOP_DAYS_OFF = {6}           # неділя
BIG = 1e9
OIL_LITERS = {True: 30, False: 6}  # заміна оливи: вантажівка / легкий автомобіль


def _as_dt(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00')).replace(tzinfo=None)
        except ValueError:
            return None
    return None


def _days(db, start, horizon, bays):
    days = []
    for k in range(horizon):
        d = start + timedelta(days=k)
        days.append({'date': d, 'capacity': 0 if d.weekday() in WORKSHOP_DAYS_OFF else bays})
    return days


def _blocked(db, vehicle_ids, start, end):
    """Дні рейсів: {vehicle_id: {(day_index): номер путівки}}."""
    out = {}
    for w in db.waybills.find({'vehicle_id': {'$in': vehicle_ids}, 'status': {'$in': ['issued', 'active']},
                               'valid_until': {'$gte': start}, 'valid_from': {'$lt': end}}):
        a, b = _as_dt(w.get('valid_from')), _as_dt(w.get('valid_until'))
        if not a or not b:
            continue
        k = max(0, (a.replace(hour=0, minute=0, second=0, microsecond=0) - start).days)
        while start + timedelta(days=k) <= b and start + timedelta(days=k) < end:
            out.setdefault(w['vehicle_id'], {})[k] = w.get('number')
            k += 1
    return out


def _hazard(p30):
    return -math.log(max(1e-6, 1 - min(p30, 0.95))) / 30


def _fail_prob(p30, due, d, excess=False):
    """
    Імовірність відмови до дня d: інтенсивність з 30-денного прогнозу, після строку ТО зростає.
    excess=True - лише та частина ризику, яку усуває ТО (понад ризик щойно обслуженого авто).
    """
    h, h0 = _hazard(p30), (_hazard(FRESH_RISK_30D) if excess else 0.0)
    total = 0.0
    for t in range(max(0, d)):
        total += max(0.0, h * (1 + OVERDUE_HAZARD_GROWTH * max(0, t - due)) - h0)
    return 1 - math.exp(-total)


def _cost(c, d, params, interval_days):
    fail = _fail_prob(c['risk'], c['due_day'], d)
    avoidable = _fail_prob(c['risk'], c['due_day'], d, excess=True)
    early = max(0, c['due_day'] - d) / interval_days * params['maintenance_cost']
    overdue = max(0, d - max(c['due_day'], 0)) * params['overdue_day_cost']
    return {'total': avoidable * params['failure_cost'] + early + overdue, 'fail_prob': fail,
            'avoidable': avoidable, 'early_cost': early, 'overdue_cost': overdue}


def _postpone_cost(c, params, interval_days, horizon):
    """Вартість перенесення ТО за межі горизонту (ТО у свій строк, але не раніше кінця горизонту)."""
    base = _cost(c, max(horizon, c['due_day']), params, interval_days)
    penalty = params['overdue_day_cost'] * 7 if c['due_day'] < horizon else 0   # потрібне було в горизонті
    return {**base, 'total': base['total'] + penalty}


def candidates(db, start, horizon, settings):
    """Автомобілі, яким потрібне ТО в межах горизонту (+2 тижні) або з підвищеним ризиком відмови."""
    from services.maintenance_forecast import daily_mileage
    from services.predictive_maintenance import fleet_risk, LEVEL_MEDIUM
    interval_km = float(settings.get('maintenance_interval_km') or 10000)
    vehicles = list(db.vehicles.find({'status': 'active'}))
    ids = [str(v['_id']) for v in vehicles]
    daily = daily_mileage(db, vehicle_ids=ids)
    risk = {i['vehicle_id']: i for i in fleet_risk(db).get('items', [])}
    planned = {r['vehicle_id']: r for r in db.repairs.find({'vehicle_id': {'$in': ids}, 'repair_type': 'maintenance',
                                                            'status': {'$in': ['planned', 'in_progress']}})}
    out, fixed = [], []
    for v in vehicles:
        vid = str(v['_id'])
        if vid in planned:
            r = planned[vid]
            sd = _as_dt(r.get('scheduled_date'))
            fixed.append({'vehicle_id': vid, 'plate': v.get('plate_number'), 'repair_id': str(r['_id']),
                          'number': r.get('number'), 'day': (sd - start).days if sd else None,
                          'date': sd})
            continue
        by_date = _as_dt(v.get('next_maintenance_date'))
        km_left = (v.get('next_maintenance_km') or 0) - (v.get('odometer') or 0) if v.get('next_maintenance_km') else None
        by_km = None
        if km_left is not None:
            per_day = daily.get(vid) or 0
            by_km = start if km_left <= 0 else (start + timedelta(days=math.ceil(km_left / per_day)) if per_day > 0 else None)
        options = [d for d in (by_date, by_km) if d]
        if not options:
            continue
        due = min(options)
        due_day = (due.replace(hour=0, minute=0, second=0, microsecond=0) - start).days
        r = risk.get(vid, {})
        p = r.get('probability', 0.05)
        if due_day > horizon + 14 and p < LEVEL_MEDIUM:
            continue
        out.append({
            'vehicle_id': vid, 'plate': v.get('plate_number'),
            'vehicle_label': f"{v.get('plate_number')} {v.get('brand', '')} {v.get('model', '')}".strip(),
            'heavy': (v.get('fuel_norm') or 0) >= 20,
            'due_day': due_day, 'due_date': due, 'due_basis': 'mileage' if due is by_km and by_km != by_date else 'date',
            'km_left': km_left, 'risk': p, 'risk_level': r.get('level', 'low'),
            'recommendation': r.get('recommendation'),
        })
    return out, fixed


def _naive(cands, days, blocked, used):
    """Наївний план: у порядку строку ТО, на перший вільний день не раніше строку (ризик не враховується)."""
    load = list(used)
    plan = {}
    for c in sorted(cands, key=lambda c: (c['due_day'], c['plate'])):
        d = max(0, c['due_day'])
        while d < len(days) and (load[d] >= days[d]['capacity'] or d in blocked.get(c['vehicle_id'], {})):
            d += 1
        if d < len(days):
            plan[c['vehicle_id']] = d
            load[d] += 1
        else:
            plan[c['vehicle_id']] = None
    return plan


def _evaluate(cands, plan, params, interval_days, horizon):
    m = {'cost': 0.0, 'expected_failures': 0.0, 'overdue_days': 0, 'early_days': 0, 'scheduled': 0, 'postponed': 0,
         'high_risk_wait_days': 0}
    for c in cands:
        d = plan.get(c['vehicle_id'])
        day = d if d is not None else max(horizon, c['due_day'])
        cost = _cost(c, day, params, interval_days) if d is not None else _postpone_cost(c, params, interval_days, horizon)
        m['cost'] += cost['total']
        m['expected_failures'] += cost['fail_prob']
        m['overdue_days'] += max(0, day - max(c['due_day'], 0))
        if d is not None:
            m['scheduled'] += 1
            m['early_days'] += max(0, c['due_day'] - d)
            if c['risk_level'] == 'high':
                m['high_risk_wait_days'] += d
        else:
            m['postponed'] += 1
    m['cost'] = round(m['cost'])
    m['expected_failures'] = round(m['expected_failures'], 2)
    return m


def optimize(db, horizon_days=None, bays=None, failure_cost=None, now=None):
    from scipy.optimize import linear_sum_assignment
    import numpy as np

    settings = db.settings.find_one({'_id': 'system'}) or {}
    interval_days = float(settings.get('maintenance_interval_days') or 180)
    mechanics = db.users.count_documents({'role': 'mechanic', 'is_active': True})
    params = dict(DEFAULTS)
    params['horizon_days'] = int(horizon_days or DEFAULTS['horizon_days'])
    params['bays'] = int(bays or max(1, mechanics))
    if failure_cost:
        params['failure_cost'] = float(failure_cost)
    now = now or datetime.utcnow()
    start = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    horizon = params['horizon_days']
    end = start + timedelta(days=horizon)

    cands, fixed = candidates(db, start, horizon, settings)
    days = _days(db, start, horizon, params['bays'])
    used = [0] * horizon
    for f in fixed:
        if f['day'] is not None and 0 <= f['day'] < horizon:
            used[f['day']] += 1
    blocked = _blocked(db, [c['vehicle_id'] for c in cands], start, end)

    # матриця вартостей: рядки - автомобілі, стовпці - вільні місця (день, пост) + «перенести» для кожного авто
    slots = [k for k in range(horizon) for _ in range(max(0, days[k]['capacity'] - used[k]))]
    n, m = len(cands), len(slots)
    cost = np.full((n, m + n), BIG)
    for i, c in enumerate(cands):
        for j, k in enumerate(slots):
            if k not in blocked.get(c['vehicle_id'], {}):
                cost[i, j] = _cost(c, k, params, interval_days)['total']
        # перенесення за горизонт: ТО у свій строк, але не раніше кінця горизонту
        cost[i, m + i] = _postpone_cost(c, params, interval_days, horizon)['total']
    plan = {}
    if n:
        rows, cols = linear_sum_assignment(cost)
        for i, j in zip(rows, cols):
            plan[cands[i]['vehicle_id']] = slots[j] if j < m else None
    naive = _naive(cands, days, blocked, used)

    items = []
    for c in cands:
        d, nd = plan.get(c['vehicle_id']), naive.get(c['vehicle_id'])
        conflicts = blocked.get(c['vehicle_id'], {})
        cst = _cost(c, d if d is not None else max(horizon, c['due_day']), params, interval_days)
        items.append({
            'vehicle_id': c['vehicle_id'], 'plate': c['plate'], 'vehicle_label': c['vehicle_label'],
            'due_date': c['due_date'], 'due_day': c['due_day'], 'due_basis': c['due_basis'], 'km_left': c['km_left'],
            'risk': round(c['risk'], 3), 'risk_level': c['risk_level'],
            'day': d, 'date': start + timedelta(days=d) if d is not None else None,
            'naive_day': nd, 'naive_date': start + timedelta(days=nd) if nd is not None else None,
            'shift_days': (d - max(c['due_day'], 0)) if d is not None else None,
            'trip_days': sorted(conflicts), 'trips': sorted(set(conflicts.values())),
            'fail_prob': round(cst['fail_prob'], 3), 'reason': _reason(c, d, conflicts, horizon),
        })
    items.sort(key=lambda x: (x['day'] if x['day'] is not None else 999, -x['risk']))

    planned_n = sum(1 for i in items if i['day'] is not None)
    oil = sum(OIL_LITERS[c['heavy']] for c in cands if plan.get(c['vehicle_id']) is not None)
    stock_filters = sum(p.get('quantity', 0) for p in db.parts.find({'name': {'$regex': 'Фільтр масляний'}}))
    stock_oil = sum(p.get('quantity', 0) for p in db.parts.find({'name': {'$regex': 'Олива моторна'}}))
    load = [used[k] + sum(1 for i in items if i['day'] == k) for k in range(horizon)]
    return {
        'params': {**params, 'mechanics': mechanics, 'start': start, 'end': end - timedelta(days=1)},
        'items': items,
        'fixed': [{**f, 'date': f['date']} for f in fixed],
        'days': [{'date': d['date'], 'capacity': d['capacity'], 'load': load[k], 'fixed': used[k]} for k, d in enumerate(days)],
        'optimized': _evaluate(cands, plan, params, interval_days, horizon),
        'naive': _evaluate(cands, naive, params, interval_days, horizon),
        'parts': {'filters_needed': planned_n, 'filters_stock': stock_filters,
                  'oil_needed': oil, 'oil_stock': stock_oil},
    }


def _reason(c, d, conflicts, horizon):
    if d is None:
        return ('Строк ТО за межами горизонту - планувати пізніше.' if c['due_day'] >= horizon
                else 'Немає вільних місць у сервісі - збільште кількість постів або горизонт.')
    shift = d - max(c['due_day'], 0)
    parts = []
    if c['due_day'] < 0:
        parts.append(f"ТО прострочене на {-c['due_day']} дн. - ставимо першочергово.")
    elif shift < 0 and c['risk'] >= 2.5 * FRESH_RISK_30D:
        parts.append(f"Ризик відмови {round(c['risk'] * 100)} % - ТО на {-shift} дн. раніше строку.")
    elif shift < 0:
        parts.append(f'На {-shift} дн. раніше строку - рівномірне завантаження сервісу.')
    elif shift > 0:
        parts.append(f'На {shift} дн. пізніше строку - низький ризик, звільняємо місце для ризикованіших.')
    else:
        parts.append('У строк.')
    if conflicts and any(abs(k - d) <= 2 for k in conflicts):
        parts.append('Враховано рейс: ' + ', '.join(sorted(set(conflicts.values()))) + '.')
    return ' '.join(parts)


def apply_plan(db, items, user):
    """Створює заплановані ТО (ремонти типу «maintenance») для обраних рядків плану."""
    from services.doc_generator import generate_doc_number
    mechanics = [str(u['_id']) for u in db.users.find({'role': 'mechanic', 'is_active': True}).sort('full_name', 1)]
    created = []
    for k, it in enumerate(items):
        try:
            vehicle = db.vehicles.find_one({'_id': ObjectId(it['vehicle_id'])})
            date = datetime.fromisoformat(str(it['date'])[:10])
        except Exception:  # noqa: BLE001
            continue
        if not vehicle or db.repairs.find_one({'vehicle_id': it['vehicle_id'], 'repair_type': 'maintenance',
                                               'status': {'$in': ['planned', 'in_progress']}}):
            continue
        number = generate_doc_number(db, 'repair')
        now = datetime.utcnow()
        res = db.repairs.insert_one({
            'number': number, 'vehicle_id': it['vehicle_id'],
            'mechanic_id': mechanics[k % len(mechanics)] if mechanics else str(user['_id']),
            'fault_id': None, 'repair_type': 'maintenance',
            'description': 'Планове ТО (оптимізований графік)', 'scheduled_date': date,
            'started_at': None, 'completed_at': None, 'odometer': vehicle.get('odometer'), 'status': 'planned',
            'work_performed': None, 'parts_used': [], 'labor_hours': None, 'labor_cost': None, 'parts_cost': None,
            'notes': None, 'cancellation_reason': None, 'created_by': str(user['_id']), 'created_at': now, 'updated_at': now,
        })
        created.append({'repair_id': str(res.inserted_id), 'number': number, 'vehicle_id': it['vehicle_id'],
                        'date': date})
    return created
