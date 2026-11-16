"""ETF section listings, holdings cache, heatmaps and manual refresh."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Company, EtfHoldingsSnapshot, HoldingReturnCache, MetricsSnapshot, Niche, NicheMember
from app.providers import registry
from app.providers.base import FundHoldings, HoldingLine, ProviderUnavailable, to_yahoo
from app.services.metrics import compute_swings, recompute_metrics
from app.services.screener import row_dict
from app.services.universe import niche_member_tickers
from app.vistashares_catalog import FAMILIES, VISTASHARES_FUNDS, VISTASHARES_TICKERS, is_vistashares

HOLDINGS_TTL = timedelta(hours=24)
RETURN_TTL = timedelta(minutes=30)
TOP_N = 25
PERIODS = {"wow": "chg_1w_pct", "mom": "chg_1m_pct", "yoy": "chg_1y_pct"}
AUM_FLOOR_FRAC = 0.02


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
    except ProviderUnavailable:
        return existing
    if fund is None:
        return existing
    row = existing or EtfHoldingsSnapshot(ticker=t)
    row.as_of = fund.as_of
    row.source = fund.source
    row.holdings = _holding_dicts(fund)
    row.aum = fund.aum
    row.fetched_at = now
    session.merge(row)
    session.commit()
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


def fetch_holding_returns(
    session: Session, tickers: list[str], force: bool = False
) -> dict[str, dict[str, float | None]]:
    now = datetime.now()
    wanted = [to_yahoo(t) for t in tickers if t]
    out: dict[str, dict[str, float | None]] = {}
    missing: list[str] = []

    for t in wanted:
        m = session.get(MetricsSnapshot, t)
        if m and not force:
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
        except Exception:
            bars = []
        by_ticker: dict[str, list[tuple[date, float]]] = {}
        for b in bars:
            by_ticker.setdefault(b.ticker, []).append((b.date, b.close))
        for t in missing:
            closes = sorted(by_ticker.get(t, []), key=lambda x: x[0])
            periods = _period_from_closes(closes) if closes else {
                "chg_1w_pct": None, "chg_1m_pct": None, "chg_1y_pct": None,
            }
            out[t] = periods
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
    c: Company, m: MetricsSnapshot | None, snap: EtfHoldingsSnapshot | None, period: str, max_aum: float
) -> dict:
    field = PERIODS[period]
    aum = (snap.aum if snap and snap.aum else None) or (m.market_cap if m else None)
    return {
        **row_dict(c, m),
        "aum": aum,
        "size": _map_size(aum, max_aum),
        "return_pct": getattr(m, field, None) if m else None,
        "holdings_as_of": snap.as_of.isoformat() if snap and snap.as_of else None,
        "family": None,
        "family_name": None,
    }


def _ensure_holdings(session: Session, tickers: list[str]) -> None:
    for t in tickers:
        fetch_and_store_holdings(session, t)


def list_niche_etfs(session: Session, niche: str | None = None, period: str = "wow") -> dict:
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
        _ensure_holdings(session, [c.ticker for c in comps])
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
        aums = [
            (snaps[c.ticker].aum if c.ticker in snaps and snaps[c.ticker].aum else (metrics[c.ticker].market_cap if c.ticker in metrics else 0))
            or 0
            for c in comps
        ]
        max_aum = max(aums) if aums else 1.0
        tiles = [_etf_tile(c, metrics.get(c.ticker), snaps.get(c.ticker), period, max_aum) for c in comps]
        tiles.sort(key=lambda x: x.get("aum") or 0, reverse=True)
        groups.append({"slug": node.slug, "name": node.name, "etfs": tiles})
        for t in tiles:
            if t["ticker"] not in seen:
                seen.add(t["ticker"])
                flat.append(t)

    if flat:
        max_aum = max((x.get("aum") or 0) for x in flat) or 1.0
        for x in flat:
            x["size"] = _map_size(x.get("aum"), max_aum)
    return {"period": period, "groups": groups, "etfs": flat}


def ensure_vistashares_companies(session: Session) -> list[str]:
    """Create curated ETF company rows for any VistaShares ticker missing from the universe."""
    created: list[str] = []
    for f in VISTASHARES_FUNDS:
        comp = session.get(Company, f.ticker)
        if comp is None:
            session.add(
                Company(
                    ticker=f.ticker,
                    name=f.name,
                    asset_type="etf",
                    extra_source="curated",
                )
            )
            created.append(f.ticker)
        else:
            if not comp.name:
                comp.name = f.name
            if comp.asset_type != "etf":
                comp.asset_type = "etf"
            if not comp.extra_source:
                comp.extra_source = "curated"
    if created:
        session.commit()
    return created


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
    if period not in PERIODS:
        raise ValueError(f"unsupported period '{period}'")
    from app.providers.vistashares_meta import fetch_fund_meta

    ensure_vistashares_companies(session)
    funds = [f for f in VISTASHARES_FUNDS if family is None or f.family == family]
    tickers = [f.ticker for f in funds]
    _ensure_holdings(session, tickers)
    meta = fetch_fund_meta()
    snaps = {
        s.ticker: s for s in session.scalars(select(EtfHoldingsSnapshot).where(EtfHoldingsSnapshot.ticker.in_(tickers)))
    }
    comps = {c.ticker: c for c in session.scalars(select(Company).where(Company.ticker.in_(tickers)))}
    metrics = {
        m.ticker: m for m in session.scalars(select(MetricsSnapshot).where(MetricsSnapshot.ticker.in_(tickers)))
    }
    aums = [
        _resolve_aum(snaps.get(f.ticker), metrics.get(f.ticker), meta.get(f.ticker).aum if meta.get(f.ticker) else None)
        or 0
        for f in funds
    ]
    max_aum = max(aums) if aums else 1.0
    by_family: dict[str, list] = {fid: [] for fid, _ in FAMILIES}
    for f in funds:
        c = comps.get(f.ticker)
        snap = snaps.get(f.ticker)
        m = metrics.get(f.ticker)
        aum = _resolve_aum(snap, m, meta.get(f.ticker).aum if meta.get(f.ticker) else None)
        if c:
            tile = _etf_tile(c, m, snap, period, max_aum)
            if aum and not tile.get("aum"):
                tile["aum"] = aum
                tile["size"] = _map_size(aum, max_aum)
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
                "size": _map_size(aum, max_aum),
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
    if flat:
        max_aum = max((x.get("aum") or 0) for x in flat) or 1.0
        for x in flat:
            x["size"] = _map_size(x.get("aum"), max_aum)
    return {
        "period": period,
        "families": [{"id": fid, "name": label} for fid, label in FAMILIES],
        "groups": groups,
        "etfs": flat,
    }


def refresh_etfs(session: Session, tickers: list[str]) -> dict:
    refreshed = []
    for raw in tickers:
        t = raw.strip().upper()
        if not t:
            continue
        fetch_and_store_holdings(session, t, force=True)
        fund_heatmap(session, t, period="wow", force=True)
        refreshed.append(t)
    return {"refreshed": refreshed}
