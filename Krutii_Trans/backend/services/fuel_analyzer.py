"""
Аналізатор витрат пального
"""
from datetime import datetime
from config import Constants


def get_season_coefficient(date: datetime = None) -> float:
    """
    Повертає сезонний коефіцієнт для розрахунку норми.

    Зимовий період: листопад - березень (місяці 11, 12, 1, 2, 3)
    Зимовий коефіцієнт: 1.09 (9% збільшення норми)

    Args:
        date: Дата для визначення сезону (за замовчуванням - поточна)

    Returns:
        Сезонний коефіцієнт (1.0 або 1.09)
    """
    if date is None:
        date = datetime.utcnow()

    month = date.month
    if month in Constants.WINTER_MONTHS:
        return Constants.SEASON_COEFFICIENTS['winter']
    return Constants.SEASON_COEFFICIENTS['summer']


def calculate_fuel_norm(distance_km: float, base_norm: float, date: datetime = None) -> float:
    """
    Розраховує нормативні витрати пального.

    Формула: (distance_km / 100) * base_norm * season_coefficient

    Args:
        distance_km: Пройдена відстань в км
        base_norm: Базова норма витрат л/100км
        date: Дата для визначення сезонного коефіцієнта

    Returns:
        Нормативні витрати пального в літрах
    """
    if distance_km <= 0:
        return 0

    coefficient = get_season_coefficient(date)
    return (distance_km / 100) * base_norm * coefficient


def calculate_fuel_consumption(distance_km: float, fuel_used: float, base_norm: float = None) -> float:
    """
    Розраховує фактичні витрати пального на 100 км.

    Args:
        distance_km: Пройдена відстань в км
        fuel_used: Витрачено пального в літрах
        base_norm: Базова норма (не використовується в розрахунку, для сумісності)

    Returns:
        Витрати пального л/100км
    """
    if distance_km <= 0:
        return 0

    return (fuel_used / distance_km) * 100


def check_overspend(actual_consumption: float, base_norm: float, threshold: float = None) -> dict:
    """
    Перевіряє перевитрату пального.

    Args:
        actual_consumption: Фактичні витрати л/100км
        base_norm: Базова норма л/100км
        threshold: Поріг перевитрати у відсотках (за замовчуванням з Constants)

    Returns:
        dict з інформацією про перевитрату
    """
    if threshold is None:
        threshold = Constants.OVERSPEND_THRESHOLD

    if base_norm <= 0:
        return {
            'is_overspend': False,
            'deviation': 0,
            'deviation_percent': 0,
            'message': 'Норма не встановлена'
        }

    deviation = actual_consumption - base_norm
    deviation_percent = (deviation / base_norm) * 100

    is_overspend = deviation_percent > threshold

    if is_overspend:
        message = f'Перевитрата {deviation_percent:.1f}% (поріг {threshold}%)'
    elif deviation_percent > 0:
        message = f'Незначне перевищення {deviation_percent:.1f}%'
    elif deviation_percent < -5:
        message = f'Економія {abs(deviation_percent):.1f}%'
    else:
        message = 'В межах норми'

    return {
        'is_overspend': is_overspend,
        'deviation': round(deviation, 2),
        'deviation_percent': round(deviation_percent, 2),
        'threshold': threshold,
        'message': message
    }


def analyze_waybill_fuel(waybill: dict, vehicle: dict, date: datetime = None) -> dict:
    """
    Аналізує витрати пального по путівці.

    Args:
        waybill: Документ путівки
        vehicle: Документ транспортного засобу
        date: Дата для сезонного коефіцієнта

    Returns:
        dict з повним аналізом
    """
    odometer_start = waybill.get('odometer_start', 0)
    odometer_end = waybill.get('odometer_end', 0)
    fuel_used = waybill.get('fuel_used')

    distance = odometer_end - odometer_start
    base_norm = vehicle.get('fuel_norm', Constants.DEFAULT_FUEL_NORM)

    result = {
        'waybill_number': waybill.get('number'),
        'vehicle_plate': vehicle.get('plate_number'),
        'distance_km': distance,
        'fuel_used': fuel_used,
        'base_norm': base_norm,
        'season_coefficient': get_season_coefficient(date)
    }

    if distance <= 0:
        result['status'] = 'no_distance'
        result['message'] = 'Немає даних про пробіг'
        return result

    if fuel_used is None:
        result['status'] = 'no_fuel_data'
        result['message'] = 'Немає даних про витрати пального'
        return result

    # Розраховуємо
    fuel_norm_recommended = calculate_fuel_norm(distance, base_norm, date)
    actual_consumption = calculate_fuel_consumption(distance, fuel_used)
    overspend_info = check_overspend(actual_consumption, base_norm)

    result.update({
        'status': 'analyzed',
        'fuel_norm_recommended': round(fuel_norm_recommended, 2),
        'actual_consumption_per_100km': round(actual_consumption, 2),
        **overspend_info
    })

    return result


def get_vehicle_fuel_stats(db, vehicle_id: str, limit: int = 20) -> dict:
    """
    Отримує статистику витрат пального для транспортного засобу.

    Args:
        db: MongoDB database instance
        vehicle_id: ID транспортного засобу
        limit: Кількість останніх путівок для аналізу

    Returns:
        dict зі статистикою
    """
    from bson import ObjectId

    vehicle = db.vehicles.find_one({'_id': ObjectId(vehicle_id)})
    if not vehicle:
        return {'error': 'Транспортний засіб не знайдено'}

    waybills = list(db.waybills.find({
        'vehicle_id': vehicle_id,
        'status': 'completed',
        'odometer_end': {'$exists': True},
        'fuel_used': {'$exists': True, '$ne': None}
    }).sort('completed_at', -1).limit(limit))

    if not waybills:
        return {
            'vehicle': {
                '_id': str(vehicle['_id']),
                'plate_number': vehicle['plate_number'],
                'fuel_norm': vehicle.get('fuel_norm', Constants.DEFAULT_FUEL_NORM)
            },
            'total_waybills': 0,
            'message': 'Немає даних для аналізу'
        }

    total_distance = 0
    total_fuel = 0
    overspend_count = 0
    consumptions = []

    for wb in waybills:
        distance = wb.get('odometer_end', 0) - wb.get('odometer_start', 0)
        fuel = wb.get('fuel_used', 0)

        if distance > 0 and fuel > 0:
            total_distance += distance
            total_fuel += fuel

            consumption = calculate_fuel_consumption(distance, fuel)
            consumptions.append(consumption)

            overspend = check_overspend(consumption, vehicle.get('fuel_norm', Constants.DEFAULT_FUEL_NORM))
            if overspend['is_overspend']:
                overspend_count += 1

    avg_consumption = sum(consumptions) / len(consumptions) if consumptions else 0

    return {
        'vehicle': {
            '_id': str(vehicle['_id']),
            'plate_number': vehicle['plate_number'],
            'fuel_norm': vehicle.get('fuel_norm', Constants.DEFAULT_FUEL_NORM)
        },
        'total_waybills': len(waybills),
        'total_distance': total_distance,
        'total_fuel': round(total_fuel, 2),
        'avg_consumption_per_100km': round(avg_consumption, 2),
        'overspend_count': overspend_count,
        'overspend_percentage': round((overspend_count / len(waybills)) * 100, 1) if waybills else 0
    }
