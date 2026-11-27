"""
Спільні метрики якості класифікаторів для прогнозу несправностей
(використовуються і для власних даних автопарку, і для перевірки на наборі Scania APS).
"""
import numpy as np
from sklearn.metrics import (average_precision_score, brier_score_loss, precision_recall_curve,
                             roc_auc_score, roc_curve)


def confusion(y, pred):
    y, pred = np.asarray(y).astype(bool), np.asarray(pred).astype(bool)
    return {'tp': int((y & pred).sum()), 'fp': int((~y & pred).sum()),
            'fn': int((y & ~pred).sum()), 'tn': int((~y & ~pred).sum())}


def at_threshold(y, proba, threshold):
    c = confusion(y, np.asarray(proba) >= threshold)
    precision = c['tp'] / (c['tp'] + c['fp']) if c['tp'] + c['fp'] else 0.0
    recall = c['tp'] / (c['tp'] + c['fn']) if c['tp'] + c['fn'] else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {**c, 'threshold': round(float(threshold), 4), 'precision': round(precision, 3),
            'recall': round(recall, 3), 'f1': round(f1, 3)}


def best_threshold(y, proba, cost_fp=1.0, cost_fn=1.0, objective='f1'):
    """Поріг, що мінімізує вартість помилок (objective='cost') або максимізує F1."""
    y, proba = np.asarray(y), np.asarray(proba)
    candidates = np.unique(np.quantile(proba, np.linspace(0.5, 0.999, 300)))
    best, best_val = 0.5, None
    for t in candidates:
        c = at_threshold(y, proba, t)
        val = -(cost_fp * c['fp'] + cost_fn * c['fn']) if objective == 'cost' else c['f1']
        if best_val is None or val > best_val:
            best, best_val = float(t), val
    return best


def _thin(xs, ys, n=60):
    """Скорочує криву до ~n точок для графіка."""
    idx = np.unique(np.linspace(0, len(xs) - 1, min(n, len(xs))).astype(int))
    return [{'x': round(float(xs[i]), 4), 'y': round(float(ys[i]), 4)} for i in idx]


def curves(y, proba):
    fpr, tpr, _ = roc_curve(y, proba)
    prec, rec, _ = precision_recall_curve(y, proba)
    order = np.argsort(rec)
    return {'roc': _thin(fpr, tpr), 'pr': _thin(rec[order], prec[order])}


def calibration(y, proba, bins=10):
    """Надійність прогнозу: середня прогнозована ймовірність vs фактична частка відмов у кожному інтервалі."""
    y, proba = np.asarray(y), np.asarray(proba)
    edges = np.quantile(proba, np.linspace(0, 1, bins + 1))
    out = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (proba >= lo) & (proba <= hi)
        if m.sum():
            out.append({'predicted': round(float(proba[m].mean()), 4), 'actual': round(float(y[m].mean()), 4), 'n': int(m.sum())})
    return out


def lift_top(y, proba, share=0.2):
    """Яка частка всіх відмов припадає на share найризикованіших об'єктів."""
    y, proba = np.asarray(y), np.asarray(proba)
    k = max(1, int(round(len(y) * share)))
    top = np.argsort(-proba)[:k]
    return round(float(y[top].sum() / max(1, y.sum())), 3)


def summary(y, proba, threshold):
    y, proba = np.asarray(y), np.asarray(proba)
    return {
        'roc_auc': round(float(roc_auc_score(y, proba)), 4),
        'pr_auc': round(float(average_precision_score(y, proba)), 4),
        'brier': round(float(brier_score_loss(y, np.clip(proba, 0, 1))), 4),
        'top20_capture': lift_top(y, proba, 0.2),
        'at_threshold': at_threshold(y, proba, threshold),
    }
