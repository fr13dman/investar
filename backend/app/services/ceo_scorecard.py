"""CEO scorecard: return during tenure vs SPY, revenue/EPS/margin growth during tenure, and pay vs performance."""

import logging
import re
from collections import defaultdict
from datetime import date, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import CeoOverride, CeoScorecard, Company, Executive, FinancialFact, PriceDaily, StockSplit
from app.providers import registry
from app.providers.sec_edgar import EPS_CONCEPTS, NET_INCOME_CONCEPTS, REVENUE_CONCEPTS, annual_facts, find_instance_document
from app.providers.wikidata import Tenure
from app.providers.xbrl import Fact, parse_instance, to_float

log = logging.getLogger(__name__)
HONORIFICS = re.compile(r"^(mr|mrs|ms|mx|dr|prof|sir|dame)\.?\s+", re.I)
PVP_FIELDS = {
    "PeoTotalCompAmt": "peo_total_comp",
    "PeoActuallyPaidCompAmt": "peo_comp_actually_paid",
    "TotalShareholderRtnAmt": "tsr_value",
    "PeerGroupTotalShareholderRtnAmt": "peer_tsr_value",
    "NetIncomeLoss": "net_income",
}
METRIC_CONCEPTS = {"revenue": (REVENUE_CONCEPTS, "USD"), "eps": (EPS_CONCEPTS, "USD/shares"),
                   "net_income": (NET_INCOME_CONCEPTS, "USD")}


def clean_name(name: str | None) -> str | None:
    if not name:
        return None
    return HONORIFICS.sub("", " ".join(name.split())).strip()


def _tokens(name: str) -> set[str]:
    return {t for t in re.findall(r"[a-z]+", name.lower()) if len(t) > 1}


def names_match(a: str | None, b: str | None) -> bool:
    if not a or not b:
        return False
    ta, tb = _tokens(clean_name(a) or ""), _tokens(clean_name(b) or "")
    if not ta or not tb:
        return False
    # Candidates come from a single company's CEO history, so a shared surname is enough ("Tim" vs "Timothy").
    last_a, last_b = re.findall(r"[a-z]+", a.lower())[-1], re.findall(r"[a-z]+", b.lower())[-1]
    return last_a == last_b or ta <= tb or tb <= ta


def resolve_ceo(override: CeoOverride | None, exec_name: str | None, tenures: list[Tenure]) -> tuple[str | None, date | None, str | None]:
    """Returns (ceo_name, tenure_start, tenure_source)."""
    name = clean_name(override.ceo_name if override and override.ceo_name else exec_name)
    current = [t for t in tenures if t.end is None]
    if not name and current:
        name = current[-1].name
    start, source = None, None
    if override and override.tenure_start:
        return name, override.tenure_start, "manual"
    matches = [t for t in tenures if names_match(t.name, name) and t.start]
    if matches:
        open_matches = [t for t in matches if t.end is None] or matches
        start, source = max(t.start for t in open_matches), "wikidata"
    else:
        # Very new CEOs often lack an English label on Wikidata (the label is the bare Q-id).
        unlabeled = [t for t in current if t.start and re.fullmatch(r"Q\d+", t.name)]
        if unlabeled:
            start, source = max(t.start for t in unlabeled), "wikidata-unlabeled"
    return name, start, source


def parse_pay_vs_performance(facts: list[Fact]) -> list[dict]:
    rows: dict[date, dict] = defaultdict(dict)
    for f in facts:
        field = PVP_FIELDS.get(f.name)
        if field and f.prefix in ("ecd", "us-gaap") and not f.context.dims and f.context.end:
            if field == "net_income" and f.prefix != "us-gaap":
                continue
            value = to_float(f.value)
            if value is not None:
                rows[f.context.end][field] = value
        elif f.name == "PeoName" and f.context.end and f.context.dims.get("ecd:ExecutiveCategoryAxis", "").endswith("PeoMember"):
            rows[f.context.end].setdefault("peo_names", [])
            if f.value not in rows[f.context.end]["peo_names"]:
                rows[f.context.end]["peo_names"].append(f.value)
    return [
        {"fiscal_year_end": end.isoformat(), **vals}
        for end, vals in sorted(rows.items(), reverse=True)
        if any(k in vals for k in ("peo_total_comp", "peo_comp_actually_paid"))
    ]


def _cagr(start: float | None, end: float | None, years: float) -> float | None:
    if not start or not end or start <= 0 or end <= 0 or years <= 0:
        return None
    return ((end / start) ** (1 / years) - 1) * 100


def split_factor(splits: list[tuple[date, float]], as_of: date) -> float:
    """Cumulative split ratio after `as_of`: divide an as-reported per-share value by this to get today's basis."""
    factor = 1.0
    for d, ratio in splits:
        if d > as_of:
            factor *= ratio
    return factor


def fundamentals_table(session: Session, ticker: str) -> list[dict]:
    facts = session.scalars(select(FinancialFact).where(FinancialFact.ticker == ticker)).all()
    splits = [(s.date, s.ratio) for s in session.scalars(select(StockSplit).where(StockSplit.ticker == ticker))]
    rows: dict[date, dict] = defaultdict(dict)
    for f in facts:
        for key, (concepts, unit) in METRIC_CONCEPTS.items():
            if f.concept in concepts and f.unit == unit:
                value = f.value
                if key == "eps":  # SEC values are as reported; restate older EPS for later splits
                    value = value / split_factor(splits, f.filed or f.period_end)
                rows[f.period_end][key] = value
    out = []
    for end in sorted(rows):
        r = rows[end]
        margin = (r["net_income"] / r["revenue"] * 100) if r.get("net_income") is not None and r.get("revenue") else None
        out.append({"fiscal_year_end": end.isoformat(), "revenue": r.get("revenue"), "eps": r.get("eps"),
                    "net_income": r.get("net_income"), "net_margin_pct": margin})
    return out


def _window_return(session: Session, ticker: str, start: date | None) -> tuple[date | None, date | None, float | None]:
    q = select(PriceDaily.date, PriceDaily.adj_close, PriceDaily.close).where(PriceDaily.ticker == ticker)
    if start:
        q = q.where(PriceDaily.date >= start)
    first = session.execute(q.order_by(PriceDaily.date.asc()).limit(1)).first()
    last = session.execute(q.order_by(PriceDaily.date.desc()).limit(1)).first()
    if not first or not last or first.date == last.date:
        return None, None, None
    p0, p1 = (first.adj_close or first.close), (last.adj_close or last.close)
    return first.date, last.date, (p1 / p0 - 1) * 100 if p0 else None


def _annualize(total_pct: float | None, start: date | None, end: date | None) -> float | None:
    if total_pct is None or not start or not end or (end - start).days < 30:
        return None
    return ((1 + total_pct / 100) ** (365.25 / (end - start).days) - 1) * 100


def compute_scorecard(session: Session, ticker: str, tenures: list[Tenure], pvp: list[dict]) -> CeoScorecard:
    override = session.get(CeoOverride, ticker)
    exec_row = session.scalars(select(Executive).where(Executive.ticker == ticker, Executive.is_ceo)).first()
    name, tenure_start, source = resolve_ceo(override, exec_row.name if exec_row else None, tenures)

    first_bar = session.scalar(select(PriceDaily.date).where(PriceDaily.ticker == ticker).order_by(PriceDaily.date).limit(1))
    window_from = tenure_start if tenure_start and (not first_bar or tenure_start >= first_bar) else first_bar
    w_start, w_end, tsr = _window_return(session, ticker, window_from)
    _, _, spy = _window_return(session, "SPY", w_start)

    fundamentals = fundamentals_table(session, ticker)
    base = None
    if fundamentals:
        before = [r for r in fundamentals if tenure_start and date.fromisoformat(r["fiscal_year_end"]) <= tenure_start]
        base = before[-1] if before else fundamentals[0]
    latest = fundamentals[-1] if fundamentals else None
    years = ((date.fromisoformat(latest["fiscal_year_end"]) - date.fromisoformat(base["fiscal_year_end"])).days / 365.25
             if base and latest else 0)

    card = session.get(CeoScorecard, ticker) or CeoScorecard(ticker=ticker)
    card.ceo_name = name
    card.tenure_start = tenure_start
    card.tenure_source = source
    card.tenures = [{"name": t.name, "start": t.start.isoformat() if t.start else None,
                     "end": t.end.isoformat() if t.end else None} for t in tenures]
    card.window_start = w_start
    card.window_truncated = bool(tenure_start is None or (w_start and tenure_start < w_start))
    card.tsr_pct = tsr
    card.spy_tsr_pct = spy
    card.excess_return_pct = tsr - spy if tsr is not None and spy is not None else None
    card.tsr_annualized_pct = _annualize(tsr, w_start, w_end)
    card.spy_annualized_pct = _annualize(spy, w_start, w_end)
    card.revenue_cagr_pct = _cagr(base and base["revenue"], latest and latest["revenue"], years) if base is not latest else None
    card.eps_cagr_pct = _cagr(base and base["eps"], latest and latest["eps"], years) if base is not latest else None
    card.margin_start_pct = base["net_margin_pct"] if base else None
    card.margin_end_pct = latest["net_margin_pct"] if latest else None
    card.fundamentals = fundamentals
    card.pay_vs_performance = pvp
    card.computed_at = datetime.now()
    session.add(card)
    session.commit()
    return card


def store_financial_facts(session: Session, ticker: str, companyfacts: dict) -> int:
    session.execute(delete(FinancialFact).where(FinancialFact.ticker == ticker))
    n = 0
    for concepts, unit in METRIC_CONCEPTS.values():
        for f in annual_facts(companyfacts, concepts, unit):
            session.add(FinancialFact(ticker=ticker, concept=f.concept, period_end=f.end, unit=unit,
                                      period_start=f.start, value=f.value, form=f.form, filed=f.filed))
            n += 1
    session.commit()
    return n


def store_splits(session: Session, ticker: str, splits: list[tuple[date, float]]) -> None:
    session.execute(delete(StockSplit).where(StockSplit.ticker == ticker))
    for d, ratio in splits:
        session.add(StockSplit(ticker=ticker, date=d, ratio=ratio))
    session.commit()


def fetch_pay_vs_performance(cik: str) -> list[dict]:
    sec = registry.sec()
    filing = sec.latest_filing(cik, ("DEF 14A",))
    if not filing:
        return []
    instance = find_instance_document(sec.filing_index(cik, filing))
    if not instance:
        return []
    return parse_pay_vs_performance(parse_instance(sec.document(cik, filing, instance)))


def refresh_ceo(session: Session, ticker: str) -> CeoScorecard:
    comp = session.get(Company, ticker)
    if comp is None or not comp.cik:
        raise ValueError(f"{ticker} has no SEC CIK")
    store_financial_facts(session, ticker, registry.sec().company_facts(comp.cik))
    try:
        store_splits(session, ticker, registry.prices().splits(ticker))
    except Exception as exc:  # noqa: BLE001
        log.warning("split history unavailable for %s: %s", ticker, exc)
    try:
        tenures = registry.wikidata().ceo_tenures(comp.cik)
    except Exception as exc:  # noqa: BLE001
        log.warning("wikidata lookup failed for %s: %s", ticker, exc)
        tenures = []
    try:
        pvp = fetch_pay_vs_performance(comp.cik)
    except Exception as exc:  # noqa: BLE001
        log.warning("pay-vs-performance fetch failed for %s: %s", ticker, exc)
        pvp = []
    return compute_scorecard(session, ticker, tenures, pvp)


def recompute_from_stored(session: Session, ticker: str) -> CeoScorecard:
    """Recompute after a manual override without hitting the network."""
    card = session.get(CeoScorecard, ticker)
    tenures = [
        Tenure(t["name"], date.fromisoformat(t["start"]) if t.get("start") else None,
               date.fromisoformat(t["end"]) if t.get("end") else None)
        for t in (card.tenures or [])
    ] if card else []
    return compute_scorecard(session, ticker, tenures, (card.pay_vs_performance if card else None) or [])
