from sqlalchemy import func, select

from app.models import CeoScorecard, FetchLog, NewsArticle
from app.seed import seed_all
from app.services.refresh import is_stale
from tests.conftest import SEED_END


def test_seed_all_is_offline_and_fresh(session):
    from datetime import timedelta

    seed_all(session, end=SEED_END)
    assert session.scalar(select(func.count()).select_from(NewsArticle)) == 12 * 5
    card = session.get(CeoScorecard, "AAPL")
    assert card.ceo_name == "Jordan Avery" and card.tenure_source == "wikidata"
    assert card.revenue_cagr_pct is not None and card.pay_vs_performance
    assert not is_stale(session, "news", "AAPL", timedelta(minutes=60))
    assert not is_stale(session, "profile", "AMD", timedelta(days=7))
    assert session.get(FetchLog, ("ceo", "MSFT")).status == "ok"
    assert not is_stale(session, "patents", "TSLA", timedelta(days=7))

    from app.services.global_presence import global_payload
    from app.services.patents import patents_payload

    g = global_payload(session, "AAPL", None)
    assert {c["alpha2"] for c in g["countries"]} >= {"IE", "JP", "US", "BR"}
    p = patents_payload(session, "NVDA")
    assert p["granted"]["total_10y"] and len(p["granted"]["recent"]) == 50 and p["applications"]["total_24m"] == 2700
