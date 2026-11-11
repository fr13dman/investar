from datetime import date, timedelta

import pytest

from app.models import MetricsSnapshot, QuoteLatest
from app.services.metrics import compute_swings, recompute_metrics


def bars(start: date, closes: list[float]) -> list[tuple[date, float]]:
    out, d = [], start
    for c in closes:
        while d.weekday() >= 5:
            d += timedelta(days=1)
        out.append((d, c))
        d += timedelta(days=1)
    return out


def test_daily_weekly_ytd_references():
    # Dec 29 2025 (Mon) .. Jan 9 2026 (Fri): 10 trading days.
    series = bars(date(2025, 12, 29), [100, 101, 102, 104, 103, 105, 106, 107, 108, 110])
    s = compute_swings(series)
    assert s.price == 110
    # 1D: vs previous session close (108)
    assert s.chg_1d_abs == pytest.approx(2)
    assert s.chg_1d_pct == pytest.approx((110 / 108 - 1) * 100)
    # 1W: latest session is Fri Jan 9; week starts Mon Jan 5; last close before = Fri Jan 2 (103)
    assert series[4] == (date(2026, 1, 2), 103)
    assert s.chg_1w_abs == pytest.approx(7)
    # YTD: last close of 2025 = Wed Dec 31 (102)
    assert s.chg_ytd_abs == pytest.approx(8)
    assert s.chg_ytd_pct == pytest.approx((110 / 102 - 1) * 100)
    assert s.sparkline == [105, 106, 107, 108, 110]
    assert s.week52_high == 110 and s.week52_low == 100


def test_live_price_and_prev_close_override():
    series = bars(date(2026, 3, 2), [50, 51, 52])
    s = compute_swings(series, price=55, prev_close=51.5)
    assert s.price == 55
    assert s.chg_1d_abs == pytest.approx(3.5)
    assert s.sparkline[-1] == 55
    assert s.week52_high == 55


def test_missing_references_are_none():
    s = compute_swings([(date(2026, 1, 5), 10.0)])
    assert s.chg_1d_pct is None and s.chg_ytd_pct is None and s.chg_1w_pct is None


def test_empty_series():
    assert compute_swings([]) is None


def test_holiday_week_uses_last_trading_close():
    # Mon Jan 19 2026 is a market holiday (no bar); week of Tue Jan 20 references Fri Jan 16.
    series = [(date(2026, 1, 15), 10), (date(2026, 1, 16), 11), (date(2026, 1, 20), 12), (date(2026, 1, 21), 13)]
    s = compute_swings(series)
    assert s.chg_1w_abs == pytest.approx(2)


def test_recompute_metrics_uses_fresh_quote(seeded):
    from datetime import datetime

    from tests.conftest import SEED_END

    seeded.merge(QuoteLatest(ticker="AAPL", price=999.0, prev_close=990.0, as_of=datetime.combine(SEED_END, datetime.min.time())))
    seeded.commit()
    recompute_metrics(seeded, ["AAPL"], today=SEED_END)
    m = seeded.get(MetricsSnapshot, "AAPL")
    assert m.price == 999.0
    assert m.chg_1d_abs == pytest.approx(9.0)
    assert m.market_cap == pytest.approx(999.0 * 14.8e9)
