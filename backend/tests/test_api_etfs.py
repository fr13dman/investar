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
