from collections import Counter
from datetime import date, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import NewsArticle
from app.providers import registry
from app.services.db_utils import upsert
from app.services.sentiment import get_analyzer

WINDOW_DAYS = 30


def refresh_news(session: Session, ticker: str, today: date | None = None) -> int:
    today = today or date.today()
    items = registry.news().company_news(ticker, today - timedelta(days=WINDOW_DAYS), today)
    analyzer = get_analyzer()
    scores = analyzer.analyze([f"{i.headline}. {i.summary or ''}".strip() for i in items])
    rows = [
        dict(ticker=ticker, external_id=i.external_id, headline=i.headline, summary=i.summary, source=i.source,
             url=i.url, image=i.image, published_at=i.published_at, sentiment_label=s.label,
             sentiment_score=s.score, sentiment_model=analyzer.name)
        for i, s in zip(items, scores)
    ]
    upsert(session, NewsArticle, rows, ["ticker", "url"])
    cutoff = datetime.combine(today - timedelta(days=WINDOW_DAYS), datetime.min.time())
    session.execute(delete(NewsArticle).where(NewsArticle.ticker == ticker, NewsArticle.published_at < cutoff))
    session.commit()
    return len(rows)


def news_payload(session: Session, ticker: str, limit: int = 100) -> dict:
    articles = session.scalars(
        select(NewsArticle).where(NewsArticle.ticker == ticker).order_by(NewsArticle.published_at.desc()).limit(limit)
    ).all()
    counts = Counter(a.sentiment_label or "neutral" for a in articles)
    scored = [a.sentiment_score for a in articles if a.sentiment_score is not None]
    return {
        "items": [
            {
                "headline": a.headline,
                "summary": a.summary,
                "source": a.source,
                "url": a.url,
                "image": a.image,
                "published_at": a.published_at.isoformat(),
                "sentiment": {"label": a.sentiment_label, "score": a.sentiment_score, "model": a.sentiment_model},
            }
            for a in articles
        ],
        "summary": {
            "positive": counts.get("positive", 0),
            "neutral": counts.get("neutral", 0),
            "negative": counts.get("negative", 0),
            "average_score": round(sum(scored) / len(scored), 4) if scored else None,
        },
    }
