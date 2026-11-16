import pytest

from app.providers import registry
from app.vistashares_catalog import VISTASHARES_TICKERS
from tests.conftest import SEED_END
from tests.fakes import FakeConstituents, FakePrices, FakeProfiles, FakeSearch


@pytest.fixture
def niched(session):
    from app.seed import seed_market, seed_niches

    seed_market(session, end=SEED_END)
    seed_niches(session, end=SEED_END)
    registry.override(
        search=FakeSearch(),
        profiles=FakeProfiles(),
        prices=FakePrices(),
        constituents=FakeConstituents(),
    )
    return session


def test_list_niche_etfs(client, niched):
    res = client.get("/api/etfs?period=wow")
    assert res.status_code == 200
    body = res.json()
    assert body["period"] == "wow"
    tickers = {e["ticker"] for e in body["etfs"]}
    assert "URA" in tickers and "AIS" in tickers and "POW" in tickers
    assert all("size" in e and "return_pct" in e for e in body["etfs"])
    slugs = {g["slug"] for g in body["groups"]}
    assert "ai" in slugs and "income" in slugs


def test_list_etfs_filter_niche(client, niched):
    res = client.get("/api/etfs?niche=space")
    assert res.status_code == 200
    tickers = {e["ticker"] for e in res.json()["etfs"]}
    assert tickers == {"GALX"}


def test_vistashares_families(client, niched):
    res = client.get("/api/etfs/vistashares")
    assert res.status_code == 200
    body = res.json()
    assert {f["id"] for f in body["families"]} == {"target15", "supercycle", "shield"}
    seeded = {e["ticker"] for e in body["etfs"]}
    assert seeded == VISTASHARES_TICKERS
    assert "AIS" in seeded and "OMAH" in seeded
    # AUM comes from holdings snapshot or issuer meta so the map has real tile sizes.
    assert any(e.get("aum") for e in body["etfs"])
    assert all(e["size"] > 0 for e in body["etfs"])


def test_heatmap_top_holdings(client, niched):
    res = client.get("/api/etfs/AIS/heatmap?period=mom")
    assert res.status_code == 200
    body = res.json()
    assert body["ticker"] == "AIS"
    assert body["period"] == "mom"
    assert body["issuer"] == "vistashares"
    assert body["nodes"]
    assert any(n["kind"] == "other" for n in body["nodes"])
    assert any(n["ticker"] == "MU" for n in body["nodes"])


def test_refresh_etf(client, niched):
    res = client.post("/api/etfs/refresh", json={"tickers": ["URA", "AIS"]})
    assert res.status_code == 200
    assert set(res.json()["refreshed"]) == {"URA", "AIS"}
    one = client.post("/api/etfs/URA/refresh")
    assert one.status_code == 200
    assert one.json()["refreshed"] == ["URA"]


def test_heatmap_rejects_non_etf_and_bad_period(client, niched):
    assert client.get("/api/etfs/AAPL/heatmap").status_code == 404
    assert client.get("/api/etfs/BAD TICKER!/heatmap").status_code == 422
    assert client.get("/api/etfs/AIS/heatmap?period=nope").status_code == 422
    assert client.get("/api/etfs?period=nope").status_code == 422
    assert client.get("/api/etfs/vistashares?family=nope").status_code == 400


def test_refresh_skips_unknown_and_caps(client, niched):
    res = client.post("/api/etfs/refresh", json={"tickers": ["AAPL", "NOTREAL", "URA"]})
    assert res.status_code == 200
    assert res.json()["refreshed"] == ["URA"]
    too_many = client.post("/api/etfs/refresh", json={"tickers": [f"T{i}" for i in range(30)]})
    assert too_many.status_code == 422


def test_list_endpoints_do_not_hit_network(client, niched, monkeypatch):
    from app.providers import holdings_tickerinside, holdings_vistashares, vistashares_meta

    def boom(*_a, **_k):
        raise AssertionError("GET lists must not fetch holdings")

    monkeypatch.setattr(holdings_vistashares.VistaSharesHoldings, "holdings", boom)
    monkeypatch.setattr(holdings_tickerinside.TickerInsideHoldings, "holdings", boom)
    monkeypatch.setattr(vistashares_meta, "fetch_fund_meta", boom)
    assert client.get("/api/etfs").status_code == 200
    assert client.get("/api/etfs/vistashares").status_code == 200


def test_empty_holdings_do_not_overwrite(session, niched):
    from app.models import EtfHoldingsSnapshot
    from app.providers.base import FundHoldings
    from app.providers.holdings_demo import DemoHoldings
    from app.services.etfs import fetch_and_store_holdings

    class EmptyHoldings:
        def holdings(self, ticker: str):
            return FundHoldings(ticker=ticker, as_of=None, source="empty", holdings=[])

    before = session.get(EtfHoldingsSnapshot, "AIS")
    assert before and before.holdings
    fetched_at = before.fetched_at
    registry.override(holdings=EmptyHoldings())
    out = fetch_and_store_holdings(session, "AIS", force=True)
    assert out is before
    session.refresh(before)
    assert before.holdings
    assert before.fetched_at == fetched_at
    registry.override(holdings=DemoHoldings())
