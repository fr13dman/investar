"""Deterministic demo data for end-to-end tests and offline development (no network)."""

import math
import random
from datetime import date, datetime, timedelta

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.db import Base
from app.models import Company, FetchLog, PriceDaily, QuoteLatest
from app.niches_catalog import NicheSpec
from app.services.db_utils import upsert
from app.services.metrics import recompute_metrics
from app.services.niches import load_catalog

DEMO_COMPANIES = [
    # ticker, name, sector, industry, sp500, ndx100, shares (bn), base price, drift
    ("AAPL", "Apple Inc.", "Technology", "Consumer Electronics", True, True, 14.8, 180, 0.0006),
    ("MSFT", "Microsoft Corporation", "Technology", "Software - Infrastructure", True, True, 7.4, 380, 0.0005),
    ("NVDA", "NVIDIA Corporation", "Technology", "Semiconductors", True, True, 24.4, 60, 0.0018),
    ("AMD", "Advanced Micro Devices, Inc.", "Technology", "Semiconductors", True, True, 1.6, 140, -0.0002),
    ("ORCL", "Oracle Corporation", "Technology", "Software - Infrastructure", True, False, 2.8, 120, 0.0007),
    ("JPM", "JPMorgan Chase & Co.", "Financial Services", "Banks - Diversified", True, False, 2.8, 170, 0.0004),
    ("GS", "The Goldman Sachs Group, Inc.", "Financial Services", "Capital Markets", True, False, 0.32, 400, 0.0003),
    ("XOM", "Exxon Mobil Corporation", "Energy", "Oil & Gas Integrated", True, False, 4.0, 105, -0.0003),
    ("PEP", "PepsiCo, Inc.", "Consumer Defensive", "Beverages - Non-Alcoholic", True, True, 1.37, 170, -0.0004),
    ("AMZN", "Amazon.com, Inc.", "Consumer Cyclical", "Internet Retail", True, True, 10.5, 150, 0.0006),
    ("TSLA", "Tesla, Inc.", "Consumer Cyclical", "Auto Manufacturers", True, True, 3.2, 240, 0.0002),
    ("ASML", "ASML Holding N.V.", "Technology", "Semiconductor Equipment & Materials", False, True, 0.39, 700, 0.0001),
]
BENCHMARKS = [("SPY", "SPDR S&P 500 ETF Trust", 450, 0.0004), ("QQQ", "Invesco QQQ Trust", 380, 0.0005)]
# Non-index niche symbols: ticker, name, sector, industry, asset type, shares (bn), base price, drift
DEMO_EXTRAS = [
    ("CRWV", "CoreWeave, Inc.", "Technology", "Information Technology Services", "stock", 0.48, 40, 0.0025),
    ("OKLO", "Oklo Inc.", "Utilities", "Utilities - Regulated Electric", "stock", 0.15, 20, 0.003),
    ("URA", "Global X Uranium ETF", None, None, "etf", 0.1, 25, 0.001),
]
DEMO_CATALOG = (
    NicheSpec("ai", "AI", "Companies building, hosting and selling artificial intelligence.", children=(
        NicheSpec("ai-chips", "AI Chips", "Accelerators for AI.", stocks=("NVDA", "AMD", "ASML")),
        NicheSpec("hyperscalers", "Hyperscalers", "Public clouds at global scale.", stocks=("MSFT", "AMZN", "ORCL")),
        NicheSpec("neoclouds", "Neoclouds", "GPU-first clouds.", stocks=("CRWV",)),
    )),
    NicheSpec("energy-transition", "Energy Transition", "Low-carbon power.", etfs=("URA",), children=(
        NicheSpec("small-modular-reactors", "Small Modular Reactors", "SMR developers.", stocks=("OKLO",)),
    )),
)


def _trading_days(end: date, n_days: int) -> list[date]:
    days, d = [], end
    while len(days) < n_days:
        if d.weekday() < 5:
            days.append(d)
        d -= timedelta(days=1)
    return list(reversed(days))


def _series(rng: random.Random, days: list[date], base: float, drift: float) -> list[tuple[date, float]]:
    price, out = base, []
    for i, d in enumerate(days):
        shock = rng.gauss(0, 0.017)
        price *= math.exp(drift + shock + 0.002 * math.sin(i / 9))
        out.append((d, round(price, 2)))
    return out


def seed_market(session: Session, end: date | None = None, years: int = 2) -> None:
    end = end or date.today()
    rng = random.Random(42)
    days = _trading_days(end, 252 * years)
    for model in (QuoteLatest, PriceDaily):
        session.execute(delete(model))
    rows = []
    for t, name, sector, industry, sp, ndx, shares, base, drift in DEMO_COMPANIES:
        session.merge(Company(ticker=t, name=name, sector=sector, industry=industry, gics_sector=sector,
                              in_sp500=sp, in_ndx100=ndx, shares_outstanding=shares * 1e9,
                              pe_ratio=round(rng.uniform(12, 60), 2), country="United States",
                              description=f"{name} is a demo company used for offline development.",
                              website=f"https://www.{t.lower()}.example.com", employees=rng.randint(10_000, 200_000)))
        for d, c in _series(rng, days, base, drift):
            rows.append(dict(ticker=t, date=d, open=c, high=round(c * 1.01, 2), low=round(c * 0.99, 2), close=c,
                             adj_close=c, volume=float(rng.randint(5_000_000, 80_000_000))))
    for t, name, base, drift in BENCHMARKS:
        session.merge(Company(ticker=t, name=name, is_benchmark=True))
        for d, c in _series(rng, days, base, drift):
            rows.append(dict(ticker=t, date=d, open=c, high=c, low=c, close=c, adj_close=c, volume=1e7))
    session.commit()
    upsert(session, PriceDaily, rows, ["ticker", "date"])
    session.commit()
    recompute_metrics(session, today=end)


def seed_niches(session: Session, end: date | None = None, years: int = 2) -> None:
    """Demo niche catalog plus a few non-index symbols (stocks and an ETF) with synthetic prices."""
    end = end or date.today()
    rng = random.Random(7)
    days = _trading_days(end, 252 * years)
    rows = []
    for t, name, sector, industry, kind, shares, base, drift in DEMO_EXTRAS:
        session.merge(Company(ticker=t, name=name, sector=sector, industry=industry, asset_type=kind,
                              shares_outstanding=shares * 1e9, country="United States",
                              pe_ratio=None if kind == "etf" else round(rng.uniform(40, 200), 2),
                              description=f"{name} is a demo symbol used for offline development."))
        for d, c in _series(rng, days, base, drift):
            rows.append(dict(ticker=t, date=d, open=c, high=round(c * 1.01, 2), low=round(c * 0.99, 2), close=c,
                             adj_close=c, volume=float(rng.randint(1_000_000, 20_000_000))))
    session.commit()
    upsert(session, PriceDaily, rows, ["ticker", "date"])
    session.commit()
    load_catalog(session, DEMO_CATALOG)
    recompute_metrics(session, [t for t, *_ in DEMO_EXTRAS], today=end)


def seed_all(session: Session, end: date | None = None) -> None:
    from app.seed_research import seed_research

    Base.metadata.create_all(session.get_bind())
    end = end or date.today()
    seed_market(session, end)
    seed_niches(session, end)
    now = datetime.now().replace(microsecond=0)
    seed_research(session, now)
    for t, *_ in DEMO_EXTRAS:  # demo profiles are complete; don't trigger a live profile refresh
        session.add(FetchLog(resource="profile", ticker=t, source="seed", fetched_at=now, status="ok"))
    session.commit()
