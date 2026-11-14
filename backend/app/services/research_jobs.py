"""Weekly research refresh across the universe (slow-changing filings data)."""

from functools import partial

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Company
from app.services.ceo_scorecard import refresh_ceo
from app.services.global_presence import refresh_global
from app.services.ingest import universe_tickers
from app.services.patents import refresh_patents
from app.services.refresh import run_refresh

WEEKLY_RESEARCH = [
    ("ceo", "sec+wikidata", refresh_ceo),
    ("global", "sec", refresh_global),
    ("patents", "patentsview", refresh_patents),
]


def research_tickers(session: Session) -> list[str]:
    """Filings-based research needs an SEC registrant; ETFs and non-SEC extras are skipped."""
    tracked = universe_tickers(session, include_benchmarks=False)
    eligible = set(session.scalars(select(Company.ticker).where(Company.asset_type == "stock", Company.cik.is_not(None))))
    return [t for t in tracked if t in eligible]


def refresh_all_research(session: Session) -> None:
    for ticker in research_tickers(session):
        for resource, source, fn in WEEKLY_RESEARCH:
            run_refresh(resource, ticker, source, partial(fn, ticker=ticker))
