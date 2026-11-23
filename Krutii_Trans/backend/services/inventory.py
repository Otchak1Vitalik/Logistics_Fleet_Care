"""
Облік запчастин: списання при ремонті, надходження, контроль мінімального залишку.
"""
from datetime import datetime, timedelta

from bson import ObjectId
from bson.errors import InvalidId

from services.alert_engine import create_alert


class InventoryError(ValueError):
    """Помилка списання (невідома запчастина або недостатній залишок)."""


def _fmt(q):
    return int(q) if float(q).is_integer() else round(q, 2)


def consume_parts(db, items, repair_id, user_id):
    """
    Списує запчастини, використані в ремонті.
    Спочатку перевіряються всі позиції, і лише потім змінюються залишки,
    тож за помилки склад не змінюється частково.
    Повертає (перелік використаних запчастин, загальна вартість).
    """
    needed = {}
    for item in items or []:
        try:
            pid = ObjectId(str(item.get('part_id')))
            qty = float(item.get('quantity'))
        except (InvalidId, TypeError, ValueError):
            raise InventoryError('Невірні дані про запчастини.')
        if qty <= 0:
            raise InventoryError('Кількість запчастин має бути більше 0.')
        needed[pid] = needed.get(pid, 0) + qty
    if not needed:
        return [], 0.0

    parts = {p['_id']: p for p in db.parts.find({'_id': {'$in': list(needed)}})}
    for pid, qty in needed.items():
        part = parts.get(pid)
        if not part:
            raise InventoryError('Запчастину не знайдено.')
        if part.get('quantity', 0) < qty:
            raise InventoryError(
                f'Недостатньо запчастини «{part["name"]}»: на складі {_fmt(part.get("quantity", 0))} '
                f'{part.get("unit", "шт")}, потрібно {_fmt(qty)}.'
            )

    used, total = [], 0.0
    now = datetime.utcnow()
    for pid, qty in needed.items():
        part = parts[pid]
        # Умова в запиті захищає від одночасного списання тієї ж позиції
        res = db.parts.update_one({'_id': pid, 'quantity': {'$gte': qty}},
                                  {'$inc': {'quantity': -qty}, '$set': {'updated_at': now}})
        if res.modified_count != 1:
            raise InventoryError(f'Недостатньо запчастини «{part["name"]}».')
        cost = round(qty * part.get('price', 0), 2)
        total += cost
        db.part_movements.insert_one({
            'part_id': str(pid), 'type': 'out', 'quantity': qty, 'price': part.get('price', 0),
            'repair_id': repair_id, 'user_id': user_id, 'created_at': now,
        })
        used.append({'part_id': str(pid), 'name': part['name'], 'unit': part.get('unit', 'шт'),
                     'quantity': qty, 'price': part.get('price', 0), 'cost': cost})
        check_low_stock(db, db.parts.find_one({'_id': pid}))
    return used, round(total, 2)


def receive_part(db, part, quantity, price, user_id, note=None):
    """Надходження запчастини на склад."""
    now = datetime.utcnow()
    update = {'$inc': {'quantity': quantity}, '$set': {'updated_at': now}}
    if price is not None:
        update['$set']['price'] = price
    db.parts.update_one({'_id': part['_id']}, update)
    db.part_movements.insert_one({
        'part_id': str(part['_id']), 'type': 'in', 'quantity': quantity,
        'price': price if price is not None else part.get('price', 0),
        'note': note, 'user_id': user_id, 'created_at': now,
    })
    # Залишок поповнено - знімаємо попередження про нестачу
    if part.get('quantity', 0) + quantity > part.get('min_quantity', 0):
        db.alerts.update_many(
            {'related_type': 'part', 'related_id': str(part['_id']), 'is_dismissed': False},
            {'$set': {'is_dismissed': True, 'dismissed_at': now}})


def check_low_stock(db, part):
    """Попередження механікам і керівнику, якщо залишок не перевищує мінімуму (не частіше разу на добу)."""
    if not part or part.get('quantity', 0) > part.get('min_quantity', 0):
        return False
    pid = str(part['_id'])
    recent = db.alerts.find_one({
        'related_type': 'part', 'related_id': pid, 'is_dismissed': False,
        'created_at': {'$gte': datetime.utcnow() - timedelta(days=1)},
    })
    if recent:
        return False
    title = f'Закінчується запчастина: {part["name"]}'
    message = f'Залишок: {_fmt(part.get("quantity", 0))} {part.get("unit", "шт")} (мінімум {_fmt(part.get("min_quantity", 0))}).'
    for role in ('mechanic', 'manager'):
        create_alert(db, alert_type='warning', category='parts', title=title, message=message,
                     recipient_role=role, related_type='part', related_id=pid)
    return True
