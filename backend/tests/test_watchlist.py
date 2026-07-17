from tests.conftest import login, mock_market_data_valid


async def test_add_and_list(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    with mock_market_data_valid():
        resp = await client.post("/watchlist", json={"ticker": "aapl"}, headers=headers)
    assert resp.status_code == 201
    assert resp.json()["stock"]["ticker"] == "AAPL"

    resp = await client.get("/watchlist", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


async def test_duplicate_rejected(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    with mock_market_data_valid():
        await client.post("/watchlist", json={"ticker": "AAPL"}, headers=headers)
        resp = await client.post("/watchlist", json={"ticker": "AAPL"}, headers=headers)
    assert resp.status_code == 422


async def test_invalid_ticker(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    from unittest.mock import AsyncMock, patch

    with patch("app.services.market_data._finnhub_get", new=AsyncMock(return_value={})):
        resp = await client.post("/watchlist", json={"ticker": "XXXXXX"}, headers=headers)
    assert resp.status_code == 422


async def test_add_ticker_when_finnhub_unavailable(client, user_a):
    """Se a Finnhub estiver em baixo/rate-limited (excepção), o ticker é aceite na
    mesma, sem metadados, em vez de rejeitado (ver services/market_data.py)."""
    headers = await login(client, "a@test.dev", "password-a")
    from unittest.mock import AsyncMock, patch

    with patch(
        "app.services.market_data._finnhub_get",
        new=AsyncMock(side_effect=Exception("429 Too Many Requests")),
    ):
        resp = await client.post("/watchlist", json={"ticker": "AAPL"}, headers=headers)
    assert resp.status_code == 201
    assert resp.json()["stock"]["ticker"] == "AAPL"
    assert resp.json()["stock"]["name"] is None


async def test_search_stocks(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    from unittest.mock import AsyncMock, patch

    fake_response = {
        "count": 1,
        "result": [
            {"symbol": "AAPL", "description": "Apple Inc.", "displaySymbol": "AAPL", "type": "Common Stock"},
        ],
    }
    with patch("app.services.market_data._finnhub_get", new=AsyncMock(return_value=fake_response)):
        resp = await client.get("/watchlist/search?q=apple", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body[0]["ticker"] == "AAPL"
    assert body[0]["name"] == "Apple Inc."


async def test_search_stocks_failure_returns_empty(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    from unittest.mock import AsyncMock, patch

    with patch(
        "app.services.market_data._finnhub_get",
        new=AsyncMock(side_effect=Exception("429 Too Many Requests")),
    ):
        resp = await client.get("/watchlist/search?q=apple", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []


async def test_watchlist_news(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    from unittest.mock import AsyncMock, patch

    with mock_market_data_valid():
        await client.post("/watchlist", json={"ticker": "AAPL"}, headers=headers)

    fake_news = [
        {
            "headline": "Apple anuncia resultados",
            "summary": "resumo",
            "url": "https://example.com/a",
            "source": "Reuters",
            "datetime": 1750000000,
        },
    ]
    with patch("app.services.market_data._finnhub_get", new=AsyncMock(return_value=fake_news)):
        resp = await client.get("/watchlist/news", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["ticker"] == "AAPL"
    assert body[0]["headline"] == "Apple anuncia resultados"


async def test_watchlist_news_empty_watchlist(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    resp = await client.get("/watchlist/news", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []


async def test_watchlist_news_failure_returns_empty(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    from unittest.mock import AsyncMock, patch

    with mock_market_data_valid():
        await client.post("/watchlist", json={"ticker": "AAPL"}, headers=headers)

    with patch(
        "app.services.market_data._finnhub_get",
        new=AsyncMock(side_effect=Exception("429 Too Many Requests")),
    ):
        resp = await client.get("/watchlist/news", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []


async def test_reorder(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    with mock_market_data_valid():
        r1 = await client.post("/watchlist", json={"ticker": "AAPL"}, headers=headers)
        r2 = await client.post("/watchlist", json={"ticker": "MSFT"}, headers=headers)
    id1, id2 = r1.json()["id"], r2.json()["id"]

    # Ordem inicial: ordem de inserção (AAPL, depois MSFT) — novos itens são
    # sempre acrescentados ao fim (display_order = max+1).
    resp = await client.get("/watchlist", headers=headers)
    assert [i["stock"]["ticker"] for i in resp.json()] == ["AAPL", "MSFT"]

    resp = await client.put("/watchlist/reorder", json={"ordered_ids": [id2, id1]}, headers=headers)
    assert resp.status_code == 204

    resp = await client.get("/watchlist", headers=headers)
    assert [i["stock"]["ticker"] for i in resp.json()] == ["MSFT", "AAPL"]


async def test_reorder_ignores_other_users_ids(client, user_a, user_b):
    headers_a = await login(client, "a@test.dev", "password-a")
    headers_b = await login(client, "b@test.dev", "password-b")
    with mock_market_data_valid():
        r1 = await client.post("/watchlist", json={"ticker": "AAPL"}, headers=headers_a)
        r2 = await client.post("/watchlist", json={"ticker": "MSFT"}, headers=headers_b)

    resp = await client.put(
        "/watchlist/reorder", json={"ordered_ids": [r2.json()["id"], r1.json()["id"]]}, headers=headers_a
    )
    assert resp.status_code == 204

    resp = await client.get("/watchlist", headers=headers_a)
    assert len(resp.json()) == 1
    assert resp.json()[0]["stock"]["ticker"] == "AAPL"


async def test_user_isolation(client, user_a, user_b):
    """Utilizador B não vê nem apaga itens do utilizador A."""
    headers_a = await login(client, "a@test.dev", "password-a")
    headers_b = await login(client, "b@test.dev", "password-b")
    with mock_market_data_valid():
        resp = await client.post("/watchlist", json={"ticker": "AAPL"}, headers=headers_a)
    item_id = resp.json()["id"]

    resp = await client.get("/watchlist", headers=headers_b)
    assert resp.json() == []

    resp = await client.delete(f"/watchlist/{item_id}", headers=headers_b)
    assert resp.status_code == 404  # 404, não 403 — não revela existência
