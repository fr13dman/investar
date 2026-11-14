"""Market search and user-added ("tracked") symbols outside the index universe."""

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import Company, FetchLog, MetricsSnapshot, Niche
from app.providers import registry
from app.services.ingest import apply_profile, fill_ciks, store_bars
from app.services.metrics import recompute_metrics
from app.services.niches import set_user_niches
from app.services.refresh import is_refreshing, last_fetch

# Yahoo exchange codes: Nasdaq (NMS/NGM/NCM/NAS), NYSE (NYQ/NYS), NYSE American (ASE), NYSE Arca (PCX), Cboe BZX (BTS).
US_EXCHANGES = {"NMS", "NGM", "NCM", "NAS", "NYQ", "NYS", "ASE", "PCX", "BTS"}
ASSET_TYPES = {"EQUITY": "stock", "ETF": "etf"}
TRACK_RESOURCE = "track"


def normalize(ticker: str) -> str:
    """Yahoo symbols are used verbatim (BRK-B, SHOP.TO); only case and whitespace are normalized."""
    return ticker.strip().upper()


class TrackError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


def is_tracked(comp: Company | None) -> bool:
    return bool(comp and (comp.is_benchmark or comp.in_sp500 or comp.in_ndx100 or comp.extra_source))


def search_market(session: Session, query: str, limit: int = 10) -> list[dict]:
    matches = registry.search().search(query, limit)
    known = {c.ticker: c for c in session.scalars(select(Company).where(Company.ticker.in_([m.symbol for m in matches])))}
    out = []
    for m in matches:
        asset_type = ASSET_TYPES.get(m.quote_type or "")
        us_listed = m.exchange in US_EXCHANGES
        tracked = is_tracked(known.get(m.symbol))
        out.append({"symbol": m.symbol, "name": m.name, "exchange": m.exchange, "quote_type": m.quote_type,
                    "asset_type": asset_type, "us_listed": us_listed, "tracked": tracked,
                    "addable": bool(asset_type and us_listed and not tracked)})
    return out


def track_symbol(session: Session, ticker: str, niche_ids: list[int] | None = None) -> Company:
    """Validate a symbol (US-listed, USD, stock or ETF) and add it to the universe; prices load in the background."""
    t = normalize(ticker)
    comp = session.get(Company, t)
    if is_tracked(comp):
        raise TrackError(409, f"{t} is already tracked")
    niche_ids = sorted(set(niche_ids or []))
    if niche_ids and len(session.scalars(select(Niche.id).where(Niche.id.in_(niche_ids))).all()) != len(niche_ids):
        raise TrackError(422, "unknown niche id")
    p = registry.profiles().profile(t)
    if p is None or not (p.quote_type or p.name):
        raise TrackError(404, f"no data found for {t}")
    asset_type = ASSET_TYPES.get(p.quote_type or "")
    if asset_type is None:
        raise TrackError(422, f"{t} is a {p.quote_type or 'unknown'} symbol; only stocks and ETFs can be added")
    if p.exchange not in US_EXCHANGES:
        raise TrackError(422, f"{t} trades on {p.exchange or 'an unknown exchange'}; only US-listed symbols can be added")
    if (p.currency or "").upper() != "USD":
        raise TrackError(422, f"{t} is priced in {p.currency or 'an unknown currency'}; only USD symbols can be added")
    comp = comp or Company(ticker=t, name=p.name or t)
    comp.extra_source, comp.asset_type = "user", asset_type
    session.add(comp)
    session.flush()
    apply_profile(session, comp, p)
    session.commit()
    if niche_ids:
        set_user_niches(session, t, niche_ids)
    return comp


def backfill_tracked(session: Session, ticker: str, period: str = "5y") -> None:
    fill_ciks(session, [ticker])
    if not store_bars(session, registry.prices().history([ticker], period)):
        raise RuntimeError(f"no price history for {ticker}")
    recompute_metrics(session, [ticker])


def track_status(session: Session, ticker: str) -> dict:
    t = normalize(ticker)
    row = last_fetch(session, TRACK_RESOURCE, t)
    if is_refreshing(TRACK_RESOURCE, t):
        status = "adding"
    elif row and row.status == "error":
        status = "error"
    elif row or session.get(MetricsSnapshot, t):
        status = "ready"
    else:
        status = "adding"
    return {"ticker": t, "status": status, "message": row.message if row else None}


def untrack(session: Session, ticker: str) -> None:
    t = normalize(ticker)
    comp = session.get(Company, t)
    if comp is None:
        raise TrackError(404, f"unknown ticker {t}")
    if comp.extra_source != "user" or comp.in_sp500 or comp.in_ndx100 or comp.is_benchmark:
        raise TrackError(409, f"{t} is part of the index or curated universe and cannot be removed")
    session.execute(delete(FetchLog).where(FetchLog.ticker == t))
    session.delete(comp)
    session.commit()
