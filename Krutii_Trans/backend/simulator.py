"""
Симулятор телематики: «прикидається» GPS-трекерами автомобілів автопарку і надсилає їхні дані
в систему так само, як справжні трекери - POST /api/telematics/ingest з ключем пристрою.

  - автомобілі з активними путівками їдуть маршрутом путівки трасами України
    (з прискоренням часу), заправляються, коли пального мало, після прибуття повертаються назад;
  - решта автомобілів стоїть на базі (трекер періодично надсилає стан із вимкненим двигуном);
  - час від часу відтворюються несправності й порушення: перегрів двигуна, код помилки,
    розряд акумулятора, злив пального, рух без путівки - система має їх помітити.

Запуск (з папки backend, коли запущено сервер app.py):
    venv\\Scripts\\python.exe simulator.py
Параметри:
    --speed 30        у скільки разів швидше реального часу рухаються машини (за замовчуванням 30)
    --interval 2      як часто (с) трекери надсилають дані
    --no-incidents    без несправностей і порушень
    --api URL         адреса сервера (за замовчуванням http://localhost:5001)
Зупинка - Ctrl+C.
"""
import argparse
import json
import math
import os
import random
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

from pymongo import MongoClient

from config import Config
from services import telematics as tm
from services.geo_ukraine import CITIES, DEPOT, bearing, haversine, route_points

INCIDENT_EVERY = 75          # с реального часу між подіями
PARKED_REPORT_EVERY = 30     # стоянка: трекер надсилає дані рідше


def lerp(a, b, t):
    return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]


class Truck:
    def __init__(self, v, key, rnd):
        self.id = str(v['_id'])
        self.plate = v['plate_number']
        self.key = key
        self.rnd = rnd
        self.heavy = (v.get('fuel_norm') or 0) >= 20
        self.norm = v.get('fuel_norm') or (28 if self.heavy else 10)
        self.tank = v.get('tank_capacity') or (400 if self.heavy else 70)
        self.odometer = float(v.get('odometer') or 100000)
        self.fuel = self.tank * rnd.uniform(0.45, 0.9)
        self.temp = 20.0
        self.volts_on, self.volts_off = (27.8, 25.0) if self.heavy else (14.1, 12.6)
        self.volts = self.volts_off
        self.volts_drop = 2.4 if self.heavy else 1.3      # розряд акумулятора
        self.cruise = rnd.uniform(72, 85) if self.heavy else rnd.uniform(85, 100)
        self.speed = 0.0
        self.route, self.seg, self.seg_pos = None, 0, 0.0
        self.pos = list(CITIES[DEPOT])
        self.pos = [self.pos[0] + rnd.uniform(-0.03, 0.03), self.pos[1] + rnd.uniform(-0.03, 0.03)]
        self.heading = 0.0
        self.stop_ticks = 0        # вимушена зупинка (заправка, перегрів, «злив»)
        self.park_ticks = 0        # стоянка після прибуття
        self.dtc = set()
        self.overheating = False
        self.battery_fault = False
        self.joyride = 0
        self.pending_drain = 0.0
        self.last_sent = 0.0

    # ---------------------------------------------------------------- маршрут
    def set_route(self, origin, destination, progress=0.0):
        pts, _ = route_points(origin, destination)
        if not pts or len(pts) < 2:
            return False
        self.route, self.dest = pts, destination
        lens = [haversine(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
        target = sum(lens) * progress
        self.seg = 0
        while self.seg < len(lens) - 1 and target > lens[self.seg]:
            target -= lens[self.seg]
            self.seg += 1
        self.seg_pos = target
        self.pos = lerp(pts[self.seg], pts[self.seg + 1], self.seg_pos / lens[self.seg])
        return True

    @property
    def driving(self):
        return (self.route is not None or self.joyride > 0) and self.stop_ticks == 0 and self.park_ticks == 0

    # ---------------------------------------------------------------- один крок
    def step(self, dt_sim):
        hours = dt_sim / 3600
        if self.driving:
            limit = self.cruise
            if self.route:
                a, b = self.route[self.seg], self.route[self.seg + 1]
                seg_len = haversine(a, b)
                left = seg_len - self.seg_pos
                if left < 4 or self.seg_pos < 4:
                    limit = 50                                     # населений пункт
            self.speed += (limit - self.speed) * 0.5 + self.rnd.gauss(0, 2)
            self.speed = max(5.0, min(self.speed, 110.0))
            km = self.speed * hours
            if self.route:
                self._advance(km)
            else:                                                  # «покатушки» без путівки біля бази
                self.heading = (self.heading + self.rnd.uniform(-25, 25)) % 360
                rad = math.radians(self.heading)
                self.pos = [self.pos[0] + km / 111 * math.cos(rad), self.pos[1] + km / 71 * math.sin(rad)]
                self.joyride -= 1
            self.odometer += km
            self.fuel = max(0.0, self.fuel - km / 100 * self.norm * self.rnd.uniform(0.95, 1.1))
            target = 112.0 if self.overheating else 88.0
            self.temp += (target - self.temp) * (0.08 if self.overheating else 0.3) + self.rnd.gauss(0, 0.6)
            self.volts = (self.volts_off - self.volts_drop if self.battery_fault else self.volts_on) + self.rnd.gauss(0, 0.05)
            if self.fuel < self.tank * 0.15 and self.route:
                self.stop_ticks = 6                               # заїзд на АЗС
                self.refuel_after = True
        else:
            self.speed = 0.0
            ambient = 8.0
            self.temp += (ambient - self.temp) * 0.02
            self.volts = (self.volts_off - (self.volts_drop if self.battery_fault else 0)) + self.rnd.gauss(0, 0.03)
            if self.pending_drain and self.stop_ticks <= 3:
                self.fuel = max(0.0, self.fuel - self.pending_drain)
                self.pending_drain = 0.0
            if self.stop_ticks:
                self.stop_ticks -= 1
                if self.stop_ticks == 0 and getattr(self, 'refuel_after', False):
                    self.fuel = self.tank * self.rnd.uniform(0.88, 0.97)
                    self.refuel_after = False
                if self.stop_ticks == 0 and self.overheating:      # охолонув, водій поїхав далі
                    self.overheating = False
            elif self.park_ticks:
                self.park_ticks -= 1
                if self.park_ticks == 0 and getattr(self, 'next_route', None):
                    self.set_route(*self.next_route)
                    self.next_route = None
        if self.overheating and self.temp >= 106 and self.driving:
            self.dtc.add('P0217')
            self.stop_ticks = 25                                  # водій зупиняється, двигун охолоджується

    def _advance(self, km):
        while km > 0 and self.route:
            a, b = self.route[self.seg], self.route[self.seg + 1]
            seg_len = haversine(a, b)
            step = min(km, seg_len - self.seg_pos)
            self.seg_pos += step
            km -= step
            self.heading = bearing(a, b)
            if self.seg_pos >= seg_len - 1e-6:
                if self.seg + 2 < len(self.route):
                    self.seg += 1
                    self.seg_pos = 0.0
                else:                                             # прибули: стоянка, потім рейс назад
                    self.pos = list(b)
                    origin = next(c for c, xy in CITIES.items() if list(xy) == list(self.route[0]))
                    self.next_route = (self.dest, origin)
                    self.route = None
                    self.park_ticks = 40
                    return
        if self.route:
            a, b = self.route[self.seg], self.route[self.seg + 1]
            self.pos = lerp(a, b, self.seg_pos / max(haversine(a, b), 1e-6))

    def point(self):
        moving = self.speed > 0
        return {
            'ts': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            'lat': round(self.pos[0], 6), 'lon': round(self.pos[1], 6),
            'speed': round(self.speed, 1), 'heading': round(self.heading, 1),
            'odometer': round(self.odometer, 2), 'fuel_level': round(self.fuel, 1),
            'engine_temp': round(self.temp, 1), 'battery_v': round(self.volts, 2),
            'rpm': round(900 + self.speed * 14 + self.rnd.gauss(0, 30)) if moving else 0,
            'ignition': moving or self.stop_ticks > 0 and not self.park_ticks, 'dtc': sorted(self.dtc),
        }


def send(api, truck, points):
    req = urllib.request.Request(api.rstrip('/') + '/api/telematics/ingest',
                                 data=json.dumps({'points': points}).encode(), method='POST',
                                 headers={'Content-Type': 'application/json', 'X-Device-Key': truck.key})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())


def incident(trucks, rnd):
    """Випадкова несправність або порушення. Повертає опис для консолі."""
    driving = [t for t in trucks if t.route and t.driving]
    parked = [t for t in trucks if not t.route and not t.joyride]
    kinds = []
    if driving:
        kinds += ['overheat', 'dtc', 'drain']
    if parked:
        kinds += ['battery', 'joyride']
    if not kinds:
        return None
    kind = rnd.choice(kinds)
    if kind == 'overheat':
        t = rnd.choice(driving)
        t.overheating = True
        return f'{t.plate}: перегрів двигуна (температура почне рости)'
    if kind == 'dtc':
        t = rnd.choice(driving)
        code = rnd.choice(['P0087', 'P0300', 'P0401', 'P2463', 'P0128'])
        t.dtc.add(code)
        return f'{t.plate}: код помилки {code}'
    if kind == 'drain':
        t = rnd.choice(driving)
        t.stop_ticks = 8
        t.pending_drain = min(t.fuel * 0.6, max(t.tank * 0.15, 40 if t.heavy else 15))
        return f'{t.plate}: зупинка і злив ~{t.pending_drain:.0f} л пального'
    if kind == 'battery':
        t = rnd.choice(parked)
        t.battery_fault = True
        return f'{t.plate}: розряд акумулятора на стоянці'
    t = rnd.choice(parked)
    t.joyride = 25
    return f'{t.plate}: рух без путівки'


def main():
    ap = argparse.ArgumentParser(description='Симулятор телематики KRUTII TRANS')
    ap.add_argument('--api', default=os.getenv('SIMULATOR_API', 'http://localhost:5001'))
    ap.add_argument('--speed', type=float, default=30.0)
    ap.add_argument('--interval', type=float, default=2.0)
    ap.add_argument('--no-incidents', action='store_true')
    ap.add_argument('--seed', type=int, default=None)
    ap.add_argument('--incident-every', type=float, default=INCIDENT_EVERY, help='с між сценаріями несправностей')
    args = ap.parse_args()
    rnd = random.Random(args.seed)

    db = MongoClient(Config.MONGO_URI).get_database()
    vehicles = list(db.vehicles.find({'status': {'$ne': 'decommissioned'}}).sort('plate_number', 1))
    if not vehicles:
        sys.exit('У базі немає автомобілів. Спочатку запустіть seed.py.')
    # «встановлення трекерів»: кожному авто - ключ пристрою (як це зробив би керівник у системі)
    trucks = [Truck(v, tm.provision(db, str(v['_id'])), rnd) for v in vehicles]
    by_id = {t.id: t for t in trucks}
    for w in db.waybills.find({'status': 'active'}):
        t = by_id.get(w['vehicle_id'])
        if t and t.set_route(w.get('route_from'), w.get('route_to'), progress=rnd.uniform(0.05, 0.5)):
            print(f"  {t.plate}: рейс {w.get('number')} {w.get('route_from')} -> {w.get('route_to')}")
    # авто на стоянці - на базі або в місті останнього рейсу
    for t in trucks:
        if not t.route:
            last = db.waybills.find_one({'vehicle_id': t.id, 'status': 'completed'}, sort=[('completed_at', -1)])
            city = (last or {}).get('route_to') if (last or {}).get('route_to') in CITIES else DEPOT
            base = CITIES[city]
            t.pos = [base[0] + rnd.uniform(-0.02, 0.02), base[1] + rnd.uniform(-0.02, 0.02)]
    # продовжуємо з останнього відомого стану (як справжній трекер після перезапуску):
    # інакше «новий» рівень пального система сприйняла б як злив або заправку
    for s in db.telematics_state.find():
        t = by_id.get(s['_id'])
        if not t:
            continue
        if s.get('fuel_level') is not None:
            t.fuel = float(s['fuel_level'])
        if s.get('engine_temp') is not None:
            t.temp = float(s['engine_temp'])
        if not t.route and s.get('lat') is not None:
            t.pos = [s['lat'], s['lon']]

    print(f'\nСимулятор телематики: {len(trucks)} трекерів, у рейсі {sum(1 for t in trucks if t.route)}, '
          f'прискорення x{args.speed:g}, дані кожні {args.interval:g} с. Зупинка - Ctrl+C.\n')
    next_incident = time.time() + (min(30, args.incident_every) if not args.no_incidents else 1e12)
    errors = 0
    try:
        while True:
            started = time.time()
            for t in trucks:
                t.step(args.interval * args.speed)
                quiet = not t.driving and t.stop_ticks == 0
                if quiet and started - t.last_sent < PARKED_REPORT_EVERY:
                    continue
                try:
                    res = send(args.api, t, [t.point()])
                    t.last_sent = started
                    errors = 0
                    for ev in res.get('events', []):
                        print(f'  [система] {t.plate}: подія «{tm.EVENT_LABELS.get(ev, ev)}»')
                except urllib.error.HTTPError as exc:
                    errors += 1
                    if errors in (1, 10) or errors % 50 == 0:
                        if exc.code == 404:
                            print('  Сервер працює зі старою версією коду (немає /api/telematics). Перезапустіть app.py.')
                        elif exc.code == 401:
                            print('  Сервер не прийняв ключ трекера. Перезапустіть симулятор.')
                        else:
                            print(f'  Помилка сервера: {exc}')
                    if exc.code in (404, 401):
                        break
                except (urllib.error.URLError, OSError) as exc:
                    errors += 1
                    if errors in (1, 10) or errors % 50 == 0:
                        print(f'  Сервер недоступний ({exc}). Чи запущено app.py на {args.api}?')
                    break
            if started >= next_incident:
                desc = incident(trucks, rnd)
                if desc:
                    print(f'* Сценарій: {desc}')
                next_incident = started + args.incident_every * rnd.uniform(0.7, 1.3)
            time.sleep(max(0.0, args.interval - (time.time() - started)))
    except KeyboardInterrupt:
        print('\nСимулятор зупинено.')


if __name__ == '__main__':
    main()
