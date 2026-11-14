"""Universe loading, price backfill, intraday refresh and profile enrichment."""

import logging
import re
import time
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import Company, Executive, PriceDaily, QuoteLatest
from app.providers import registry
from app.providers.base import PriceBar, Profile
from app.services.db_utils import upsert
from app.services.metrics import recompute_metrics
from app.services.refresh import record_fetch
from app.services.universe import in_universe

log = logging.getLogger(__name__)

BENCHMARKS = {"SPY": "SPDR S&P 500 ETF Trust", "QQQ": "Invesco QQQ Trust"}
# Fallback when Yahoo has no sector: keep the screener on one taxonomy.
GICS_TO_YAHOO = {
    "Information Technology": "Technology",
    "Financials": "Financial Services",
    "Health Care": "Healthcare",
    "Consumer Discretionary": "Consumer Cyclical",
    "Consumer Staples": "Consumer Defensive",
    "Materials": "Basic Materials",
}


def yahoo_sector(gics: str | None) -> str | None:
    return GICS_TO_YAHOO.get(gics, gics) if gics else None
CEO_TITLE = re.compile(r"\bCEO\b|chief executive officer", re.I)


def load_universe(session: Session) -> int:
    rows = registry.constituents().fetch()
    merged: dict[str, dict] = {}
    for r in rows:
        m = merged.setdefault(r.ticker, {"ticker": r.ticker, "name": r.name, "in_sp500": False, "in_ndx100": False})
        m["in_sp500"] |= r.index == "sp500"
        m["in_ndx100"] |= r.index == "ndx100"
        for attr in ("cik", "gics_sector", "gics_sub_industry", "headquarters", "founded"):
            val = getattr(r, attr)
            if val and not m.get(attr):
                m[attr] = val
        if r.index == "sp500":
            m["name"] = r.name

    existing = {c.ticker: c for c in session.scalars(select(Company))}
    for c in existing.values():
        if not c.is_benchmark:
            c.in_sp500 = c.in_ndx100 = False
    for t, data in merged.items():
        comp = existing.get(t) or Company(ticker=t)
        for k, v in data.items():
            setattr(comp, k, v)
        comp.sector = comp.sector or yahoo_sector(data.get("gics_sector"))
        session.add(comp)
    for t, name in BENCHMARKS.items():
        comp = existing.get(t) or Company(ticker=t, name=name)
        comp.is_benchmark = True
        comp.asset_type = "etf"
        session.add(comp)
    session.commit()
    record_fetch(session, "universe", "", "wikipedia")
    return len(merged)


def universe_tickers(session: Session, include_benchmarks: bool = True) -> list[str]:
    q = select(Company.ticker).where(in_universe() | Company.is_benchmark)
    if not include_benchmarks:
        q = q.where(~Company.is_benchmark)
    return list(session.scalars(q.order_by(Company.ticker)))


def fill_ciks(session: Session, tickers: list[str] | None = None) -> int:
    """Best-effort SEC CIK lookup for non-index symbols so filings-based research works for them."""
    q = select(Company).where(Company.cik.is_(None), Company.asset_type == "stock", Company.extra_source.is_not(None))
    if tickers:
        q = q.where(Company.ticker.in_(tickers))
    missing = list(session.scalars(q))
    provider = registry.constituents()
    if not missing or not hasattr(provider, "ciks"):
        return 0
    try:
        ciks = provider.ciks()
    except Exception as exc:  # noqa: BLE001
        log.warning("SEC ticker map unavailable: %s", exc)
        return 0
    n = 0
    for comp in missing:
        if cik := ciks.get(comp.ticker):
            comp.cik, n = cik, n + 1
    session.commit()
    return n


def fetch_new_symbols(session: Session, tickers: list[str], period: str = "5y") -> int:
    """Profile + price history + metrics for symbols that just joined the tracked universe."""
    if not tickers:
        return 0
    fill_ciks(session, tickers)
    enrich_profiles(session, tickers, pause=0)
    n = store_bars(session, registry.prices().history(tickers, period))
    recompute_metrics(session, tickers)
    return n


def store_bars(session: Session, bars: list[PriceBar]) -> int:
    rows = [
        dict(ticker=b.ticker, date=b.date, open=b.open, high=b.high, low=b.low, close=b.close,
             adj_close=b.adj_close, volume=b.volume)
        for b in bars
    ]
    upsert(session, PriceDaily, rows, ["ticker", "date"])
    session.commit()
    return len(rows)


def backfill_prices(session: Session, period: str = "5y", tickers: list[str] | None = None) -> int:
    tickers = tickers or universe_tickers(session)
    n = store_bars(session, registry.prices().history(tickers, period))
    record_fetch(session, "prices_backfill", "", "yfinance", message=f"{n} bars")
    recompute_metrics(session)
    return n


def quotes_from_bars(bars: list[PriceBar], as_of: datetime) -> list[dict]:
    by_ticker: dict[str, list[PriceBar]] = {}
    for b in sorted(bars, key=lambda b: (b.ticker, b.date)):
        by_ticker.setdefault(b.ticker, []).append(b)
    out = []
    for t, series in by_ticker.items():
        last = series[-1]
        prev = series[-2].close if len(series) >= 2 else None
        out.append(dict(ticker=t, price=last.close, prev_close=prev, day_high=last.high, day_low=last.low,
                        volume=last.volume, source="yfinance", as_of=as_of))
    return out


def refresh_intraday(session: Session) -> int:
    tickers = universe_tickers(session)
    bars = registry.prices().recent(tickers)
    store_bars(session, bars)
    known = set(tickers)
    upsert(session, QuoteLatest, [q for q in quotes_from_bars(bars, datetime.now()) if q["ticker"] in known],
           ["ticker"])
    session.commit()
    n = recompute_metrics(session)
    record_fetch(session, "prices_intraday", "", "yfinance", message=f"{n} tickers")
    return n


def apply_profile(session: Session, comp: Company, p: Profile) -> None:
    if p.name and (not comp.name or comp.name == comp.ticker):
        comp.name = p.name
    if p.quote_type in ("ETF", "MUTUALFUND"):
        comp.asset_type = "etf"
    comp.sector = p.sector or yahoo_sector(comp.sector) or yahoo_sector(comp.gics_sector)
    comp.industry = p.industry or comp.industry or comp.gics_sub_industry
    comp.description = p.description or comp.description
    comp.website = p.website or comp.website
    comp.country = p.country or comp.country
    if p.city:
        comp.headquarters = ", ".join(x for x in (p.city, p.state, p.country) if x)
    comp.employees = p.employees or comp.employees
    comp.shares_outstanding = p.shares_outstanding or comp.shares_outstanding
    comp.market_cap = p.market_cap or comp.market_cap
    comp.pe_ratio = p.pe_ratio
    comp.exchange = p.exchange or comp.exchange
    if p.officers:
        session.execute(delete(Executive).where(Executive.ticker == comp.ticker, Executive.source == "yfinance"))
        ceo_idx = pick_ceo([o.title for o in p.officers])
        for i, o in enumerate(p.officers):
            session.add(Executive(ticker=comp.ticker, name=o.name, title=o.title, total_pay=o.total_pay,
                                  year_born=o.year_born, is_ceo=i == ceo_idx))


def pick_ceo(titles: list[str | None]) -> int | None:
    """Index of the company-level CEO; titles like 'CEO of Specialty Insurance' are subsidiaries."""
    matches = [i for i, t in enumerate(titles) if t and CEO_TITLE.search(t)]
    for i in matches:
        if not re.search(r"\b(of|at)\b", titles[i], re.I):
            return i
    return matches[0] if matches else None


def enrich_profiles(session: Session, tickers: list[str] | None = None, pause: float = 0.2) -> int:
    tickers = tickers or universe_tickers(session, include_benchmarks=False)
    provider = registry.profiles()
    done = 0
    for t in tickers:
        comp = session.get(Company, t)
        p = provider.profile(t)
        if comp is None or p is None:
            record_fetch(session, "profile", t, "yfinance", "error", "no profile")
            continue
        apply_profile(session, comp, p)
        session.commit()
        record_fetch(session, "profile", t, "yfinance")
        done += 1
        if pause:
            time.sleep(pause)
    recompute_metrics(session)
    return done
