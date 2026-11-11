"""Global presence: subsidiaries by country (10-K Exhibit 21) and revenue by region (10-K XBRL instance)."""

import re
from collections import Counter, defaultdict
from datetime import date

from bs4 import BeautifulSoup
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import Company, GeoRevenue, Subsidiary
from app.providers import registry
from app.providers.sec_edgar import REVENUE_CONCEPTS, find_exhibit21, find_instance_document
from app.providers.xbrl import Fact, parse_instance, to_float
from app.services.countries import country_from_xbrl_member, resolve_country

GEO_AXES = ("srt:StatementGeographicalAxis", "us-gaap:StatementGeographicalAxis")
SEGMENT_AXIS = "us-gaap:StatementBusinessSegmentsAxis"
GEO_WORDS = re.compile(
    r"america|europe|asia|pacific|china|japan|emea|apac|international|domestic|latin|middle east|africa|india|"
    r"canada|mexico|united states|u\.?s\.?|non.?us|foreign|rest of world|other countries|greater|korea|taiwan|"
    r"germany|france|united kingdom|australia|brazil|region",
    re.I,
)
HEADER_WORDS = re.compile(
    r"jurisdiction|name of (subsidiary|entity|company)|state or other|"
    r"(state|place|country) of (organization|incorporation|formation)|where incorporated|organized under|laws of|"
    r"^subsidiar(y|ies)( of|$)|(^|\s)name$",
    re.I,
)
SUBTOTAL = re.compile(r"^(total|subtotal)\b", re.I)


def parse_exhibit21(html: str) -> list[tuple[str, str | None]]:
    """Return (subsidiary name, raw jurisdiction) pairs from Exhibit 21 HTML or text."""
    soup = BeautifulSoup(html, "lxml")
    for el in soup(["script", "style"]):
        el.decompose()
    out: list[tuple[str, str | None]] = []
    for tr in soup.find_all("tr"):
        cells = [re.sub(r"\s+", " ", td.get_text(" ", strip=True)).strip() for td in tr.find_all(["td", "th"])]
        cells = [c for c in cells if c and c not in ("*", "†")]
        if len(cells) < 2:
            continue
        name, jur = cells[0], cells[-1]
        if HEADER_WORDS.search(name) or HEADER_WORDS.search(jur) or len(name) > 200:
            continue
        out.append((name.rstrip("*† "), jur))
    if out:
        return out

    section: str | None = None
    for raw in soup.get_text("\n").splitlines():
        line = re.sub(r"\s+", " ", raw).strip()
        if not line or len(line) > 250 or HEADER_WORDS.search(line) or line.lower().startswith(("exhibit", "*", "pursuant")):
            continue
        if line.endswith(":") and resolve_country(line[:-1]):
            section = line[:-1]
            continue
        m = re.match(r"^(.*\S)\s*\(([^()]+)\)\s*$", line) or re.match(r"^(.*\S)\s+[–—-]\s+(.+)$", line)
        if m and resolve_country(m.group(2)):
            out.append((m.group(1).strip(), m.group(2).strip()))
        elif section:
            out.append((line, section))
    return out


def humanize_member(member: str) -> str:
    country = country_from_xbrl_member(member)
    if country:
        return country.name
    local = member.split(":", 1)[-1]
    local = re.sub(r"(Segment)?Member$", "", local)
    local = re.sub(r"(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", " ", local)
    return local.replace("Non Us", "Non-US").replace("Usand", "US and").strip() or member


NEUTRAL_DIMS = {("srt:ConsolidationItemsAxis", "us-gaap:OperatingSegmentsMember")}


def _dims(f: Fact) -> dict[str, str]:
    """Context dimensions minus ones that do not change the meaning (segment facts are tagged as operating segments)."""
    return {k: v for k, v in f.context.dims.items() if (k, v) not in NEUTRAL_DIMS}


def _member(f: Fact) -> str:
    return next(iter(_dims(f).values()))


def extract_geo_revenue(facts: list[Fact]) -> list[dict]:
    """Full-year revenue facts that carry exactly one geographic dimension. Falls back to business segments when
    every segment member is geographic (e.g. Apple reports Americas / Europe / Greater China as segments)."""
    def candidates(axis_ok) -> dict[str, list[Fact]]:
        by_concept: dict[str, list[Fact]] = defaultdict(list)
        for f in facts:
            dims = _dims(f)
            if (f.prefix == "us-gaap" and f.name in REVENUE_CONCEPTS and len(dims) == 1 and axis_ok(next(iter(dims)))
                    and (f.context.duration_days or 0) >= 330 and to_float(f.value) is not None):
                by_concept[f.name].append(f)
        return by_concept

    rows: list[dict] = []
    for axis_label, axis_ok in (("geographic", lambda a: a in GEO_AXES), ("segment", lambda a: a == SEGMENT_AXIS)):
        by_concept = candidates(axis_ok)
        if not by_concept:
            continue
        concept = max(by_concept, key=lambda c: len({_member(f) for f in by_concept[c]}))
        chosen = by_concept[concept]
        members = {_member(f) for f in chosen}
        if axis_label == "segment" and not all(GEO_WORDS.search(humanize_member(m)) for m in members):
            continue
        seen: set[tuple[date, str]] = set()
        for f in chosen:
            member = _member(f)
            key = (f.context.end, member)
            if key in seen or SUBTOTAL.match(humanize_member(member)):
                continue
            seen.add(key)
            country = country_from_xbrl_member(member)
            rows.append({"period_end": f.context.end, "member": member, "region": humanize_member(member),
                         "axis": axis_label, "concept": concept, "revenue": to_float(f.value),
                         "country_alpha2": country.alpha2 if country else None})
    return rows


def store_subsidiaries(session: Session, ticker: str, pairs: list[tuple[str, str | None]], accession: str | None) -> int:
    session.execute(delete(Subsidiary).where(Subsidiary.ticker == ticker))
    seen = set()
    for name, jur in pairs:
        if (name, jur) in seen:
            continue
        seen.add((name, jur))
        c = resolve_country(jur)
        session.add(Subsidiary(ticker=ticker, name=name[:300], jurisdiction=(jur or "")[:200] or None,
                               country_name=c.name if c else None, country_alpha2=c.alpha2 if c else None,
                               country_numeric=c.numeric if c else None, filing_accession=accession))
    session.commit()
    return len(seen)


def store_geo_revenue(session: Session, ticker: str, rows: list[dict], accession: str | None) -> int:
    session.execute(delete(GeoRevenue).where(GeoRevenue.ticker == ticker))
    for r in rows:
        session.add(GeoRevenue(ticker=ticker, filing_accession=accession, **r))
    session.commit()
    return len(rows)


def refresh_global(session: Session, ticker: str) -> None:
    comp = session.get(Company, ticker)
    if comp is None or not comp.cik:
        raise ValueError(f"{ticker} has no SEC CIK")
    sec = registry.sec()
    filing = sec.latest_filing(comp.cik, ("10-K", "10-K/A", "20-F"))
    if filing is None:
        raise RuntimeError("no annual report found on EDGAR")
    entries = sec.filing_index(comp.cik, filing)
    ex21 = find_exhibit21(entries)
    pairs = parse_exhibit21(sec.document(comp.cik, filing, ex21).decode("utf-8", "replace")) if ex21 else []
    store_subsidiaries(session, ticker, pairs, filing.accession)
    instance = find_instance_document(entries)
    rows = extract_geo_revenue(parse_instance(sec.document(comp.cik, filing, instance))) if instance else []
    store_geo_revenue(session, ticker, rows, filing.accession)


def global_payload(session: Session, ticker: str, cik: str | None) -> dict:
    subs = session.scalars(select(Subsidiary).where(Subsidiary.ticker == ticker).order_by(Subsidiary.name)).all()
    counts = Counter((s.country_name, s.country_alpha2, s.country_numeric) for s in subs if s.country_alpha2)
    geo = session.scalars(select(GeoRevenue).where(GeoRevenue.ticker == ticker)).all()
    periods: dict[tuple[str, date], list[GeoRevenue]] = defaultdict(list)
    for g in geo:
        periods[(g.axis, g.period_end)].append(g)
    revenue = []
    # geographic axis first, newest period first within each axis
    for (axis, end), items in sorted(periods.items(), key=lambda kv: (kv[0][0] != "geographic", -kv[0][1].toordinal())):
        total = sum(i.revenue for i in items) or None
        revenue.append({
            "axis": axis,
            "period_end": end.isoformat(),
            "total": total,
            "regions": sorted(
                [{"region": i.region, "member": i.member, "revenue": i.revenue, "country_alpha2": i.country_alpha2,
                  "share_pct": (i.revenue / total * 100) if total else None} for i in items],
                key=lambda r: -r["revenue"],
            ),
        })
    accession = subs[0].filing_accession if subs else (geo[0].filing_accession if geo else None)
    filing_url = (f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace('-', '')}/{accession}-index.htm"
                  if accession and cik else None)
    return {
        "subsidiaries": [{"name": s.name, "jurisdiction": s.jurisdiction, "country_name": s.country_name,
                          "country_alpha2": s.country_alpha2} for s in subs],
        "countries": [{"country_name": n, "alpha2": a, "numeric": num, "count": c}
                      for (n, a, num), c in counts.most_common()],
        "unmapped": sum(1 for s in subs if not s.country_alpha2),
        "revenue_by_region": revenue,
        "filing": {"accession": accession, "url": filing_url},
    }
