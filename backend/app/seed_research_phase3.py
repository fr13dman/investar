"""Demo global-presence and patent data (offline)."""

from collections import Counter
from datetime import date, datetime, timedelta

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models import FetchLog, GeoRevenue, Patent, PatentAssigneeMap, PatentStat, Subsidiary
from app.providers.base import PatentRecord
from app.seed import DEMO_COMPANIES
from app.services.global_presence import store_subsidiaries
from app.services.patents import ensure_assignee_map, store_patents, store_stats

SUBSIDIARIES = {
    "AAPL": [("Demo Apple Operations International", "Ireland"), ("Demo Apple Distribution", "Ireland"),
             ("Demo Apple Japan", "Japan"), ("Demo Apple India", "India"), ("Demo Apple Europe", "United Kingdom"),
             ("Demo Braeburn Capital", "Nevada, U.S."), ("Demo Apple Asia", "Hong Kong"), ("Demo Apple Brasil", "Brazil")],
    "NVDA": [("Demo NVIDIA International", "Cayman Islands"), ("Demo NVIDIA Israel", "Israel"),
             ("Demo NVIDIA Taiwan", "Taiwan"), ("Demo NVIDIA US Holdings", "Delaware")],
}
GEO = {
    "AAPL": [("country:US", "United States", "US", 167.7e9), ("country:CN", "China", "CN", 82.4e9),
             ("aapl:OtherCountriesMember", "Other Countries", None, 228.7e9)],
    "NVDA": [("country:US", "United States", "US", 60.2e9), ("country:TW", "Taiwan", "TW", 30.1e9),
             ("nvda:OtherCountriesMember", "Other Countries", None, 40.0e9)],
}
PATENT_TOPICS = [
    ("G06F", "Low-power processor scheduling"), ("H04W", "Adaptive wireless handoff"), ("G06N", "On-device neural inference"),
    ("G06T", "Real-time image upscaling"), ("H01L", "Stacked chip packaging"),
]


def seed_phase3(session: Session, now: datetime) -> None:
    for model in (Subsidiary, GeoRevenue, Patent, PatentStat, PatentAssigneeMap):
        session.execute(delete(model))
    session.commit()
    today = now.date()
    for ticker, pairs in SUBSIDIARIES.items():
        store_subsidiaries(session, ticker, pairs, "0000000000-26-000001")
    for ticker, rows in GEO.items():
        for member, region, alpha2, revenue in rows:
            session.add(GeoRevenue(ticker=ticker, period_end=date(today.year - 1, 9, 30), region=region, member=member,
                                   axis="geographic", country_alpha2=alpha2, revenue=revenue, concept="Revenues",
                                   filing_accession="0000000000-26-000001"))
    for i, ticker in enumerate(("AAPL", "NVDA")):
        ensure_assignee_map(session, ticker)
        granted = [PatentRecord("granted", str(12_100_000 + i * 1000 + n), f"{PATENT_TOPICS[n % 5][1]} ({n + 1})",
                                f"Demo abstract describing {PATENT_TOPICS[n % 5][1].lower()}.", today - timedelta(days=7 * n),
                                PATENT_TOPICS[n % 5][0], None) for n in range(60)]
        apps = [PatentRecord("application", str(20_260_100_000 + i * 1000 + n), f"Pending: {PATENT_TOPICS[(n + 2) % 5][1]}",
                             None, today - timedelta(days=10 * n), PATENT_TOPICS[(n + 2) % 5][0], None) for n in range(25)]
        store_patents(session, ticker, "granted", granted, "patentsview_api", 50)
        store_patents(session, ticker, "application", apps, "patentsview_api", 100)
        store_stats(session, ticker, "granted", "year",
                    {str(y): 1500 + 120 * (y - today.year + 9) + i * 400 for y in range(today.year - 9, today.year + 1)})
        store_stats(session, ticker, "granted", "cpc", dict(Counter(r.cpc_class for r in granted)), note="based on the 60 most recent grants")
        store_stats(session, ticker, "application", "total", {"24m": 2400 + i * 300})
        store_stats(session, ticker, "application", "cpc", dict(Counter(r.cpc_class for r in apps)), note="based on the 25 most recent publications")
    for ticker, *_ in DEMO_COMPANIES:
        for resource in ("global", "patents"):
            session.add(FetchLog(resource=resource, ticker=ticker, source="seed", fetched_at=now, status="ok"))
    session.commit()
