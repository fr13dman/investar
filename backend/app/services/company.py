import logging
import time
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CeoScorecard, Company, Executive, MetricsSnapshot, PriceDaily, QuoteLatest
from app.providers import registry
from app.services.ingest import apply_profile
from app.services.metrics import recompute_metrics
from app.services.niches import company_niches
from app.services.screener import row_dict

log = logging.getLogger(__name__)

RANGES = {"1m": 31, "ytd": None, "1y": 366, "5y": 5 * 366 + 2}
INTRADAY = {"1d": ("1d", "5m"), "1w": ("5d", "30m")}
_intraday_cache: dict[tuple[str, str], tuple[float, list[dict]]] = {}
INTRADAY_TTL = 300


def profile_payload(session: Session, comp: Company) -> dict:
    metrics = session.get(MetricsSnapshot, comp.ticker)
    quote = session.get(QuoteLatest, comp.ticker)
    execs = session.scalars(select(Executive).where(Executive.ticker == comp.ticker).order_by(Executive.id)).all()
    return {
        **row_dict(comp, metrics),
        "cik": comp.cik,
        "exchange": comp.exchange,
        "gics_sector": comp.gics_sector,
        "gics_sub_industry": comp.gics_sub_industry,
        "website": comp.website,
        "description": comp.description,
        "headquarters": comp.headquarters,
        "country": comp.country,
        "employees": comp.employees,
        "founded": comp.founded,
        "is_benchmark": comp.is_benchmark,
        "quote": {
            "price": quote.price, "prev_close": quote.prev_close, "day_high": quote.day_high,
            "day_low": quote.day_low, "source": quote.source, "as_of": quote.as_of.isoformat(),
        } if quote else None,
        "executives": [{"name": e.name, "title": e.title, "total_pay": e.total_pay, "is_ceo": e.is_ceo} for e in execs],
        "niches": company_niches(session, comp.ticker),
    }


def refresh_profile(session: Session, ticker: str) -> None:
    comp = session.get(Company, ticker)
    p = registry.profiles().profile(ticker)
    if comp is None or p is None:
        raise RuntimeError("profile unavailable")
    apply_profile(session, comp, p)
    session.commit()
    recompute_metrics(session, [ticker])


def live_quote(session: Session, ticker: str) -> dict:
    """Finnhub real-time quote when a key is configured; stored (delayed) quote otherwise."""
    source = "stored"
    try:
        q = registry.quotes().quote(ticker)
    except Exception as exc:  # noqa: BLE001  (no key, rate limit, network)
        log.info("live quote unavailable for %s: %s", ticker, exc)
        q = None
    if q:
        row = session.get(QuoteLatest, ticker) or QuoteLatest(ticker=ticker)
        row.price, row.prev_close, row.day_high, row.day_low = q.price, q.prev_close, q.day_high, q.day_low
        row.as_of, row.source = q.as_of, "finnhub"
        session.add(row)
        session.commit()
        recompute_metrics(session, [ticker])
        source = "finnhub"
    m = session.get(MetricsSnapshot, ticker)
    quote = session.get(QuoteLatest, ticker)
    return {
        "ticker": ticker,
        "source": source,
        "price": m.price if m else (quote.price if quote else None),
        "chg_1d_pct": m.chg_1d_pct if m else None,
        "chg_1d_abs": m.chg_1d_abs if m else None,
        "as_of": (quote.as_of.isoformat() if quote else (m.as_of.isoformat() if m and m.as_of else None)),
    }


def _daily(session: Session, ticker: str, start: date | None) -> list[dict]:
    q = select(PriceDaily).where(PriceDaily.ticker == ticker)
    if start:
        q = q.where(PriceDaily.date >= start)
    return [
        {"time": p.date.isoformat(), "open": p.open or p.close, "high": p.high or p.close, "low": p.low or p.close,
         "close": p.close, "volume": p.volume}
        for p in session.scalars(q.order_by(PriceDaily.date))
    ]


def _intraday(ticker: str, rng: str) -> list[dict]:
    key = (ticker, rng)
    hit = _intraday_cache.get(key)
    if hit and time.monotonic() - hit[0] < INTRADAY_TTL:
        return hit[1]
    period, interval = INTRADAY[rng]
    try:
        bars = registry.prices().intraday(ticker, period, interval)
    except Exception as exc:  # noqa: BLE001
        log.info("intraday unavailable for %s: %s", ticker, exc)
        bars = []
    _intraday_cache[key] = (time.monotonic(), bars)
    return bars


def price_series(session: Session, ticker: str, rng: str, today: date | None = None) -> dict:
    today = today or date.today()
    interval = "1d"
    if rng in INTRADAY:
        bars, spy = _intraday(ticker, rng), _intraday("SPY", rng)
        interval = INTRADAY[rng][1]
        if not bars:  # fall back to recent daily bars when intraday data is unavailable
            start = today - timedelta(days=7 if rng == "1w" else 3)
            bars, spy, interval = _daily(session, ticker, start), _daily(session, "SPY", start), "1d"
    else:
        last = session.scalar(select(PriceDaily.date).where(PriceDaily.ticker == ticker).order_by(PriceDaily.date.desc()).limit(1))
        anchor = last or today
        start = date(anchor.year, 1, 1) if rng == "ytd" else anchor - timedelta(days=RANGES[rng])
        bars, spy = _daily(session, ticker, start), _daily(session, "SPY", start)
    return {"ticker": ticker, "range": rng, "interval": interval, "bars": bars, "benchmark": {"ticker": "SPY", "bars": spy}}


def ceo_payload(card: CeoScorecard | None) -> dict | None:
    if card is None:
        return None
    return {
        "ceo_name": card.ceo_name,
        "tenure_start": card.tenure_start.isoformat() if card.tenure_start else None,
        "tenure_source": card.tenure_source,
        "window_start": card.window_start.isoformat() if card.window_start else None,
        "window_truncated": card.window_truncated,
        "tsr_pct": card.tsr_pct,
        "spy_tsr_pct": card.spy_tsr_pct,
        "excess_return_pct": card.excess_return_pct,
        "tsr_annualized_pct": card.tsr_annualized_pct,
        "spy_annualized_pct": card.spy_annualized_pct,
        "revenue_cagr_pct": card.revenue_cagr_pct,
        "eps_cagr_pct": card.eps_cagr_pct,
        "margin_start_pct": card.margin_start_pct,
        "margin_end_pct": card.margin_end_pct,
        "fundamentals": card.fundamentals or [],
        "pay_vs_performance": card.pay_vs_performance or [],
        "tenures": card.tenures or [],
        "computed_at": card.computed_at.isoformat() if card.computed_at else None,
    }
