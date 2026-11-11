"""Weekly research refresh across the universe (slow-changing filings data)."""

from functools import partial

from sqlalchemy.orm import Session

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


def refresh_all_research(session: Session) -> None:
    for ticker in universe_tickers(session, include_benchmarks=False):
        for resource, source, fn in WEEKLY_RESEARCH:
            run_refresh(resource, ticker, source, partial(fn, ticker=ticker))
