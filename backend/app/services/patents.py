"""Patents per company: granted (last 10 years) and published applications (last 24 months)."""

import re
from collections import Counter
from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import Company, Patent, PatentAssigneeMap, PatentStat
from app.providers import registry
from app.providers.base import PatentRecord
from app.providers.patents_patentsview import Assignee

GRANTED_YEARS = 10
APPLICATION_MONTHS = 24
RECENT_GRANTED = 50
RECENT_APPLICATIONS = 100
CPC_SAMPLE = 1000

# Patent assignees are legal entities that rarely match the listed company name.
CURATED_ASSIGNEES: dict[str, list[tuple[str, str]]] = {
    "GOOGL": [("Google LLC", "exact"), ("Google Inc.", "exact"), ("DeepMind Technologies Limited", "exact"), ("Waymo LLC", "exact")],
    "GOOG": [("Google LLC", "exact"), ("Google Inc.", "exact")],
    "META": [("Meta Platforms, Inc.", "exact"), ("Facebook, Inc.", "exact"), ("Meta Platforms Technologies, LLC", "exact"),
             ("Facebook Technologies, LLC", "exact")],
    "MSFT": [("Microsoft Technology Licensing, LLC", "exact"), ("Microsoft Corporation", "exact")],
    "AMZN": [("Amazon Technologies, Inc.", "exact"), ("Amazon.com, Inc.", "exact")],
    "AAPL": [("Apple Inc.", "exact")],
    "IBM": [("International Business Machines Corporation", "exact")],
    "QCOM": [("QUALCOMM Incorporated", "exact")],
    "INTC": [("Intel Corporation", "exact")],
    "NVDA": [("NVIDIA Corporation", "exact")],
    "AMD": [("Advanced Micro Devices, Inc.", "exact"), ("ATI Technologies ULC", "exact")],
    "CSCO": [("Cisco Technology, Inc.", "exact")],
    "TSLA": [("Tesla, Inc.", "exact")],
    "GE": [("General Electric Company", "exact")],
    "JNJ": [("Johnson & Johnson", "exact"), ("Janssen Pharmaceutica NV", "exact"), ("Ethicon LLC", "exact")],
}
CPC_SECTIONS = {
    "A": "Human necessities", "B": "Operations and transport", "C": "Chemistry and metallurgy", "D": "Textiles and paper",
    "E": "Fixed constructions", "F": "Mechanical engineering", "G": "Physics and computing", "H": "Electricity",
    "Y": "Emerging cross-sectional technologies",
}
CPC_SUBCLASSES = {
    "G06F": "Electric digital data processing", "G06N": "AI and machine learning", "G06T": "Image processing",
    "G06Q": "Business data processing", "G06V": "Image and video recognition", "G06K": "Data recognition",
    "H04L": "Digital data transmission", "H04W": "Wireless networks", "H04N": "Video and image communication",
    "H04B": "Transmission", "H04M": "Telephonic communication", "H04R": "Loudspeakers and microphones",
    "H01L": "Semiconductor devices", "H10B": "Electronic memory devices", "H10D": "Semiconductor devices",
    "H01M": "Batteries", "H02J": "Power supply and distribution", "G02B": "Optical elements", "G09G": "Display control",
    "G11C": "Static memory", "G01S": "Radar, sonar and lidar", "G05D": "Vehicle control systems", "G10L": "Speech processing",
    "A61B": "Medical diagnosis and surgery", "A61K": "Medical preparations", "A61P": "Therapeutic activity of compounds",
    "A61M": "Medical devices", "A61F": "Prostheses and implants", "C07K": "Peptides", "C07D": "Heterocyclic compounds",
    "C12N": "Microorganisms and enzymes", "C12Q": "Measuring with enzymes or microorganisms", "B60L": "Electric vehicle propulsion",
    "B60W": "Vehicle drive control", "B62D": "Motor vehicles", "F02C": "Gas turbine plants", "F01D": "Turbine engines",
    "B64C": "Aircraft", "Y02E": "Clean energy technologies", "Y02T": "Climate-friendly transport", "Y10S": "Former USPC art collections",
}
SUFFIXES = re.compile(r"[,.]?\s+(inc|incorporated|corp|corporation|company|co|ltd|limited|plc|llc|n\.v|s\.a|ag|se|holdings?|group|the)\.?$", re.I)


def core_name(name: str) -> str:
    out = re.sub(r"\s+", " ", name.replace("&amp;", "&")).strip()
    while True:
        stripped = SUFFIXES.sub("", out).strip(" ,.")
        if stripped == out or not stripped:
            return out
        out = stripped


def default_assignees(ticker: str, name: str) -> list[tuple[str, str]]:
    if ticker in CURATED_ASSIGNEES:
        return CURATED_ASSIGNEES[ticker]
    core = core_name(name)
    # Exact legal name plus a prefix on "<core> " (the trailing space avoids "Apple" -> "Applied Materials").
    pairs = [(name, "exact"), (f"{core} ", "prefix")]
    return pairs if core != name else [(name, "exact")]


def ensure_assignee_map(session: Session, ticker: str) -> list[PatentAssigneeMap]:
    rows = session.scalars(select(PatentAssigneeMap).where(PatentAssigneeMap.ticker == ticker)).all()
    if rows:
        return list(rows)
    comp = session.get(Company, ticker)
    source = "curated" if ticker in CURATED_ASSIGNEES else "auto"
    for name, match in default_assignees(ticker, comp.name if comp else ticker):
        session.add(PatentAssigneeMap(ticker=ticker, assignee_name=name, match=match, source=source))
    session.commit()
    return list(session.scalars(select(PatentAssigneeMap).where(PatentAssigneeMap.ticker == ticker)))


def set_assignees(session: Session, ticker: str, items: list[dict]) -> list[PatentAssigneeMap]:
    session.execute(delete(PatentAssigneeMap).where(PatentAssigneeMap.ticker == ticker))
    seen = set()
    for it in items:
        name = (it.get("assignee_name") or "").strip()
        match = it.get("match", "exact")
        if not name or (name, match) in seen:
            continue
        seen.add((name, match))
        stored = name if match == "exact" else f"{name.rstrip()} "
        session.add(PatentAssigneeMap(ticker=ticker, assignee_name=stored, match=match, source="manual"))
    session.commit()
    return list(session.scalars(select(PatentAssigneeMap).where(PatentAssigneeMap.ticker == ticker)))


def cpc_title(code: str) -> str:
    return CPC_SUBCLASSES.get(code) or CPC_SECTIONS.get(code[:1], "Other")


def store_patents(session: Session, ticker: str, kind: str, records: list[PatentRecord], source: str, keep: int) -> None:
    session.execute(delete(Patent).where(Patent.ticker == ticker, Patent.kind == kind))
    seen = set()
    for r in sorted(records, key=lambda r: r.date or date.min, reverse=True):
        if r.number in seen:
            continue
        seen.add(r.number)
        if len(seen) > keep:
            break
        session.add(Patent(id=f"{kind[0]}:{r.number}:{ticker}", ticker=ticker, kind=kind, number=r.number, title=r.title,
                           abstract=r.abstract, date=r.date, cpc_class=r.cpc_class, assignee_name=r.assignee_name,
                           source=source))


def store_stats(session: Session, ticker: str, kind: str, dimension: str, counts: dict[str, int], note: str | None = None) -> None:
    session.execute(delete(PatentStat).where(PatentStat.ticker == ticker, PatentStat.kind == kind,
                                             PatentStat.dimension == dimension))
    for key, n in counts.items():
        session.add(PatentStat(ticker=ticker, kind=kind, dimension=dimension, key=key, count=n, note=note))


def refresh_patents(session: Session, ticker: str, today: date | None = None) -> None:
    today = today or date.today()
    api = registry.patents()
    assignees = [Assignee(a.assignee_name, a.match) for a in ensure_assignee_map(session, ticker)]
    first_year = today.year - GRANTED_YEARS + 1
    years = {str(y): api.count("granted", assignees, date(y, 1, 1), date(y, 12, 31)) for y in range(first_year, today.year + 1)}
    granted, _ = api.search("granted", assignees, date(first_year, 1, 1), CPC_SAMPLE)
    app_start = date(today.year - APPLICATION_MONTHS // 12, today.month, 1)
    applications, app_total = api.search("application", assignees, app_start, RECENT_APPLICATIONS)

    store_patents(session, ticker, "granted", granted, "patentsview_api", RECENT_GRANTED)
    store_patents(session, ticker, "application", applications, "patentsview_api", RECENT_APPLICATIONS)
    store_stats(session, ticker, "granted", "year", years)
    store_stats(session, ticker, "granted", "cpc", dict(Counter(r.cpc_class for r in granted if r.cpc_class)),
                note=f"based on the {len(granted)} most recent grants")
    store_stats(session, ticker, "application", "total", {"24m": app_total})
    store_stats(session, ticker, "application", "cpc", dict(Counter(r.cpc_class for r in applications if r.cpc_class)),
                note=f"based on the {len(applications)} most recent publications")
    session.commit()


def import_bulk(session: Session, directory, tickers: list[str] | None = None, today: date | None = None) -> dict[str, int]:
    """Load PatentsView bulk TSVs for every company (or `tickers`); exact counts since all records are local."""
    from pathlib import Path

    from app.providers.patents_bulk import import_directory
    from app.services.ingest import universe_tickers
    from app.services.refresh import record_fetch

    today = today or date.today()
    tickers = tickers or universe_tickers(session, include_benchmarks=False)
    rows = []
    for t in tickers:
        rows.extend((t, a.assignee_name, a.match) for a in ensure_assignee_map(session, t))
    first_year = today.year - GRANTED_YEARS + 1
    app_start = date(today.year - APPLICATION_MONTHS // 12, today.month, 1)
    result = import_directory(Path(directory), rows, date(first_year, 1, 1), app_start)

    imported: dict[str, int] = {}
    for kind, by_ticker in result.items():
        for t in tickers:
            records = by_ticker.get(t, [])
            keep = RECENT_GRANTED if kind == "granted" else RECENT_APPLICATIONS
            store_patents(session, t, kind, records, "patentsview_bulk", keep)
            store_stats(session, t, kind, "cpc", dict(Counter(r.cpc_class for r in records if r.cpc_class)),
                        note=f"all {len(records)} {'grants' if kind == 'granted' else 'publications'} in the bulk files")
            if kind == "granted":
                years = Counter(str(r.date.year) for r in records if r.date)
                store_stats(session, t, kind, "year", {str(y): years.get(str(y), 0) for y in range(first_year, today.year + 1)})
            else:
                store_stats(session, t, kind, "total", {"24m": len(records)})
            imported[t] = imported.get(t, 0) + len(records)
        session.commit()
    for t in tickers:
        record_fetch(session, "patents", t, "patentsview_bulk", message=f"{imported.get(t, 0)} records")
    return imported


def _patent_out(p: Patent) -> dict:
    if p.kind == "granted":
        url = f"https://patents.google.com/patent/US{p.number}"
    else:
        url = f"https://patents.google.com/patent/US{p.number}A1"
    return {"number": p.number, "title": p.title, "abstract": p.abstract, "date": p.date.isoformat() if p.date else None,
            "cpc_class": p.cpc_class, "cpc_title": cpc_title(p.cpc_class) if p.cpc_class else None,
            "assignee": p.assignee_name, "url": url, "source": p.source}


def patents_payload(session: Session, ticker: str) -> dict:
    stats = session.scalars(select(PatentStat).where(PatentStat.ticker == ticker)).all()

    def stat(kind: str, dim: str) -> list[PatentStat]:
        return [s for s in stats if s.kind == kind and s.dimension == dim]

    def cpc(kind: str) -> dict:
        rows = sorted(stat(kind, "cpc"), key=lambda s: -s.count)[:10]
        return {"items": [{"code": s.key, "title": cpc_title(s.key), "count": s.count} for s in rows],
                "note": rows[0].note if rows else None}

    by_year = sorted(({"year": s.key, "count": s.count} for s in stat("granted", "year")), key=lambda r: r["year"])
    patents = session.scalars(select(Patent).where(Patent.ticker == ticker).order_by(Patent.date.desc())).all()
    app_total = next((s.count for s in stat("application", "total")), None)
    assignees = session.scalars(select(PatentAssigneeMap).where(PatentAssigneeMap.ticker == ticker)).all()
    return {
        "granted": {
            "total_10y": sum(r["count"] for r in by_year) if by_year else None,
            "by_year": by_year,
            "top_cpc": cpc("granted"),
            "recent": [_patent_out(p) for p in patents if p.kind == "granted"],
        },
        "applications": {
            "total_24m": app_total,
            "top_cpc": cpc("application"),
            "recent": [_patent_out(p) for p in patents if p.kind == "application"],
        },
        "assignees": [{"assignee_name": a.assignee_name.strip(), "match": a.match, "source": a.source} for a in assignees],
        "source": patents[0].source if patents else None,
    }
