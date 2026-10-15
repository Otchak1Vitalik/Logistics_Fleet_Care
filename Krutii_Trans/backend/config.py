"""
Конфігурація системи KRUTII TRANS
"""
import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class Config:
    # MongoDB
    MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/bogatur')

    # JWT
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'bogatur-secret-key-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)
    JWT_TOKEN_LOCATION = ['cookies']
    JWT_COOKIE_SECURE = False  # True в production з HTTPS
    JWT_COOKIE_CSRF_PROTECT = False  # Спростимо для розробки
    JWT_COOKIE_SAMESITE = 'Lax'
    JWT_ACCESS_COOKIE_PATH = '/'  # Cookie доступний для всіх шляхів
    JWT_REFRESH_COOKIE_PATH = '/'
    JWT_ACCESS_COOKIE_NAME = 'access_token_cookie'

    # Rate Limiting
    RATELIMIT_DEFAULT = "500/minute"
    RATELIMIT_STORAGE_URL = "memory://"

    # CORS
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:5173,http://localhost:3000').split(',')


# Константи системи
class Constants:
    # Ролі користувачів
    ROLES = {
        'manager': 'Керівник',
        'mechanic': 'Механік',
        'driver': 'Водій'
    }

    # Серії документів
    DOC_SERIES = {
        'waybill': 'ПЛ',      # Путівка (Подорожній Лист)
        'fault': 'НС',         # Несправність
        'repair': 'РМ',        # Ремонт
        'fuel_invoice': 'НП'   # Накладна Паливна
    }

    # Статуси путівок
    WAYBILL_STATUSES = {
        'issued': 'Видано',
        'active': 'Активна',
        'completed': 'Завершена',
        'cancelled': 'Скасована'
    }

    # Статуси ремонтів
    REPAIR_STATUSES = {
        'planned': 'Заплановано',
        'in_progress': 'В роботі',
        'completed': 'Завершено',
        'cancelled': 'Скасовано'
    }

    # Статуси несправностей
    FAULT_STATUSES = {
        'new': 'Нова',
        'acknowledged': 'Прийнято',
        'in_repair': 'В ремонті',
        'resolved': 'Вирішено',
        'rejected': 'Відхилено'
    }

    # Статуси транспорту
    VEHICLE_STATUSES = {
        'active': 'Активний',
        'repair': 'В ремонті',
        'inspection': 'На огляді',
        'decommissioned': 'Списано'
    }

    # Типи сповіщень
    ALERT_TYPES = {
        'info': 'Інформація',
        'warning': 'Попередження',
        'critical': 'Критично'
    }

    # Паливні норми (за замовчуванням)
    DEFAULT_FUEL_NORM = 25.0  # л/100км
    OVERSPEND_THRESHOLD = 10  # відсоток перевитрати

    # Сезонні коефіцієнти
    SEASON_COEFFICIENTS = {
        'summer': 1.0,
        'winter': 1.09  # місяці 11, 12, 1, 2, 3
    }
    WINTER_MONTHS = [11, 12, 1, 2, 3]

    # Пороги ТО
    MAINTENANCE_WARNING_KM = 1000  # км до ТО
    MAINTENANCE_WARNING_DAYS = 14  # днів до ТО

    # Ескалація (в годинах)
    FAULT_MECHANIC_ESCALATION = 4   # години без відповіді - сповіщення механіку
    FAULT_MANAGER_ESCALATION = 24   # години без відповіді - сповіщення керівнику
