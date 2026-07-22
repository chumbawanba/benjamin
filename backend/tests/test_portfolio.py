from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from tests.conftest import login, mock_market_data_valid

from app.models import Position


@pytest.fixture(autouse=True)
def _mock_fx_rate():
    """seeded_stock é USD e User.preferred_currency é EUR por defeito - sem
    isto, todos os testes deste ficheiro chamariam a Twelve Data a sério (ver
    CLAUDE.md: nunca chamar Finnhub/Twelve Data diretamente nos testes)."""
    with patch("app.services.market_data._twelvedata_get", new=AsyncMock(return_value={"rate": "0.9"})):
        yield


async def test_create_and_list_position(client, user_a, seeded_stock):
    headers = await login(client, "a@test.dev", "password-a")
    resp = await client.post(
        "/portfolio", json={"ticker": "AAPL", "quantity": "10", "avg_cost": "150.00"}, headers=headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["stock"]["ticker"] == "AAPL"
    assert Decimal(body["quantity"]) == Decimal("10")
    assert Decimal(body["avg_cost"]) == Decimal("150.00")
    assert Decimal(body["cost_total"]) == Decimal("1500.00")
    # seeded_stock termina a subir perto de 180 -> valor de mercado > custo -> P&L positivo
    assert Decimal(body["market_value"]) > Decimal(body["cost_total"])
    assert Decimal(body["unrealized_pl"]) > 0
    assert Decimal(body["unrealized_pl_pct"]) > 0

    resp2 = await client.get("/portfolio", headers=headers)
    assert resp2.status_code == 200
    assert len(resp2.json()) == 1


async def test_create_position_creates_stock_if_new(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    with mock_market_data_valid("Microsoft Corp."):
        resp = await client.post(
            "/portfolio", json={"ticker": "msft", "quantity": "5", "avg_cost": "300"}, headers=headers,
        )
    assert resp.status_code == 201
    body = resp.json()
    assert body["stock"]["ticker"] == "MSFT"
    # sem PriceSnapshot ainda -> não há preço de mercado conhecido
    assert body["last_price"] is None
    assert body["market_value"] is None
    assert body["unrealized_pl"] is None


async def test_invalid_ticker_rejected(client, user_a):
    from unittest.mock import AsyncMock, patch

    headers = await login(client, "a@test.dev", "password-a")
    with patch("app.services.market_data._finnhub_get", new=AsyncMock(return_value={})):
        resp = await client.post(
            "/portfolio", json={"ticker": "ZZZZZZ", "quantity": "1", "avg_cost": "1"}, headers=headers,
        )
    assert resp.status_code == 422


async def test_duplicate_position_rejected(client, user_a, seeded_stock):
    headers = await login(client, "a@test.dev", "password-a")
    await client.post("/portfolio", json={"ticker": "AAPL", "quantity": "1", "avg_cost": "100"}, headers=headers)
    resp = await client.post("/portfolio", json={"ticker": "AAPL", "quantity": "2", "avg_cost": "110"}, headers=headers)
    assert resp.status_code == 422


async def test_update_position(client, user_a, seeded_stock):
    headers = await login(client, "a@test.dev", "password-a")
    create = await client.post(
        "/portfolio", json={"ticker": "AAPL", "quantity": "10", "avg_cost": "150"}, headers=headers,
    )
    position_id = create.json()["id"]
    resp = await client.put(
        f"/portfolio/{position_id}", json={"quantity": "20", "avg_cost": "160"}, headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert Decimal(body["quantity"]) == Decimal("20")
    assert Decimal(body["avg_cost"]) == Decimal("160")
    assert Decimal(body["cost_total"]) == Decimal("3200")


async def test_delete_position(client, user_a, seeded_stock):
    headers = await login(client, "a@test.dev", "password-a")
    create = await client.post(
        "/portfolio", json={"ticker": "AAPL", "quantity": "1", "avg_cost": "100"}, headers=headers,
    )
    position_id = create.json()["id"]
    resp = await client.delete(f"/portfolio/{position_id}", headers=headers)
    assert resp.status_code == 204
    resp2 = await client.get("/portfolio", headers=headers)
    assert resp2.json() == []


async def test_position_isolated_between_users(client, user_a, user_b, seeded_stock):
    headers_a = await login(client, "a@test.dev", "password-a")
    headers_b = await login(client, "b@test.dev", "password-b")
    await client.post("/portfolio", json={"ticker": "AAPL", "quantity": "1", "avg_cost": "100"}, headers=headers_a)

    resp_b = await client.get("/portfolio", headers=headers_b)
    assert resp_b.json() == []

    # utilizador B não consegue editar/apagar a posição de A
    create_a = await client.get("/portfolio", headers=headers_a)
    position_id = create_a.json()[0]["id"]
    resp_edit = await client.put(
        f"/portfolio/{position_id}", json={"quantity": "5", "avg_cost": "1"}, headers=headers_b,
    )
    assert resp_edit.status_code == 404
    resp_delete = await client.delete(f"/portfolio/{position_id}", headers=headers_b)
    assert resp_delete.status_code == 404


async def test_position_converted_to_preferred_currency(client, user_a, seeded_stock):
    """seeded_stock é USD; User.preferred_currency é EUR por defeito (ver
    models/user.py). O mock global deste ficheiro devolve sempre rate=0.9."""
    headers = await login(client, "a@test.dev", "password-a")
    resp = await client.post(
        "/portfolio", json={"ticker": "AAPL", "quantity": "10", "avg_cost": "150"}, headers=headers,
    )
    body = resp.json()
    assert body["display_currency"] == "EUR"
    assert Decimal(body["cost_total_converted"]) == Decimal(body["cost_total"]) * Decimal("0.9")
    assert Decimal(body["market_value_converted"]) == Decimal(body["market_value"]) * Decimal("0.9")


async def test_position_same_currency_no_conversion_call(client, user_a, seeded_stock):
    """Se a moeda preferida já é a da ação, get_rate devolve 1 sem chamar a
    Twelve Data - confirmamos isso sobrepondo o mock do ficheiro (que só
    devolveria 0.9 se fosse chamado) para garantir que NÃO é chamado."""
    headers = await login(client, "a@test.dev", "password-a")
    await client.put("/portfolio/currency", json={"currency": "USD"}, headers=headers)
    with patch("app.services.market_data._twelvedata_get", new=AsyncMock(side_effect=Exception("não devia ser chamado"))):
        resp = await client.post(
            "/portfolio", json={"ticker": "AAPL", "quantity": "10", "avg_cost": "150"}, headers=headers,
        )
    body = resp.json()
    assert body["display_currency"] == "USD"
    assert Decimal(body["cost_total_converted"]) == Decimal(body["cost_total"])


async def test_get_and_set_portfolio_currency(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    resp = await client.get("/portfolio/currency", headers=headers)
    assert resp.json() == {"currency": "EUR"}

    resp2 = await client.put("/portfolio/currency", json={"currency": "usd"}, headers=headers)
    assert resp2.status_code == 200
    assert resp2.json() == {"currency": "USD"}

    resp3 = await client.get("/portfolio/currency", headers=headers)
    assert resp3.json() == {"currency": "USD"}


async def test_portfolio_currency_isolated_between_users(client, user_a, user_b):
    headers_a = await login(client, "a@test.dev", "password-a")
    headers_b = await login(client, "b@test.dev", "password-b")

    await client.put("/portfolio/currency", json={"currency": "USD"}, headers=headers_a)

    resp_b = await client.get("/portfolio/currency", headers=headers_b)
    assert resp_b.json() == {"currency": "EUR"}


async def test_set_portfolio_currency_requires_auth(client):
    resp = await client.put("/portfolio/currency", json={"currency": "USD"})
    assert resp.status_code == 401


async def test_fx_rates_lists_currencies_used_in_portfolio(client, user_a, seeded_stock):
    """seeded_stock é USD, preferred_currency por defeito é EUR - deve aparecer
    exatamente um par USD->EUR, com o rate=0.9 do mock global deste ficheiro."""
    headers = await login(client, "a@test.dev", "password-a")
    await client.post("/portfolio", json={"ticker": "AAPL", "quantity": "1", "avg_cost": "100"}, headers=headers)

    resp = await client.get("/portfolio/fx-rates", headers=headers)
    assert resp.status_code == 200
    rates = resp.json()
    assert len(rates) == 1
    assert rates[0]["base_currency"] == "USD"
    assert rates[0]["quote_currency"] == "EUR"
    assert Decimal(rates[0]["rate"]) == Decimal("0.9")


async def test_fx_rates_empty_when_same_currency(client, user_a, seeded_stock):
    headers = await login(client, "a@test.dev", "password-a")
    await client.put("/portfolio/currency", json={"currency": "USD"}, headers=headers)
    await client.post("/portfolio", json={"ticker": "AAPL", "quantity": "1", "avg_cost": "100"}, headers=headers)

    resp = await client.get("/portfolio/fx-rates", headers=headers)
    assert resp.json() == []


async def test_fx_rates_empty_without_positions(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    resp = await client.get("/portfolio/fx-rates", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []


async def test_fx_rates_requires_auth(client):
    resp = await client.get("/portfolio/fx-rates")
    assert resp.status_code == 401


async def test_cascade_delete_position_with_user(client, db_session, user_a, seeded_stock):
    """positions.user_id tem ON DELETE CASCADE (ver migração b2c3d4e5f6a7) —
    confirma que apagar o utilizador não deixa IntegrityError nem posições
    órfãs, com o enforcement de FKs ligado no SQLite de teste (mesmo padrão
    usado para apanhar o bug real de cascade em test_strategies.py)."""
    from sqlalchemy import select, text

    await db_session.execute(text("PRAGMA foreign_keys=ON"))

    headers = await login(client, "a@test.dev", "password-a")
    await client.post("/portfolio", json={"ticker": "AAPL", "quantity": "1", "avg_cost": "100"}, headers=headers)

    user = (await db_session.execute(select(type(user_a)).where(type(user_a).id == user_a.id))).scalar_one()
    await db_session.delete(user)
    await db_session.commit()

    remaining = (await db_session.execute(select(Position))).scalars().all()
    assert remaining == []
