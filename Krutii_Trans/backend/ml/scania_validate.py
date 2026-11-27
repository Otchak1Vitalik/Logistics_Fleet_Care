"""
Перевірка методів прогнозу несправностей на реальних даних: «APS Failure at Scania Trucks»
(Scania CV AB, UCI Machine Learning Repository, 2016).

Набір: 60 000 записів для навчання і 16 000 для перевірки, 170 знеособлених показників
пневматичної системи (APS) вантажівок Scania. Клас «pos» - відмова, пов'язана з APS (близько 1.7 %).
Вартість помилок за умовою змагання IDA 2016: хибна тривога (зайвий огляд) - 10, пропущена відмова - 500.

Запуск із папки backend:
    venv\\Scripts\\python.exe -m ml.scania_validate
Скрипт завантажує набір (≈ 56 МБ, у репозиторій не додається), навчає ті самі моделі,
що й для власного автопарку, і зберігає підсумок у assets/ml/scania_report.json -
його показує сторінка «Якість прогнозної моделі».
"""
import csv
import io
import json
import os
import sys
import time
import urllib.request
import zipfile
from datetime import datetime

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sklearn.ensemble import HistGradientBoostingClassifier  # noqa: E402
from sklearn.impute import SimpleImputer  # noqa: E402
from sklearn.inspection import permutation_importance  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.metrics import roc_auc_score  # noqa: E402
from sklearn.model_selection import StratifiedKFold, cross_val_predict  # noqa: E402
from sklearn.pipeline import make_pipeline  # noqa: E402
from sklearn.preprocessing import FunctionTransformer, StandardScaler  # noqa: E402

from services import ml_metrics as mm  # noqa: E402

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE, 'ml', 'data')
REPORT = os.path.join(BASE, 'assets', 'ml', 'scania_report.json')
COST_FP, COST_FN = 10, 500
SOURCES = [
    ('zip', 'https://archive.ics.uci.edu/static/public/421/aps+failure+at+scania+trucks.zip'),
    ('csv', 'https://raw.githubusercontent.com/jieqiong-pang/APS-Failure-at-Scania-Trucks-Data-Set/master/{name}'),
]
FILES = ('aps_failure_training_set.csv', 'aps_failure_test_set.csv')


def download():
    os.makedirs(DATA_DIR, exist_ok=True)
    if all(os.path.exists(os.path.join(DATA_DIR, f)) for f in FILES):
        return
    for kind, url in SOURCES:
        try:
            print(f'Завантаження: {url.split("/")[2]} ...')
            if kind == 'zip':
                raw = urllib.request.urlopen(url, timeout=120).read()
                with zipfile.ZipFile(io.BytesIO(raw)) as z:
                    for f in FILES:
                        name = next(n for n in z.namelist() if n.endswith(f))
                        with open(os.path.join(DATA_DIR, f), 'wb') as out:
                            out.write(z.read(name))
            else:
                for f in FILES:
                    urllib.request.urlretrieve(url.format(name=f), os.path.join(DATA_DIR, f))
            return
        except Exception as exc:  # noqa: BLE001 - пробуємо наступне джерело
            print(f'  не вдалося: {exc}')
    raise SystemExit('Не вдалося завантажити набір даних. Покладіть файли ' + ', '.join(FILES) + f' у {DATA_DIR}')


def load(name):
    with open(os.path.join(DATA_DIR, name), encoding='utf-8') as fh:
        rows = list(csv.reader(fh))
    start = next(i for i, r in enumerate(rows) if r and r[0] == 'class')
    header, data = rows[start], rows[start + 1:]
    y = np.array([r[0] == 'pos' for r in data], dtype=int)
    X = np.array([[np.nan if v == 'na' else float(v) for v in r[1:]] for r in data], dtype=float)
    return X, y, header[1:]


def models():
    log = FunctionTransformer(lambda a: np.sign(a) * np.log1p(np.abs(a)))
    return {
        'logreg': ('Логістична регресія', make_pipeline(
            SimpleImputer(strategy='median'), log, StandardScaler(),
            LogisticRegression(max_iter=2000, class_weight='balanced', C=0.1))),
        'gboost': ('Градієнтний бустинг', HistGradientBoostingClassifier(
            max_iter=300, learning_rate=0.08, class_weight='balanced', random_state=42)),
    }


def main():
    t0 = time.time()
    download()
    Xtr, ytr, names = load(FILES[0])
    Xte, yte, _ = load(FILES[1])
    print(f'Навчальна вибірка: {len(ytr)} ({ytr.sum()} відмов), перевірна: {len(yte)} ({yte.sum()} відмов)')

    report = {
        'dataset': 'APS Failure at Scania Trucks', 'source': 'Scania CV AB, UCI Machine Learning Repository (2016)',
        'generated_at': datetime.utcnow().isoformat(timespec='seconds') + 'Z',
        'train': {'n': int(len(ytr)), 'positives': int(ytr.sum())},
        'test': {'n': int(len(yte)), 'positives': int(yte.sum())},
        'features': len(names), 'missing_share': round(float(np.isnan(Xtr).mean()), 3),
        'cost': {'fp': COST_FP, 'fn': COST_FN,
                 'no_model': int(yte.sum()) * COST_FN},   # нічого не перевіряти - усі відмови пропущено
        'methods': [],
    }

    # базове правило: одна найінформативніша ознака з порогом (аналог «правила за пробігом»)
    imp = SimpleImputer(strategy='median').fit(Xtr)
    Xtr_i, Xte_i = imp.transform(Xtr), imp.transform(Xte)
    aucs = [roc_auc_score(ytr, Xtr_i[:, j]) if np.std(Xtr_i[:, j]) > 0 else 0.5 for j in range(Xtr_i.shape[1])]
    j = int(np.argmax(aucs))
    rank = lambda col, ref: np.searchsorted(np.sort(ref), col) / len(ref)  # noqa: E731 - шкала 0..1
    p_tr, p_te = rank(Xtr_i[:, j], Xtr_i[:, j]), rank(Xte_i[:, j], Xtr_i[:, j])
    thr = mm.best_threshold(ytr, p_tr, COST_FP, COST_FN, 'cost')
    report['methods'].append({'key': 'rule', 'title': 'Правило за одним показником', 'detail': f'ознака {names[j]}',
                              **mm.summary(yte, p_te, thr), **mm.curves(yte, p_te)})
    print(f'  правило ({names[j]}) готово')

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    for key, (title, model) in models().items():
        t = time.time()
        oof = cross_val_predict(model, Xtr, ytr, cv=cv, method='predict_proba')[:, 1]
        thr = mm.best_threshold(ytr, oof, COST_FP, COST_FN, 'cost')     # поріг обираємо лише на навчальних даних
        model.fit(Xtr, ytr)
        p = model.predict_proba(Xte)[:, 1]
        entry = {'key': key, 'title': title, **mm.summary(yte, p, thr), **mm.curves(yte, p),
                 'calibration': mm.calibration(yte, p)}
        if key == 'gboost':
            sub = np.random.RandomState(0).choice(len(yte), 6000, replace=False)
            pi = permutation_importance(model, Xte[sub], yte[sub], scoring='average_precision', n_repeats=3, random_state=0)
            top = np.argsort(-pi.importances_mean)[:10]
            entry['importance'] = [{'feature': names[i], 'value': round(float(pi.importances_mean[i]), 4)} for i in top]
        report['methods'].append(entry)
        print(f'  {title}: {time.time() - t:.0f} с')

    for m in report['methods']:
        c = m['at_threshold']
        m['cost'] = COST_FP * c['fp'] + COST_FN * c['fn']
    report['best'] = min(report['methods'], key=lambda m: m['cost'])['key']
    report['seconds'] = round(time.time() - t0)
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    with open(REPORT, 'w', encoding='utf-8') as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)
    for m in report['methods']:
        c = m['at_threshold']
        print(f"{m['title']:32} ROC-AUC {m['roc_auc']:.3f}  PR-AUC {m['pr_auc']:.3f}  "
              f"recall {c['recall']:.2f}  precision {c['precision']:.2f}  FP {c['fp']}  FN {c['fn']}  вартість {m['cost']}")
    print(f'Звіт збережено: {REPORT}')


if __name__ == '__main__':
    main()
