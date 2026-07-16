from tests.conftest import login, mock_yfinance_valid


async def test_add_and_list(client, user_a):
    headers = await login(client, "a@test.local", "password-a")
    with mock_yfinance_valid():
        resp = await client.post("/watchlist", json={"ticker": "aapl"}, headers=headers)
    assert resp.status_code == 201
    assert resp.json()["stock"]["ticker"] == "AAPL"

    resp = await client.get("/watchlist", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


async def test_duplicate_rejected(client, user_a):
    headers = await login(client, "a@test.local", "password-a")
    with mock_yfinance_valid():
        await client.post("/watchlist", json={"ticker": "AAPL"}, headers=headers)
        resp = await client.post("/watchlist", json={"ticker": "AAPL"}, headers=headers)
    assert resp.status_code == 422


async def test_invalid_ticker(client, user_a):
    headers = await login(client, "a@test.local", "password-a")
    from unittest.mock import patch

    class EmptyTicker:
        info = {}
    with patch("app.services.market_data._yf_ticker", return_value=EmptyTicker()):
        resp = await client.post("/watchlist", json={"ticker": "XXXXXX"}, headers=headers)
    assert resp.status_code == 422


async def test_user_isolation(client, user_a, user_b):
    """Utilizador B não vê nem apaga itens do utilizador A."""
    headers_a = await login(client, "a@test.local", "password-a")
    headers_b = await login(client, "b@test.local", "password-b")
    with mock_yfinance_valid():
        resp = await client.post("/watchlist", json={"ticker": "AAPL"}, headers=headers_a)
    item_id = resp.json()["id"]

    resp = await client.get("/watchlist", headers=headers_b)
    assert resp.json() == []

    resp = await client.delete(f"/watchlist/{item_id}", headers=headers_b)
    assert resp.status_code == 404  # 404, não 403 — não revela existência
