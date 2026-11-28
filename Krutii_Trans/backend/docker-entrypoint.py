"""
Запуск бекенду в Docker: дочекатися MongoDB, за порожньої бази заповнити її демоданими, запустити сервер.
"""
import os
import subprocess
import sys
import time

from pymongo import MongoClient

from config import Config

client = MongoClient(Config.MONGO_URI, serverSelectionTimeoutMS=2000)
for attempt in range(30):
    try:
        client.admin.command('ping')
        break
    except Exception:  # noqa: BLE001 - база ще стартує
        print('Очікуємо MongoDB...', flush=True)
        time.sleep(2)
else:
    sys.exit('MongoDB недоступна.')

if os.getenv('AUTO_SEED', '1') == '1' and client.get_database().users.count_documents({}) == 0:
    print('База порожня - заповнюємо демоданими (seed.py)...', flush=True)
    subprocess.run([sys.executable, 'seed.py'], check=True)

os.execv(sys.executable, [sys.executable, 'app.py'])
