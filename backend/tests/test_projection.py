from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from tests.conftest import login


@pytest.fixture(autouse=True)
def _mock_fx_rate():
    """seeded_stock é USD e User.preferred_currency é EUR por defeito - sem
    isto, chamaria a Twelve Data a sério (ver CLAUDE.md). Mesmo padrão de
    test_portfolio.py."""
    with patch("app.services.market_data._twelvedata_get", new=AsyncMock(return_value={"rate": "0.9"})):
        yield


async def test_projection_with_no_data_is_flat_zero(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    resp = await client.get("/projection?years=5&annual_return_pct=5", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["years"] == 5
    assert len(body["points"]) == 6  # year 0..5 inclusive
    assert Decimal(body["starting_portfolio_value"]) == Decimal("0")
    for point in body["points"]:
        assert Decimal(point["net_worth"]) == Decimal("0")


async def test_projection_grows_portfolio_at_assumed_rate(client, user_a, seeded_stock):
    headers = await login(client, "a@test.dev", "password-a")
    await client.post(
        "/portfolio", json={"ticker": "AAPL", "quantity": "10", "avg_cost": "150"}, headers=headers,
    )
    resp = await client.get("/projection?years=2&annual_return_pct=10", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    points = body["points"]
    starting = Decimal(body["starting_portfolio_value"])
    assert starting > 0
    # year 1 e year 2 devem crescer exatamente ao fator composto de 10%/ano.
    assert Decimal(points[1]["portfolio_value"]) == starting * Decimal("1.1")
    assert Decimal(points[2]["portfolio_value"]) == starting * Decimal("1.1") ** 2


async def test_projection_pays_down_loan_linearly(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    await client.post(
        "/loans",
        json={"name": "Crédito pessoal", "currency": "EUR", "balance": "2400", "monthly_payment": "200"},
        headers=headers,
    )
    resp = await client.get("/projection?years=10&annual_return_pct=0", headers=headers)
    assert resp.status_code == 200
    points = resp.json()["points"]
    # 200/mês x 12 = 2400/ano -> paga por completo no fim do ano 1, e fica a 0 depois.
    assert Decimal(points[0]["loans_balance"]) == Decimal("2400")
    assert Decimal(points[1]["loans_balance"]) == Decimal("0")
    assert Decimal(points[2]["loans_balance"]) == Decimal("0")
    assert Decimal(points[1]["net_worth"]) == Decimal("0")


async def test_projection_loan_without_payment_stays_constant(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    await client.post(
        "/loans", json={"name": "Sem prestação definida", "currency": "EUR", "balance": "5000"}, headers=headers,
    )
    resp = await client.get("/projection?years=3&annual_return_pct=0", headers=headers)
    points = resp.json()["points"]
    for point in points:
        assert Decimal(point["loans_balance"]) == Decimal("5000")


async def test_projection_defaults_years_and_return(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    resp = await client.get("/projection", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["years"] == 20
    assert Decimal(body["annual_return_pct"]) == Decimal("5")
    assert len(body["points"]) == 21


async def test_projection_requires_auth(client):
    resp = await client.get("/projection")
    assert resp.status_code == 401


async def test_projection_grows_other_asset_at_its_own_rate(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    await client.post(
        "/other-assets",
        json={"category": "imovel", "name": "Apartamento", "currency": "EUR", "value": "100000", "expected_return_pct": "3"},
        headers=headers,
    )
    # taxa geral do portfolio (annual_return_pct=10) não deve afetar o ativo,
    # que tem a sua própria taxa (3%) - ver "Cada ativo com a sua própria taxa".
    resp = await client.get("/projection?years=2&annual_return_pct=10", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert Decimal(body["starting_other_assets_value"]) == Decimal("100000")
    points = body["points"]
    assert Decimal(points[0]["other_assets_value"]) == Decimal("100000")
    assert Decimal(points[1]["other_assets_value"]) == Decimal("100000") * Decimal("1.03")
    assert Decimal(points[2]["other_assets_value"]) == Decimal("100000") * Decimal("1.03") ** 2
    assert Decimal(points[1]["net_worth"]) == Decimal(points[1]["portfolio_value"]) + Decimal(points[1]["other_assets_value"])


async def test_projection_other_asset_without_rate_stays_constant(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    await client.post(
        "/other-assets", json={"category": "outro", "name": "Sem taxa definida", "currency": "EUR", "value": "5000"},
        headers=headers,
    )
    resp = await client.get("/projection?years=3&annual_return_pct=10", headers=headers)
    points = resp.json()["points"]
    for point in points:
        assert Decimal(point["other_assets_value"]) == Decimal("5000")


async def test_projection_adds_monthly_savings_to_portfolio(client, user_a, seeded_stock):
    headers = await login(client, "a@test.dev", "password-a")
    await client.post(
        "/portfolio", json={"ticker": "AAPL", "quantity": "10", "avg_cost": "150"}, headers=headers,
    )
    resp = await client.get("/projection?years=2&annual_return_pct=10&monthly_savings=100", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert Decimal(body["monthly_savings"]) == Decimal("100")
    starting = Decimal(body["starting_portfolio_value"])
    points = body["points"]
    # pv0 = starting; pv1 = pv0*1.1 + 1200 (100/mês x 12); pv2 = pv1*1.1 + 1200.
    expected_1 = starting * Decimal("1.1") + Decimal("1200")
    expected_2 = expected_1 * Decimal("1.1") + Decimal("1200")
    assert Decimal(points[1]["portfolio_value"]) == expected_1
    assert Decimal(points[2]["portfolio_value"]) == expected_2


async def test_projection_without_monthly_savings_unchanged(client, user_a, seeded_stock):
    """monthly_savings omitido (0) deve dar exactamente o mesmo resultado de
    antes desta funcionalidade - crescimento composto simples."""
    headers = await login(client, "a@test.dev", "password-a")
    await client.post(
        "/portfolio", json={"ticker": "AAPL", "quantity": "10", "avg_cost": "150"}, headers=headers,
    )
    resp = await client.get("/projection?years=2&annual_return_pct=10", headers=headers)
    body = resp.json()
    assert Decimal(body["monthly_savings"]) == Decimal("0")
    starting = Decimal(body["starting_portfolio_value"])
    points = body["points"]
    assert Decimal(points[1]["portfolio_value"]) == starting * Decimal("1.1")
    assert Decimal(points[2]["portfolio_value"]) == starting * Decimal("1.1") ** 2


async def test_projection_monthly_savings_negative_rejected(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    resp = await client.get("/projection?monthly_savings=-50", headers=headers)
    assert resp.status_code == 422


async def test_projection_isolated_between_users(client, user_a, user_b):
    headers_a = await login(client, "a@test.dev", "password-a")
    headers_b = await login(client, "b@test.dev", "password-b")
    await client.post(
        "/loans", json={"name": "Empréstimo A", "currency": "EUR", "balance": "1000"}, headers=headers_a,
    )
    await client.post(
        "/other-assets", json={"category": "outro", "name": "Ativo A", "currency": "EUR", "value": "2000"},
        headers=headers_a,
    )
    resp_b = await client.get("/projection", headers=headers_b)
    body_b = resp_b.json()
    assert Decimal(body_b["starting_loans_balance"]) == Decimal("0")
    assert Decimal(body_b["starting_other_assets_value"]) == Decimal("0")


async def test_projection_years_out_of_range_rejected(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    resp = await client.get("/projection?years=0", headers=headers)
    assert resp.status_code == 422
    resp2 = await client.get("/projection?years=200", headers=headers)
    assert resp2.status_code == 422
