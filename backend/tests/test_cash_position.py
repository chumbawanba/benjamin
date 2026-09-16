from decimal import Decimal

from sqlalchemy import select

from tests.conftest import login

from app.models import Stock


async def test_add_cash_creates_position_priced_at_one(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    resp = await client.post("/portfolio/cash", json={"currency": "EUR", "amount": "500"}, headers=headers)

    assert resp.status_code == 201
    body = resp.json()
    assert body["stock"]["ticker"] == "CASH:EUR"
    assert body["stock"]["asset_type"] == "cash"
    assert Decimal(body["quantity"]) == Decimal("500")
    assert Decimal(body["avg_cost"]) == Decimal("1")
    assert Decimal(body["cost_total"]) == Decimal("500")
    # Preço de cash é sempre 1 -> valor de mercado = montante, sem P&L.
    assert Decimal(body["market_value"]) == Decimal("500")
    assert Decimal(body["unrealized_pl"]) == Decimal("0")


async def test_add_cash_lowercases_currency_and_reuses_stock(client, user_a, db_session):
    headers = await login(client, "a@test.dev", "password-a")
    resp = await client.post("/portfolio/cash", json={"currency": "usd", "amount": "100"}, headers=headers)

    assert resp.status_code == 201
    assert resp.json()["stock"]["ticker"] == "CASH:USD"

    stocks = (await db_session.execute(select(Stock).where(Stock.ticker == "CASH:USD"))).scalars().all()
    assert len(stocks) == 1


async def test_add_cash_duplicate_currency_rejected(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    resp1 = await client.post("/portfolio/cash", json={"currency": "EUR", "amount": "500"}, headers=headers)
    resp2 = await client.post("/portfolio/cash", json={"currency": "EUR", "amount": "200"}, headers=headers)

    assert resp1.status_code == 201
    assert resp2.status_code == 422


async def test_add_cash_no_auth_rejected(client):
    resp = await client.post("/portfolio/cash", json={"currency": "EUR", "amount": "500"})
    assert resp.status_code == 401


async def test_add_cash_isolated_between_users(client, user_a, user_b):
    headers_a = await login(client, "a@test.dev", "password-a")
    headers_b = await login(client, "b@test.dev", "password-b")

    await client.post("/portfolio/cash", json={"currency": "EUR", "amount": "500"}, headers=headers_a)
    resp_b = await client.get("/portfolio", headers=headers_b)

    assert resp_b.status_code == 200
    assert resp_b.json() == []


async def test_add_cash_never_calls_market_data(client, user_a):
    """ensure_fresh nunca deve tentar Finnhub/Twelve Data para cash - ver
    market_data.ensure_fresh, curto-circuito no topo para asset_type=='cash'.
    Sem mocks de Finnhub/Twelve Data ativos, isto rebentaria (CLAUDE.md:
    nunca chamados a sério nos testes) se o curto-circuito não existisse."""
    headers = await login(client, "a@test.dev", "password-a")
    await client.post("/portfolio/cash", json={"currency": "EUR", "amount": "500"}, headers=headers)

    resp = await client.get("/portfolio", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1
