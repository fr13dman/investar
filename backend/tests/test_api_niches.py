import pytest

from app.providers import registry
from app.providers.base import ProviderUnavailable
from tests.conftest import SEED_END
from tests.fakes import FakeConstituents, FakePrices, FakeProfiles, FakeSearch


@pytest.fixture
def niched(session):
    from app.seed import seed_market, seed_niches

    seed_market(session, end=SEED_END)
    seed_niches(session, end=SEED_END)
    registry.override(search=FakeSearch(), profiles=FakeProfiles(), prices=FakePrices(),
                      constituents=FakeConstituents())
    return session


def _niche_id(client, slug):
    for parent in client.get("/api/niches").json():
        for n in (parent, *parent["children"]):
            if n["slug"] == slug:
                return n["id"]
    raise KeyError(slug)


def _tickers(client, **params):
    return {r["ticker"] for r in client.get("/api/stocks", params={"page_size": 100, **params}).json()["items"]}


def test_niche_tree_endpoint(client, niched):
    tree = client.get("/api/niches").json()
    ai = tree[0]
    assert ai["slug"] == "ai" and ai["count"] == 7
    assert {"id", "slug", "name", "description", "count"} <= set(ai["children"][0])


def test_screener_includes_extras_and_filters_by_niche(client, niched):
    body = client.get("/api/stocks").json()
    assert body["total"] == 15
    assert _tickers(client, niche="ai") == {"NVDA", "AMD", "ASML", "MSFT", "AMZN", "ORCL", "CRWV"}
    assert _tickers(client, niche="neoclouds") == {"CRWV"}
    assert _tickers(client, niche="energy-transition") == {"URA", "OKLO"}
    assert _tickers(client, niche="no-such-niche") == set()


def test_asset_type_and_index_other(client, niched):
    assert _tickers(client, asset_type="etf") == {"URA"}
    assert "URA" not in _tickers(client, asset_type="stock")
    assert _tickers(client, index="other") == {"CRWV", "OKLO", "URA"}
    row = next(r for r in client.get("/api/stocks", params={"q": "URA"}).json()["items"] if r["ticker"] == "URA")
    assert row["asset_type"] == "etf" and row["extra_source"] == "curated"


def test_change_range_filters(client, niched):
    gainers = client.get("/api/stocks", params={"chg_window": "chg_ytd", "chg_min": 0, "page_size": 100}).json()
    assert gainers["items"] and all(r["chg_ytd_pct"] >= 0 for r in gainers["items"])
    band = client.get("/api/stocks", params={"chg_window": "chg_1d", "chg_min": -1, "chg_max": 1}).json()
    assert all(-1 <= r["chg_1d_pct"] <= 1 for r in band["items"])
    everything = client.get("/api/stocks").json()["total"]
    assert gainers["total"] < everything
    assert client.get("/api/stocks", params={"chg_window": "chg_5y", "chg_min": 0}).status_code == 422


def test_movers_by_niche_and_sectors_exclude_etfs(client, niched):
    body = client.get("/api/movers", params={"niche": "ai", "limit": 3}).json()
    ai = {"NVDA", "AMD", "ASML", "MSFT", "AMZN", "ORCL", "CRWV"}
    assert {r["ticker"] for r in body["gainers"] + body["losers"]} <= ai
    sectors = client.get("/api/sectors").json()
    assert all(s["sector"] for s in sectors)
    assert sum(s["count"] for s in sectors) == 14  # 12 index stocks + CRWV + OKLO; URA has no sector


def test_market_search_flags(client, niched):
    results = {r["symbol"]: r for r in client.get("/api/search", params={"q": "nb"}).json()}
    assert results["NBIS"]["addable"] and results["NBIS"]["asset_type"] == "stock"
    assert results["NLR"]["addable"] and results["NLR"]["asset_type"] == "etf"
    assert not results["NBIS.MX"]["addable"] and not results["NBIS.MX"]["us_listed"]
    assert not results["^NBI"]["addable"]
    assert results["NVDA"]["tracked"] and not results["NVDA"]["addable"]


def test_market_search_unavailable(client, niched):
    class Down:
        def search(self, q, limit=10):
            raise ProviderUnavailable("Yahoo search failed")

    registry.override(search=Down())
    assert client.get("/api/search", params={"q": "x"}).status_code == 503


def test_track_symbol_with_niches(client, niched):
    neo = _niche_id(client, "neoclouds")
    r = client.post("/api/tracked", json={"ticker": "nbis", "niche_ids": [neo]})
    assert r.status_code == 202
    assert r.json()["ticker"] == "NBIS" and r.json()["status"] == "adding"
    # TestClient runs background tasks before returning, so prices are already in.
    assert client.get("/api/tracked/NBIS/status").json()["status"] == "ready"
    assert "NBIS" in _tickers(client, niche="neoclouds")
    company = client.get("/api/companies/NBIS").json()
    assert company["name"] == "Nebius Group N.V." and company["extra_source"] == "user"
    assert company["cik"] == "0001513845" and company["price"] is not None
    assert [(n["slug"], n["source"]) for n in company["niches"]] == [("neoclouds", "user")]


def test_track_etf(client, niched):
    assert client.post("/api/tracked", json={"ticker": "NLR"}).status_code == 202
    assert "NLR" in _tickers(client, asset_type="etf")


@pytest.mark.parametrize(("ticker", "status", "fragment"), [
    ("SHOP.TO", 422, "US-listed"),
    ("GBPUSD=X", 422, "only stocks and ETFs"),
    ("ZZZZ", 404, "no data"),
    ("NVDA", 409, "already tracked"),
    ("CRWV", 409, "already tracked"),
])
def test_track_rejections(client, niched, ticker, status, fragment):
    r = client.post("/api/tracked", json={"ticker": ticker})
    assert r.status_code == status and fragment in r.json()["detail"]


def test_track_rejects_non_usd(client, niched):
    from app.providers.base import Profile

    class CadOnNyse(FakeProfiles):
        PROFILES = {"XYZ": Profile("XYZ", exchange="NYQ", name="XYZ", quote_type="EQUITY", currency="CAD")}

    registry.override(profiles=CadOnNyse())
    r = client.post("/api/tracked", json={"ticker": "XYZ"})
    assert r.status_code == 422 and "USD" in r.json()["detail"]


def test_track_rejects_unknown_niche(client, niched):
    assert client.post("/api/tracked", json={"ticker": "NBIS", "niche_ids": [999]}).status_code == 422


def test_track_reports_backfill_failure(client, niched):
    registry.override(prices=FakePrices(empty=True))
    assert client.post("/api/tracked", json={"ticker": "NBIS"}).status_code == 202
    status = client.get("/api/tracked/NBIS/status").json()
    assert status["status"] == "error" and "no price history" in status["message"]


def test_untrack_rules(client, niched):
    client.post("/api/tracked", json={"ticker": "NBIS"})
    assert client.delete("/api/tracked/NBIS").status_code == 204
    assert "NBIS" not in _tickers(client)
    assert client.get("/api/companies/NBIS").status_code == 404
    assert client.delete("/api/tracked/CRWV").status_code == 409
    assert client.delete("/api/tracked/NVDA").status_code == 409
    assert client.delete("/api/tracked/NOPE").status_code == 404


def test_edit_user_niches(client, niched):
    client.post("/api/tracked", json={"ticker": "NBIS"})
    neo, chips = _niche_id(client, "neoclouds"), _niche_id(client, "ai-chips")
    r = client.put("/api/companies/NBIS/niches", json={"niche_ids": [neo, chips]})
    assert r.status_code == 200 and {n["slug"] for n in r.json()["niches"]} == {"neoclouds", "ai-chips"}
    r = client.put("/api/companies/NBIS/niches", json={"niche_ids": [neo]})
    assert [n["slug"] for n in r.json()["niches"]] == ["neoclouds"]
    assert client.put("/api/companies/NBIS/niches", json={"niche_ids": [999]}).status_code == 422
    assert client.put("/api/companies/CRWV/niches", json={"niche_ids": [neo]}).status_code == 409
    assert client.put("/api/companies/NOPE/niches", json={"niche_ids": []}).status_code == 404


def test_company_payload_has_niches_and_asset_type(client, niched):
    ura = client.get("/api/companies/URA").json()
    assert ura["asset_type"] == "etf"
    assert [(n["slug"], n["parent_slug"]) for n in ura["niches"]] == [("energy-transition", None)]
    crwv = client.get("/api/companies/CRWV").json()
    assert crwv["niches"][0]["parent_name"] == "AI"


def test_offline_providers_support_search_and_tracking(client, session, monkeypatch):
    from app.config import get_settings
    from app.seed import seed_market, seed_niches

    seed_market(session, end=SEED_END)
    seed_niches(session, end=SEED_END)
    registry.reset()
    monkeypatch.setattr(get_settings(), "offline_providers", True)
    results = {r["symbol"]: r for r in client.get("/api/search", params={"q": "nebius"}).json()}
    assert results["NBIS"]["addable"] and not results["YDX.DE"]["addable"]
    assert client.post("/api/tracked", json={"ticker": "NBIS"}).status_code == 202
    assert client.get("/api/tracked/NBIS/status").json()["status"] == "ready"
    assert client.get("/api/companies/NBIS").json()["price"] is not None


def test_parse_yahoo_search_quotes():
    from app.providers.search_yfinance import parse_search

    matches = parse_search([
        {"symbol": "NBIS", "shortname": "Nebius", "longname": "Nebius Group N.V.", "exchange": "NMS", "quoteType": "EQUITY"},
        {"shortname": "no symbol"},
        {"symbol": "URA", "shortname": "Global X Uranium ETF", "exchange": "PCX", "quoteType": "ETF"},
    ])
    assert [(m.symbol, m.name, m.exchange, m.quote_type) for m in matches] == [
        ("NBIS", "Nebius Group N.V.", "NMS", "EQUITY"),
        ("URA", "Global X Uranium ETF", "PCX", "ETF"),
    ]
