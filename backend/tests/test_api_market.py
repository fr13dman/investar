def test_sector_tree(client, seeded):
    tree = client.get("/api/sectors").json()
    tech = next(s for s in tree if s["sector"] == "Technology")
    assert tech["count"] == 6
    assert {"industry": "Semiconductors", "count": 2} in tech["industries"]
    assert all(s["sector"] != "Benchmark" for s in tree)


def test_stocks_default_sort_market_cap_desc_and_excludes_benchmarks(client, seeded):
    body = client.get("/api/stocks").json()
    assert body["total"] == 12
    caps = [r["market_cap"] for r in body["items"]]
    assert caps == sorted(caps, reverse=True)
    assert not {"SPY", "QQQ"} & {r["ticker"] for r in body["items"]}
    row = body["items"][0]
    for key in ("chg_1d_pct", "chg_1w_pct", "chg_ytd_pct", "sparkline", "pe_ratio", "volume"):
        assert key in row
    assert len(row["sparkline"]) == 5


def test_filters_sector_industry_index_capband_search(client, seeded):
    semis = client.get("/api/stocks", params={"sector": "Technology", "industry": "Semiconductors"}).json()
    assert {r["ticker"] for r in semis["items"]} == {"NVDA", "AMD"}

    ndx_only = client.get("/api/stocks", params={"index": "ndx100"}).json()
    assert all(r["in_ndx100"] for r in ndx_only["items"])
    sp_only = client.get("/api/stocks", params={"index": "sp500"}).json()
    assert "ASML" not in {r["ticker"] for r in sp_only["items"]}
    both = client.get("/api/stocks", params={"index": "both"}).json()
    assert all(r["in_sp500"] and r["in_ndx100"] for r in both["items"])

    mega = client.get("/api/stocks", params={"cap_band": "mega"}).json()
    assert all(r["market_cap"] >= 200e9 for r in mega["items"])

    search = client.get("/api/stocks", params={"q": "gold"}).json()
    assert [r["ticker"] for r in search["items"]] == ["GS"]


def test_sort_by_swings_pct_and_abs(client, seeded):
    for window in ("chg_1d", "chg_1w", "chg_ytd"):
        asc = client.get("/api/stocks", params={"sort": window, "order": "asc"}).json()["items"]
        vals = [r[f"{window}_pct"] for r in asc]
        assert vals == sorted(vals)
        abs_desc = client.get("/api/stocks", params={"sort": window, "mode": "abs"}).json()["items"]
        vals = [r[f"{window}_abs"] for r in abs_desc]
        assert vals == sorted(vals, reverse=True)


def test_pagination(client, seeded):
    p1 = client.get("/api/stocks", params={"page_size": 5, "page": 1, "sort": "ticker", "order": "asc"}).json()
    p3 = client.get("/api/stocks", params={"page_size": 5, "page": 3, "sort": "ticker", "order": "asc"}).json()
    assert len(p1["items"]) == 5 and len(p3["items"]) == 2
    assert p1["items"][0]["ticker"] == "AAPL"


def test_invalid_sort_rejected(client, seeded):
    assert client.get("/api/stocks", params={"sort": "drop table"}).status_code == 422


def test_movers_per_sector(client, seeded):
    body = client.get("/api/movers", params={"sector": "Technology", "window": "chg_ytd", "limit": 3}).json()
    gains = [r["chg_ytd_pct"] for r in body["gainers"]]
    losses = [r["chg_ytd_pct"] for r in body["losers"]]
    assert len(gains) == 3 and gains == sorted(gains, reverse=True)
    assert losses == sorted(losses)
    assert all(r["sector"] == "Technology" for r in body["gainers"] + body["losers"])


def test_benchmarks(client, seeded):
    tickers = [r["ticker"] for r in client.get("/api/benchmarks").json()]
    assert tickers == ["QQQ", "SPY"]


def test_status_and_refresh_trigger(client, seeded, monkeypatch):
    from app.api.routes import admin

    calls = []
    monkeypatch.setitem(admin.JOBS, "prices", ("prices_intraday", "yfinance", lambda s: calls.append(1)))
    r = client.post("/api/refresh", json={"scope": "prices"})
    assert r.status_code == 202 and r.json()["started"] is True
    assert calls == [1]  # background task ran after the response
    status = client.get("/api/status").json()
    assert status["companies"] == 12
    assert status["jobs"]["prices_intraday"]["status"] == "ok"
