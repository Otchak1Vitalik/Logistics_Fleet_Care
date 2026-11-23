"""Експеримент 5. Розрахунок норм витрат пального та виявлення перевитрат."""
from datetime import datetime

import pytest

from services import fuel_analyzer as fa

JAN, JUL = datetime(2026, 1, 15), datetime(2026, 7, 15)


@pytest.mark.parametrize('distance,norm,date,expected', [
    (500, 28.0, JUL, 140.0),     # 500/100*28*1.00
    (500, 28.0, JAN, 152.6),     # 500/100*28*1.09
    (1200, 31.0, JAN, 405.48),   # 1200/100*31*1.09
    (0, 28.0, JUL, 0),
])
def test_fuel_norm(distance, norm, date, expected):
    assert fa.calculate_fuel_norm(distance, norm, date) == pytest.approx(expected, abs=0.01)


def test_overspend_detected():
    res = fa.check_overspend(actual_consumption=32.0, base_norm=28.0, threshold=10)
    assert res['is_overspend'] and res['deviation_percent'] == pytest.approx(14.29, abs=0.01)


def test_within_threshold():
    assert not fa.check_overspend(30.0, 28.0, threshold=10)['is_overspend']


def test_waybill_analysis_uses_season_coefficient():
    res = fa.analyze_waybill_fuel({'odometer_start': 1000, 'odometer_end': 1500, 'fuel_used': 150},
                                  {'fuel_norm': 28.0}, JAN)
    assert res['fuel_norm_recommended'] == pytest.approx(152.6) and res['season_coefficient'] == 1.09


def test_settings_winter_coefficient_respected():
    """Коефіцієнт, змінений керівником у налаштуваннях, має впливати на розрахунок."""
    res = fa.calculate_fuel_norm(500, 28.0, JAN, settings={'winter_coefficient': 1.15})
    assert res == pytest.approx(161.0)
