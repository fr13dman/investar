from dataclasses import dataclass

from sqlalchemy import and_, func, nulls_last, select
from sqlalchemy.orm import Session

from app.models import Company, MetricsSnapshot, WatchlistItem
from app.services.universe import in_universe, niche_member_tickers

CAP_BANDS = {
    "mega": (200e9, None),
    "large": (10e9, 200e9),
    "mid": (2e9, 10e9),
    "small": (None, 2e9),
}
SWING_FIELDS = {"chg_1d", "chg_1w", "chg_ytd"}
PLAIN_SORTS = {
    "ticker": Company.ticker,
    "name": Company.name,
    "sector": Company.sector,
    "industry": Company.industry,
    "price": MetricsSnapshot.price,
    "market_cap": MetricsSnapshot.market_cap,
    "volume": MetricsSnapshot.volume,
    "pe_ratio": MetricsSnapshot.pe_ratio,
}


@dataclass
class ScreenerQuery:
    sector: str | None = None
    industry: str | None = None
    niche: str | None = None  # parent or sub-niche slug; a parent includes its sub-niches
    asset_type: str = "all"  # all | stock | etf
    index: str = "all"  # all | sp500 | ndx100 | both | other
    cap_band: str | None = None
    q: str | None = None
    watchlist_id: int | None = None
    chg_window: str = "chg_1d"  # window that chg_min / chg_max apply to (always percent)
    chg_min: float | None = None
    chg_max: float | None = None
    sort: str = "market_cap"
    order: str = "desc"
    mode: str = "pct"  # pct | abs
    page: int = 1
    page_size: int = 50


def sort_column(sort: str, mode: str):
    if sort in SWING_FIELDS:
        return getattr(MetricsSnapshot, f"{sort}_{'abs' if mode == 'abs' else 'pct'}")
    if sort in PLAIN_SORTS:
        return PLAIN_SORTS[sort]
    raise ValueError(f"unsupported sort '{sort}'")


def _filters(q: ScreenerQuery) -> list:
    conds = [~Company.is_benchmark, in_universe()]
    if q.sector:
        conds.append(Company.sector == q.sector)
    if q.industry:
        conds.append(Company.industry == q.industry)
    if q.niche:
        conds.append(Company.ticker.in_(niche_member_tickers(q.niche)))
    if q.asset_type in ("stock", "etf"):
        conds.append(Company.asset_type == q.asset_type)
    if q.index == "sp500":
        conds.append(Company.in_sp500)
    elif q.index == "ndx100":
        conds.append(Company.in_ndx100)
    elif q.index == "both":
        conds.append(and_(Company.in_sp500, Company.in_ndx100))
    elif q.index == "other":
        conds.append(and_(~Company.in_sp500, ~Company.in_ndx100))
    if q.cap_band:
        lo, hi = CAP_BANDS[q.cap_band]
        if lo is not None:
            conds.append(MetricsSnapshot.market_cap >= lo)
        if hi is not None:
            conds.append(MetricsSnapshot.market_cap < hi)
    if q.chg_min is not None or q.chg_max is not None:
        if q.chg_window not in SWING_FIELDS:
            raise ValueError(f"unsupported change window '{q.chg_window}'")
        col = getattr(MetricsSnapshot, f"{q.chg_window}_pct")
        if q.chg_min is not None:
            conds.append(col >= q.chg_min)
        if q.chg_max is not None:
            conds.append(col <= q.chg_max)
    if q.q:
        like = f"%{q.q.strip()}%"
        conds.append(Company.ticker.ilike(like) | Company.name.ilike(like))
    if q.watchlist_id:
        conds.append(Company.ticker.in_(select(WatchlistItem.ticker).where(WatchlistItem.watchlist_id == q.watchlist_id)))
    return conds


def row_dict(c: Company, m: MetricsSnapshot | None) -> dict:
    return {
        "ticker": c.ticker,
        "name": c.name,
        "sector": c.sector,
        "industry": c.industry,
        "asset_type": c.asset_type or "stock",
        "extra_source": c.extra_source,
        "in_sp500": c.in_sp500,
        "in_ndx100": c.in_ndx100,
        "price": m.price if m else None,
        "market_cap": m.market_cap if m else None,
        "volume": m.volume if m else None,
        "pe_ratio": m.pe_ratio if m else None,
        "week52_high": m.week52_high if m else None,
        "week52_low": m.week52_low if m else None,
        "chg_1d_pct": m.chg_1d_pct if m else None,
        "chg_1d_abs": m.chg_1d_abs if m else None,
        "chg_1w_pct": m.chg_1w_pct if m else None,
        "chg_1w_abs": m.chg_1w_abs if m else None,
        "chg_ytd_pct": m.chg_ytd_pct if m else None,
        "chg_ytd_abs": m.chg_ytd_abs if m else None,
        "sparkline": m.sparkline if m else None,
        "as_of": m.as_of.isoformat() if m and m.as_of else None,
    }


def screen(session: Session, q: ScreenerQuery) -> dict:
    col = sort_column(q.sort, q.mode)
    conds = _filters(q)
    base = select(Company, MetricsSnapshot).outerjoin(MetricsSnapshot, MetricsSnapshot.ticker == Company.ticker)
    total = session.scalar(
        select(func.count()).select_from(Company).outerjoin(MetricsSnapshot, MetricsSnapshot.ticker == Company.ticker).where(*conds)
    )
    order = nulls_last(col.desc() if q.order == "desc" else col.asc())
    page_size = max(1, min(q.page_size, 600))
    stmt = base.where(*conds).order_by(order, Company.ticker).offset((max(q.page, 1) - 1) * page_size).limit(page_size)
    items = [row_dict(c, m) for c, m in session.execute(stmt)]
    return {"total": total or 0, "page": q.page, "page_size": page_size, "items": items}


def sector_tree(session: Session) -> list[dict]:
    stmt = (
        select(Company.sector, Company.industry, func.count())
        .where(~Company.is_benchmark, in_universe(), Company.asset_type == "stock", Company.sector.is_not(None))
        .group_by(Company.sector, Company.industry)
        .order_by(Company.sector, Company.industry)
    )
    tree: dict[str, dict] = {}
    for sector, industry, n in session.execute(stmt):
        node = tree.setdefault(sector, {"sector": sector, "count": 0, "industries": []})
        node["count"] += n
        if industry:
            node["industries"].append({"industry": industry, "count": n})
    return list(tree.values())


def movers(session: Session, sector: str | None = None, window: str = "chg_1d", mode: str = "pct",
           limit: int = 5, industry: str | None = None, niche: str | None = None) -> dict:
    col = sort_column(window, mode)
    conds = _filters(ScreenerQuery(sector=sector, industry=industry, niche=niche)) + [col.is_not(None)]
    base = select(Company, MetricsSnapshot).join(MetricsSnapshot, MetricsSnapshot.ticker == Company.ticker).where(*conds)
    gainers = [row_dict(c, m) for c, m in session.execute(base.order_by(col.desc()).limit(limit))]
    losers = [row_dict(c, m) for c, m in session.execute(base.order_by(col.asc()).limit(limit))]
    return {"window": window, "mode": mode, "gainers": gainers, "losers": losers}


def benchmarks(session: Session) -> list[dict]:
    stmt = (
        select(Company, MetricsSnapshot)
        .outerjoin(MetricsSnapshot, MetricsSnapshot.ticker == Company.ticker)
        .where(Company.is_benchmark)
        .order_by(Company.ticker)
    )
    return [row_dict(c, m) for c, m in session.execute(stmt)]
