"""ETF section listings, holdings cache, heatmaps and manual refresh."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Company, EtfHoldingsSnapshot, HoldingReturnCache, MetricsSnapshot, Niche
from app.providers import registry
from app.providers.base import FundHoldings, HoldingLine, ProviderUnavailable, to_yahoo
from app.providers.vistashares_meta import DEMO_META
from app.services.metrics import compute_swings, recompute_metrics
from app.services.screener import row_dict
from app.services.universe import niche_member_tickers
from app.vistashares_catalog import FAMILIES, VISTASHARES_FUNDS, VISTASHARES_TICKERS, is_vistashares

log = logging.getLogger(__name__)

HOLDINGS_TTL = timedelta(hours=24)
RETURN_TTL = timedelta(minutes=30)
TOP_N = 25
PERIODS = {"wow": "chg_1w_pct", "mom": "chg_1m_pct", "yoy": "chg_1y_pct"}
AUM_FLOOR_FRAC = 0.02
MAX_REFRESH = 25


def _holding_dicts(fund: FundHoldings) -> list[dict]:
    return [
        {"ticker": h.ticker, "name": h.name, "weight_pct": h.weight_pct, "kind": h.kind}
        for h in fund.holdings
    ]


def _from_snapshot(row: EtfHoldingsSnapshot) -> FundHoldings:
    return FundHoldings(
        ticker=row.ticker,
        as_of=row.as_of,
        source=row.source,
        aum=row.aum,
        holdings=[
            HoldingLine(
                ticker=h.get("ticker"),
                name=h.get("name"),
                weight_pct=float(h["weight_pct"]),
                kind=h.get("kind") or "equity",
            )
            for h in (row.holdings or [])
        ],
    )


def fetch_and_store_holdings(session: Session, ticker: str, force: bool = False) -> EtfHoldingsSnapshot | None:
    t = ticker.strip().upper()
    existing = session.get(EtfHoldingsSnapshot, t)
    now = datetime.now()
    if existing and not force and existing.fetched_at and now - existing.fetched_at < HOLDINGS_TTL:
        return existing
    try:
        fund = registry.holdings(t).holdings(t)
    except ProviderUnavailable as exc:
        log.info("holdings unavailable for %s: %s", t, exc)
        return existing
    if fund is None or not fund.holdings:
        # Never overwrite a good snapshot with an empty/missing payload.
        return existing
    try:
        row = existing or EtfHoldingsSnapshot(ticker=t)
        row.as_of = fund.as_of
        row.source = fund.source
        row.holdings = _holding_dicts(fund)
        row.aum = fund.aum
        row.fetched_at = now
        session.merge(row)
        session.commit()
    except IntegrityError:
        session.rollback()
        return session.get(EtfHoldingsSnapshot, t)
    return session.get(EtfHoldingsSnapshot, t)


def load_etf_holdings(session: Session, tickers: list[str] | None = None, force: bool = False) -> int:
    if tickers:
        targets = [t.upper() for t in tickers]
    else:
        curated = {
            c.ticker
            for c in session.scalars(select(Company).where(Company.asset_type == "etf", Company.extra_source == "curated"))
        }
        targets = sorted(curated | set(VISTASHARES_TICKERS))
    n = 0
    for t in targets:
        if session.get(Company, t) is None:
            continue
        if fetch_and_store_holdings(session, t, force=force):
            n += 1
    return n


def _period_from_closes(closes: list[tuple[date, float]]) -> dict[str, float | None]:
    s = compute_swings(closes)
    if not s:
        return {"chg_1w_pct": None, "chg_1m_pct": None, "chg_1y_pct": None}
    return {"chg_1w_pct": s.chg_1w_pct, "chg_1m_pct": s.chg_1m_pct, "chg_1y_pct": s.chg_1y_pct}


def _metrics_usable(m: MetricsSnapshot) -> bool:
    """Prefer metrics only when MoM/YoY columns are populated (post-migration backfill)."""
    return m.chg_1m_pct is not None and m.chg_1y_pct is not None


def fetch_holding_returns(
    session: Session, tickers: list[str], force: bool = False
) -> dict[str, dict[str, float | None]]:
    now = datetime.now()
    wanted = [to_yahoo(t) for t in tickers if t]
    out: dict[str, dict[str, float | None]] = {}
    missing: list[str] = []

    for t in wanted:
        m = session.get(MetricsSnapshot, t)
        if m and not force and _metrics_usable(m):
            out[t] = {"chg_1w_pct": m.chg_1w_pct, "chg_1m_pct": m.chg_1m_pct, "chg_1y_pct": m.chg_1y_pct}
            continue
        cached = session.get(HoldingReturnCache, t)
        if cached and not force and now - cached.fetched_at < RETURN_TTL:
            out[t] = {
                "chg_1w_pct": cached.chg_1w_pct,
                "chg_1m_pct": cached.chg_1m_pct,
                "chg_1y_pct": cached.chg_1y_pct,
            }
            continue
        missing.append(t)

    if missing:
        try:
            bars = registry.prices().history(missing, period="2y")
        except Exception as exc:
            log.warning("holding return fetch failed: %s", exc)
            for t in missing:
                out.setdefault(t, {"chg_1w_pct": None, "chg_1m_pct": None, "chg_1y_pct": None})
            return out
        by_ticker: dict[str, list[tuple[date, float]]] = {}
        for b in bars:
            by_ticker.setdefault(b.ticker, []).append((b.date, b.close))
        for t in missing:
            closes = sorted(by_ticker.get(t, []), key=lambda x: x[0])
            if not closes:
                out[t] = {"chg_1w_pct": None, "chg_1m_pct": None, "chg_1y_pct": None}
                continue
            periods = _period_from_closes(closes)
            out[t] = periods
            # Only cache successful period computations (avoid poisoning the map for 30m).
            if any(v is not None for v in periods.values()):
                session.merge(
                    HoldingReturnCache(
                        ticker=t,
                        chg_1w_pct=periods["chg_1w_pct"],
                        chg_1m_pct=periods["chg_1m_pct"],
                        chg_1y_pct=periods["chg_1y_pct"],
                        fetched_at=now,
                    )
                )
        session.commit()
    return out


def build_treemap_nodes(holdings: list[HoldingLine], returns: dict[str, dict], period: str) -> list[dict]:
    field = PERIODS[period]
    equities = sorted(
        [h for h in holdings if h.kind == "equity" and h.weight_pct > 0],
        key=lambda h: h.weight_pct,
        reverse=True,
    )
    top, rest = equities[:TOP_N], equities[TOP_N:]
    other_weight = sum(h.weight_pct for h in holdings if h.kind != "equity") + sum(h.weight_pct for h in rest)
    nodes = []
    for h in top:
        ret = returns.get(h.ticker or "", {}).get(field) if h.ticker else None
        nodes.append({
            "id": h.ticker or h.name or "?",
            "ticker": h.ticker,
            "name": h.name,
            "weight_pct": round(h.weight_pct, 4),
            "return_pct": ret,
            "kind": "equity",
            "navigable": bool(h.ticker),
        })
    if other_weight > 0.01:
        nodes.append({
            "id": "OTHER",
            "ticker": None,
            "name": "Other / overlays",
            "weight_pct": round(other_weight, 4),
            "return_pct": None,
            "kind": "other",
            "navigable": False,
        })
    return nodes


def fund_heatmap(session: Session, ticker: str, period: str = "wow", force: bool = False) -> dict:
    if period not in PERIODS:
        raise ValueError(f"unsupported period '{period}'")
    t = ticker.strip().upper()
    snap = fetch_and_store_holdings(session, t, force=force)
    if not snap:
        return {
            "ticker": t, "period": period, "as_of": None, "source": None, "aum": None,
            "nodes": [], "fetched_at": None, "issuer": "vistashares" if is_vistashares(t) else None,
        }
    fund = _from_snapshot(snap)
    if force:
        syms = [h.ticker for h in fund.holdings if h.ticker] + [t]
        for s in syms:
            row = session.get(HoldingReturnCache, s)
            if row:
                session.delete(row)
        session.commit()
        if session.get(Company, t):
            recompute_metrics(session, [t])
    returns = fetch_holding_returns(session, [h.ticker for h in fund.holdings if h.ticker], force=force)
    return {
        "ticker": t,
        "period": period,
        "as_of": fund.as_of.isoformat() if fund.as_of else None,
        "source": fund.source,
        "aum": fund.aum if fund.aum is not None else snap.aum,
        "nodes": build_treemap_nodes(fund.holdings, returns, period),
        "fetched_at": snap.fetched_at.isoformat() if snap.fetched_at else None,
        "issuer": "vistashares" if is_vistashares(t) else None,
    }


def _map_size(aum: float | None, max_aum: float) -> float:
    if max_aum <= 0:
        return 1.0
    base = aum if aum and aum > 0 else max_aum * AUM_FLOOR_FRAC
    return max(base, max_aum * AUM_FLOOR_FRAC)


def _etf_tile(
    c: Company, m: MetricsSnapshot | None, snap: EtfHoldingsSnapshot | None, period: str, max_aum: float,
    aum_override: float | None = None,
) -> dict:
    field = PERIODS[period]
    aum = aum_override if aum_override is not None else (
        (snap.aum if snap and snap.aum else None) or (m.market_cap if m else None)
    )
    return {
        **row_dict(c, m),
        "aum": aum,
        "size": _map_size(aum, max_aum),
        "return_pct": getattr(m, field, None) if m else None,
        "holdings_as_of": snap.as_of.isoformat() if snap and snap.as_of else None,
        "family": None,
        "family_name": None,
    }


def _apply_flat_sizes(tiles: list[dict]) -> None:
    if not tiles:
        return
    max_aum = max((x.get("aum") or 0) for x in tiles) or 1.0
    for x in tiles:
        x["size"] = _map_size(x.get("aum"), max_aum)


def list_niche_etfs(session: Session, niche: str | None = None, period: str = "wow") -> dict:
    """Read-only listing from DB snapshots (no outbound holdings fetches on the request path)."""
    if period not in PERIODS:
        raise ValueError(f"unsupported period '{period}'")

    if niche:
        match = session.scalars(select(Niche).where(Niche.slug == niche)).first()
        if not match:
            return {"period": period, "groups": [], "etfs": []}
        groups_spec = [match]
    else:
        groups_spec = list(
            session.scalars(select(Niche).where(Niche.parent_id.is_(None)).order_by(Niche.sort_order, Niche.name))
        )

    groups = []
    flat: list[dict] = []
    seen: set[str] = set()
    for node in groups_spec:
        comps = session.scalars(
            select(Company).where(
                Company.ticker.in_(niche_member_tickers(node.slug)),
                Company.asset_type == "etf",
            )
        ).all()
        if not comps:
            continue
        snaps = {
            s.ticker: s
            for s in session.scalars(
                select(EtfHoldingsSnapshot).where(EtfHoldingsSnapshot.ticker.in_([c.ticker for c in comps]))
            )
        }
        metrics = {
            m.ticker: m
            for m in session.scalars(select(MetricsSnapshot).where(MetricsSnapshot.ticker.in_([c.ticker for c in comps])))
        }
        tiles = [_etf_tile(c, metrics.get(c.ticker), snaps.get(c.ticker), period, 1.0) for c in comps]
        tiles.sort(key=lambda x: x.get("aum") or 0, reverse=True)
        groups.append({"slug": node.slug, "name": node.name, "etfs": tiles})
        for t in tiles:
            if t["ticker"] not in seen:
                seen.add(t["ticker"])
                flat.append(t)

    # One global size scale so the map and every niche table agree.
    _apply_flat_sizes(flat)
    size_by = {t["ticker"]: t["size"] for t in flat}
    for g in groups:
        for t in g["etfs"]:
            t["size"] = size_by.get(t["ticker"], t.get("size") or 1.0)
    return {"period": period, "groups": groups, "etfs": flat}


def _resolve_aum(
    snap: EtfHoldingsSnapshot | None,
    metrics: MetricsSnapshot | None,
    meta_aum: float | None,
) -> float | None:
    if snap and snap.aum:
        return snap.aum
    if metrics and metrics.market_cap:
        return metrics.market_cap
    return meta_aum


def list_vistashares(session: Session, family: str | None = None, period: str = "wow") -> dict:
    """Read-only listing; AUM falls back to cached issuer meta / demo constants (no live fetch on GET)."""
    if period not in PERIODS:
        raise ValueError(f"unsupported period '{period}'")
    if family and family not in {fid for fid, _ in FAMILIES}:
        raise ValueError(f"unknown VistaShares family '{family}'")

    from app.config import get_settings

    # GET path stays offline-friendly: demo meta when OFFLINE_PROVIDERS, else DB snapshots / market cap only.
    meta = DEMO_META if get_settings().offline_providers else {}
    funds = [f for f in VISTASHARES_FUNDS if family is None or f.family == family]
    tickers = [f.ticker for f in funds]
    snaps = {
        s.ticker: s for s in session.scalars(select(EtfHoldingsSnapshot).where(EtfHoldingsSnapshot.ticker.in_(tickers)))
    }
    comps = {c.ticker: c for c in session.scalars(select(Company).where(Company.ticker.in_(tickers)))}
    metrics = {
        m.ticker: m for m in session.scalars(select(MetricsSnapshot).where(MetricsSnapshot.ticker.in_(tickers)))
    }
    by_family: dict[str, list] = {fid: [] for fid, _ in FAMILIES}
    for f in funds:
        c = comps.get(f.ticker)
        snap = snaps.get(f.ticker)
        m = metrics.get(f.ticker)
        aum = _resolve_aum(snap, m, meta.get(f.ticker).aum if meta.get(f.ticker) else None)
        if c:
            tile = _etf_tile(c, m, snap, period, 1.0, aum_override=aum)
            tile["family"] = f.family
            tile["family_name"] = f.family_name
            tile["name"] = f.name
        else:
            tile = {
                "ticker": f.ticker,
                "name": f.name,
                "asset_type": "etf",
                "extra_source": "curated",
                "aum": aum,
                "size": 1.0,
                "return_pct": None,
                "price": None,
                "family": f.family,
                "family_name": f.family_name,
                "chg_1w_pct": None,
                "chg_1m_pct": None,
                "chg_1y_pct": None,
            }
        by_family.setdefault(f.family, []).append(tile)
    groups = [
        {"slug": fid, "name": label, "etfs": by_family.get(fid, [])}
        for fid, label in FAMILIES
        if by_family.get(fid)
    ]
    flat = [t for g in groups for t in g["etfs"]]
    _apply_flat_sizes(flat)
    size_by = {t["ticker"]: t["size"] for t in flat}
    for g in groups:
        for t in g["etfs"]:
            t["size"] = size_by.get(t["ticker"], t.get("size") or 1.0)
    return {
        "period": period,
        "families": [{"id": fid, "name": label} for fid, label in FAMILIES],
        "groups": groups,
        "etfs": flat,
    }


def refresh_etfs(session: Session, tickers: list[str]) -> dict:
    refreshed = []
    for raw in tickers[:MAX_REFRESH]:
        t = raw.strip().upper()
        if not t:
            continue
        # Single force path: heatmap refreshes holdings + period colors.
        fund_heatmap(session, t, period="wow", force=True)
        refreshed.append(t)
    return {"refreshed": refreshed}
