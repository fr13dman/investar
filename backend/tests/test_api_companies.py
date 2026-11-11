from datetime import date

from app.models import Company, FetchLog
from app.providers import registry
from app.services import company as company_svc
from app.services import sentiment
from app.services.sentiment import VaderAnalyzer
from tests.fakes import FakeIntraday, FakeNews, FakeQuotes, FakeSec, FakeWikidata, NoQuotes


class NoProfiles:
    def profile(self, ticker):
        return None


def test_company_profile_and_404(client, seeded):
    registry.override(profiles=NoProfiles())
    body = client.get("/api/companies/aapl").json()
    assert body["ticker"] == "AAPL" and body["name"] == "Apple Inc."
    assert body["price"] is not None and body["chg_ytd_pct"] is not None
    assert body["refresh"]["refreshing"] is True  # stale profile -> background refresh scheduled
    assert client.get("/api/companies/ZZZZ").status_code == 404


def test_price_ranges_include_spy(client, seeded):
    one_y = client.get("/api/companies/AAPL/prices", params={"range": "1y"}).json()
    assert one_y["interval"] == "1d" and 250 <= len(one_y["bars"]) <= 263  # seed has every weekday
    assert len(one_y["benchmark"]["bars"]) == len(one_y["bars"])
    ytd = client.get("/api/companies/AAPL/prices", params={"range": "ytd"}).json()
    assert all(b["time"] >= "2026-01-01" for b in ytd["bars"])
    five_y = client.get("/api/companies/AAPL/prices", params={"range": "5y"}).json()
    assert len(five_y["bars"]) == 504  # seeded history is 2 years
    assert client.get("/api/companies/AAPL/prices", params={"range": "10y"}).status_code == 422


def test_intraday_range_uses_provider_and_falls_back(client, seeded):
    company_svc._intraday_cache.clear()
    registry.override(prices=FakeIntraday())
    body = client.get("/api/companies/AAPL/prices", params={"range": "1d"}).json()
    assert body["interval"] == "5m" and len(body["bars"]) == 5 and isinstance(body["bars"][0]["time"], int)

    class Broken:
        def intraday(self, *a):
            raise RuntimeError("offline")

    company_svc._intraday_cache.clear()
    registry.override(prices=Broken())
    body = client.get("/api/companies/AAPL/prices", params={"range": "1w"}).json()
    assert body["interval"] == "1d" and body["bars"]


def test_live_quote_updates_metrics(client, seeded):
    registry.override(quotes=FakeQuotes(price=250.0, prev=245.0))
    body = client.get("/api/companies/AAPL/quote").json()
    assert body["source"] == "finnhub" and body["price"] == 250.0
    assert round(body["chg_1d_abs"], 2) == 5.0

    registry.override(quotes=NoQuotes())
    body = client.get("/api/companies/MSFT/quote").json()
    assert body["source"] == "stored" and body["price"] is not None


def test_news_refreshes_in_background_with_sentiment(client, seeded):
    registry.override(news=FakeNews())
    sentiment.set_analyzer(VaderAnalyzer())
    first = client.get("/api/companies/NVDA/news").json()
    assert first["refresh"]["refreshing"] is True  # TestClient runs the background task after responding
    second = client.get("/api/companies/NVDA/news").json()
    assert second["refresh"]["refreshing"] is False and second["refresh"]["status"] == "ok"
    labels = [i["sentiment"]["label"] for i in second["items"]]
    assert labels == ["positive", "negative", "neutral"]
    assert second["summary"] == {"positive": 1, "neutral": 1, "negative": 1,
                                 "average_score": second["summary"]["average_score"]}
    assert second["items"][0]["sentiment"]["model"] == "vader"
    sentiment.set_analyzer(None)


def test_news_failure_is_reported(client, seeded):
    class Down:
        def company_news(self, *a):
            raise RuntimeError("FINNHUB_API_KEY is not set")

    registry.override(news=Down())
    client.get("/api/companies/AMD/news")
    body = client.get("/api/companies/AMD/news").json()
    assert body["refresh"]["status"] == "error" and "FINNHUB_API_KEY" in body["refresh"]["message"]
    assert body["items"] == [] and body["configured"] is False


def test_ceo_endpoint_and_override(client, seeded):
    seeded.get(Company, "AAPL").cik = "0000320193"
    seeded.commit()
    registry.override(sec=FakeSec(), wikidata=FakeWikidata(), prices=FakeIntraday())
    assert client.get("/api/companies/AAPL/ceo").json()["scorecard"] is None
    card = client.get("/api/companies/AAPL/ceo").json()["scorecard"]
    assert card["ceo_name"] == "Q106028933"  # no executive row seeded: Wikidata's current entry
    assert card["pay_vs_performance"] and card["fundamentals"]
    assert seeded.get(FetchLog, ("ceo", "AAPL")) is not None

    updated = client.put("/api/companies/AAPL/ceo", json={"ceo_name": "John Ternus", "tenure_start": "2026-09-01"}).json()
    assert updated["scorecard"]["ceo_name"] == "John Ternus"
    assert updated["scorecard"]["tenure_source"] == "manual"
    assert updated["scorecard"]["tenure_start"] == date(2026, 9, 1).isoformat()
