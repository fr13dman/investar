"""Swing metrics: daily, weekly and YTD change measured from the current price."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Company, MetricsSnapshot, PriceDaily, QuoteLatest
from app.services.db_utils import upsert

SPARKLINE_POINTS = 5


@dataclass
class Swings:
    price: float
    chg_1d_pct: float | None
    chg_1d_abs: float | None
    chg_1w_pct: float | None
    chg_1w_abs: float | None
    chg_ytd_pct: float | None
    chg_ytd_abs: float | None
    week52_high: float | None
    week52_low: float | None
    sparkline: list[float]


def _change(price: float, ref: float | None) -> tuple[float | None, float | None]:
    if ref is None or ref == 0:
        return None, None
    return (price / ref - 1) * 100, price - ref


def _last_before(closes: list[tuple[date, float]], cutoff: date) -> float | None:
    ref = None
    for d, c in closes:
        if d < cutoff:
            ref = c
        else:
            break
    return ref


def compute_swings(
    closes: list[tuple[date, float]],
    price: float | None = None,
    prev_close: float | None = None,
) -> Swings | None:
    """`closes` are ascending (date, close) trading-day bars; the last one is the latest
    session (possibly in progress). References:
      1D  -> close of the session before the latest one (or an explicit prev_close)
      1W  -> last close before the Monday of the latest session's week
      YTD -> last close of the previous calendar year
    """
    if not closes:
        return None
    latest_date, latest_close = closes[-1]
    price = latest_close if price is None else price
    if prev_close is None and len(closes) >= 2:
        prev_close = closes[-2][1]

    week_start = latest_date - timedelta(days=latest_date.weekday())
    week_ref = _last_before(closes, week_start)
    ytd_ref = _last_before(closes, date(latest_date.year, 1, 1))

    window = [c for d, c in closes if d > latest_date - timedelta(days=365)] + [price]
    d_pct, d_abs = _change(price, prev_close)
    w_pct, w_abs = _change(price, week_ref)
    y_pct, y_abs = _change(price, ytd_ref)
    spark = [c for _, c in closes[-SPARKLINE_POINTS:]]
    spark[-1] = price
    return Swings(
        price=price,
        chg_1d_pct=d_pct,
        chg_1d_abs=d_abs,
        chg_1w_pct=w_pct,
        chg_1w_abs=w_abs,
        chg_ytd_pct=y_pct,
        chg_ytd_abs=y_abs,
        week52_high=max(window),
        week52_low=min(window),
        sparkline=[round(x, 4) for x in spark],
    )


def recompute_metrics(session: Session, tickers: list[str] | None = None, today: date | None = None) -> int:
    today = today or date.today()
    cutoff = min(date(today.year - 1, 12, 1), today - timedelta(days=380))

    q = select(Company)
    if tickers:
        q = q.where(Company.ticker.in_(tickers))
    companies = {c.ticker: c for c in session.scalars(q)}

    pq = select(PriceDaily.ticker, PriceDaily.date, PriceDaily.close, PriceDaily.volume).where(
        PriceDaily.date >= cutoff
    )
    if tickers:
        pq = pq.where(PriceDaily.ticker.in_(tickers))
    series: dict[str, list[tuple[date, float]]] = defaultdict(list)
    volumes: dict[str, float | None] = {}
    for t, d, c, v in session.execute(pq.order_by(PriceDaily.ticker, PriceDaily.date)):
        series[t].append((d, c))
        volumes[t] = v

    quotes = {q.ticker: q for q in session.scalars(select(QuoteLatest).where(QuoteLatest.ticker.in_(list(companies))))}

    rows = []
    now = datetime.now()
    for t, comp in companies.items():
        closes = series.get(t)
        if not closes:
            continue
        quote = quotes.get(t)
        price = prev = None
        if quote and quote.as_of.date() >= closes[-1][0]:
            price, prev = quote.price, quote.prev_close
        s = compute_swings(closes, price=price, prev_close=prev)
        if s is None:
            continue
        mcap = comp.shares_outstanding * s.price if comp.shares_outstanding else comp.market_cap
        rows.append(
            dict(
                ticker=t,
                price=s.price,
                market_cap=mcap,
                pe_ratio=comp.pe_ratio,
                volume=(quote.volume if quote and quote.volume else volumes.get(t)),
                week52_high=s.week52_high,
                week52_low=s.week52_low,
                chg_1d_pct=s.chg_1d_pct,
                chg_1d_abs=s.chg_1d_abs,
                chg_1w_pct=s.chg_1w_pct,
                chg_1w_abs=s.chg_1w_abs,
                chg_ytd_pct=s.chg_ytd_pct,
                chg_ytd_abs=s.chg_ytd_abs,
                sparkline=s.sparkline,
                as_of=quote.as_of if quote else now,
            )
        )
    upsert(session, MetricsSnapshot, rows, ["ticker"])
    session.commit()
    return len(rows)
