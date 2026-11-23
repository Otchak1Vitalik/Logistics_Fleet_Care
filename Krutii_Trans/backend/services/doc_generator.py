"""
Генератор номерів документів
"""
import random
import string

from config import Constants


def generate_doc_number(db, doc_type: str) -> str:
    """
    Генерує унікальний номер документа.

    Формат: {серія}-{6 цифр}
    Приклади: ПЛ-123456, НС-789012, РМ-345678

    Args:
        db: MongoDB database instance
        doc_type: Тип документа ('waybill', 'fault', 'repair', 'fuel_invoice')

    Returns:
        Унікальний номер документа
    """
    series = Constants.DOC_SERIES.get(doc_type, 'XX')

    # Визначаємо колекцію для перевірки унікальності
    collection_map = {
        'waybill': 'waybills',
        'fault': 'fault_reports',
        'repair': 'repairs',
        'fuel_invoice': 'fuel_invoices'
    }
    collection_name = collection_map.get(doc_type, 'documents')

    max_attempts = 10
    for _ in range(max_attempts):
        # Генеруємо 6 випадкових цифр
        random_digits = ''.join(random.choices(string.digits, k=6))
        doc_number = f'{series}-{random_digits}'

        # Перевіряємо унікальність
        existing = db[collection_name].find_one({'number': doc_number})
        if not existing:
            return doc_number

    # Якщо не вдалося згенерувати за 10 спроб - використовуємо timestamp
    import time
    timestamp_suffix = str(int(time.time()))[-6:]
    return f'{series}-{timestamp_suffix}'


def parse_doc_number(doc_number: str) -> dict:
    """
    Розбирає номер документа на компоненти.

    Args:
        doc_number: Номер документа (напр. "ПЛ-123456")

    Returns:
        dict з series та number
    """
    if not doc_number or '-' not in doc_number:
        return {'series': None, 'number': None}

    parts = doc_number.split('-', 1)
    return {
        'series': parts[0],
        'number': parts[1] if len(parts) > 1 else None
    }


def get_doc_type_by_series(series: str) -> str:
    """
    Визначає тип документа за серією.

    Args:
        series: Серія документа (напр. "ПЛ")

    Returns:
        Тип документа або None
    """
    series_to_type = {v: k for k, v in Constants.DOC_SERIES.items()}
    return series_to_type.get(series)
