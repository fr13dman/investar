def test_watchlist_crud_and_screener_filter(client, seeded):
    created = client.post("/api/watchlists", json={"name": "Chips"})
    assert created.status_code == 201
    wid = created.json()["id"]
    assert client.post("/api/watchlists", json={"name": "Chips"}).status_code == 409

    client.post(f"/api/watchlists/{wid}/items", json={"ticker": "nvda"})
    body = client.post(f"/api/watchlists/{wid}/items", json={"ticker": "AMD"}).json()
    assert body["tickers"] == ["AMD", "NVDA"]
    assert client.post(f"/api/watchlists/{wid}/items", json={"ticker": "ZZZZ"}).status_code == 404

    screened = client.get("/api/stocks", params={"watchlist_id": wid}).json()
    assert {r["ticker"] for r in screened["items"]} == {"AMD", "NVDA"}

    renamed = client.put(f"/api/watchlists/{wid}", json={"name": "Semis"}).json()
    assert renamed["name"] == "Semis"
    assert client.delete(f"/api/watchlists/{wid}/items/AMD").json()["tickers"] == ["NVDA"]

    assert [w["name"] for w in client.get("/api/watchlists").json()] == ["Semis"]
    assert client.delete(f"/api/watchlists/{wid}").status_code == 204
    assert client.get("/api/watchlists").json() == []
    assert client.put("/api/watchlists/999", json={"name": "x"}).status_code == 404
