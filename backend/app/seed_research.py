"""Demo research data for offline development and end-to-end tests.

Marks each resource as freshly fetched so opening a research page never triggers live API calls."""

from datetime import date, datetime, timedelta

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models import (
    CeoOverride,
    CeoScorecard,
    Executive,
    FetchLog,
    FinancialFact,
    NewsArticle,
)
from app.providers.wikidata import Tenure
from app.seed import DEMO_COMPANIES
from app.services.ceo_scorecard import compute_scorecard
from app.services.sentiment import VaderAnalyzer

CEOS = {
    "AAPL": ("Jordan Avery", date(2025, 3, 1)),
    "MSFT": ("Priya Raman", date(2014, 2, 4)),
    "NVDA": ("Sam Okafor", date(1993, 4, 1)),
}
HEADLINES = [
    "{name} posts record quarterly revenue and raises guidance",
    "{name} faces regulatory probe over pricing practices",
    "{name} to present at annual technology conference",
    "Analysts upgrade {name} after strong product demand",
    "{name} shares slide as supply chain delays hit margins",
]


def _seed_ceo(session: Session, ticker: str, name: str, start: date, now: datetime) -> None:
    session.add(Executive(ticker=ticker, name=f"Mx. {name}", title="Chief Executive Officer & Director",
                          total_pay=25e6, is_ceo=True, source="seed"))
    session.add(Executive(ticker=ticker, name="Alex Chen", title="Chief Financial Officer", total_pay=8e6, source="seed"))
    revenue, eps, margin = 50e9, 3.0, 0.2
    for year in range(2016, 2027):
        end = date(year, 9, 30)
        revenue *= 1.08
        eps *= 1.1
        margin = min(margin + 0.004, 0.32)
        for concept, unit, value in (
            ("Revenues", "USD", revenue),
            ("EarningsPerShareDiluted", "USD/shares", eps),
            ("NetIncomeLoss", "USD", revenue * margin),
        ):
            session.add(FinancialFact(ticker=ticker, concept=concept, period_end=end, unit=unit,
                                      period_start=end - timedelta(days=364), value=round(value, 2), form="10-K"))
    session.commit()
    pvp = [
        {"fiscal_year_end": f"{y}-09-30", "peo_total_comp": 20e6 + i * 2e6, "peo_comp_actually_paid": 15e6 + i * 6e6,
         "tsr_value": 100 + i * 25.0, "peer_tsr_value": 100 + i * 18.0, "net_income": 9e9 + i * 1e9, "peo_names": [name]}
        for i, y in enumerate(range(2021, 2026))
    ][::-1]
    compute_scorecard(session, ticker, [Tenure(name, start, None)], pvp)
    session.add(FetchLog(resource="ceo", ticker=ticker, source="seed", fetched_at=now, status="ok"))


def _seed_news(session: Session, ticker: str, company: str, now: datetime) -> None:
    analyzer = VaderAnalyzer()
    texts = [h.format(name=company) for h in HEADLINES]
    for i, (text, s) in enumerate(zip(texts, analyzer.analyze(texts))):
        session.add(NewsArticle(ticker=ticker, external_id=f"seed-{ticker}-{i}", headline=text,
                                summary=f"Demo article {i + 1} about {company}.", source="Demo Wire",
                                url=f"https://example.com/news/{ticker.lower()}/{i}", published_at=now - timedelta(hours=6 * i),
                                sentiment_label=s.label, sentiment_score=s.score, sentiment_model=analyzer.name))
    session.add(FetchLog(resource="news", ticker=ticker, source="seed", fetched_at=now, status="ok"))


def seed_research(session: Session, now: datetime) -> None:
    for model in (FetchLog, NewsArticle, CeoScorecard, CeoOverride, FinancialFact, Executive):
        session.execute(delete(model))
    session.commit()
    names = {t: n for t, n, *_ in DEMO_COMPANIES}
    for ticker, *_ in DEMO_COMPANIES:
        session.add(FetchLog(resource="profile", ticker=ticker, source="seed", fetched_at=now, status="ok"))
        _seed_news(session, ticker, names[ticker], now)
    for ticker, (name, start) in CEOS.items():
        _seed_ceo(session, ticker, name, start, now)
    session.commit()
    from app.seed_research_phase3 import seed_phase3

    seed_phase3(session, now)
