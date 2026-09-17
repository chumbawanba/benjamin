from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from tests.conftest import login


@pytest.fixture(autouse=True)
def _mock_fx_rate():
    """User.preferred_currency é EUR por defeito - um empréstimo noutra
    moeda (ex: USD) chamaria a Twelve Data a sério sem isto (ver CLAUDE.md:
    nunca chamar Finnhub/Twelve Data diretamente nos testes)."""
    with patch("app.services.market_data._twelvedata_get", new=AsyncMock(return_value={"rate": "0.9"})):
        yield


async def test_create_and_list_loan(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    resp = await client.post(
        "/loans",
        json={"name": "Crédito habitação", "currency": "EUR", "balance": "120000", "interest_rate": "3.2", "monthly_payment": "650"},
        headers=headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Crédito habitação"
    assert Decimal(body["balance"]) == Decimal("120000")
    assert Decimal(body["interest_rate"]) == Decimal("3.2")
    assert Decimal(body["monthly_payment"]) == Decimal("650")
    assert body["display_currency"] == "EUR"
    # Mesma moeda que a preferida -> sem conversão (rate=1), mesmo padrão de
    # test_position_same_currency_no_conversion_call em test_portfolio.py.
    assert Decimal(body["balance_converted"]) == Decimal("120000")

    resp_list = await client.get("/loans", headers=headers)
    assert resp_list.status_code == 200
    assert len(resp_list.json()) == 1


async def test_create_loan_without_optional_fields(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    resp = await client.post(
        "/loans", json={"name": "Cartão de crédito", "currency": "EUR", "balance": "300"}, headers=headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["interest_rate"] is None
    assert body["monthly_payment"] is None


async def test_loan_converted_to_preferred_currency(client, user_a):
    """Empréstimo em USD, preferred_currency por defeito é EUR - mock global
    deste ficheiro devolve sempre rate=0.9."""
    headers = await login(client, "a@test.dev", "password-a")
    resp = await client.post(
        "/loans", json={"name": "Car loan", "currency": "usd", "balance": "10000"}, headers=headers,
    )
    body = resp.json()
    assert body["currency"] == "USD"
    assert body["display_currency"] == "EUR"
    assert Decimal(body["balance_converted"]) == Decimal("10000") * Decimal("0.9")


async def test_update_loan_balance(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    create = await client.post(
        "/loans", json={"name": "Crédito pessoal", "currency": "EUR", "balance": "5000"}, headers=headers,
    )
    loan_id = create.json()["id"]

    resp = await client.put(
        f"/loans/{loan_id}",
        json={"name": "Crédito pessoal", "balance": "4200", "interest_rate": "7.5", "monthly_payment": "200"},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert Decimal(body["balance"]) == Decimal("4200")
    assert Decimal(body["interest_rate"]) == Decimal("7.5")


async def test_delete_loan(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    create = await client.post(
        "/loans", json={"name": "Crédito pessoal", "currency": "EUR", "balance": "1000"}, headers=headers,
    )
    loan_id = create.json()["id"]

    resp = await client.delete(f"/loans/{loan_id}", headers=headers)
    assert resp.status_code == 204

    resp_list = await client.get("/loans", headers=headers)
    assert resp_list.json() == []


async def test_loans_require_auth(client):
    resp_list = await client.get("/loans")
    assert resp_list.status_code == 401
    resp_create = await client.post("/loans", json={"name": "X", "currency": "EUR", "balance": "1"})
    assert resp_create.status_code == 401


async def test_loans_isolated_between_users(client, user_a, user_b):
    headers_a = await login(client, "a@test.dev", "password-a")
    headers_b = await login(client, "b@test.dev", "password-b")

    create = await client.post(
        "/loans", json={"name": "Empréstimo A", "currency": "EUR", "balance": "1000"}, headers=headers_a,
    )
    loan_id = create.json()["id"]

    resp_b_list = await client.get("/loans", headers=headers_b)
    assert resp_b_list.json() == []

    resp_b_update = await client.put(
        f"/loans/{loan_id}", json={"name": "Hack", "balance": "0"}, headers=headers_b,
    )
    assert resp_b_update.status_code == 404

    resp_b_delete = await client.delete(f"/loans/{loan_id}", headers=headers_b)
    assert resp_b_delete.status_code == 404


async def test_update_and_delete_loan_not_found(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp_update = await client.put(
        f"/loans/{fake_id}", json={"name": "X", "balance": "1"}, headers=headers,
    )
    assert resp_update.status_code == 404
    resp_delete = await client.delete(f"/loans/{fake_id}", headers=headers)
    assert resp_delete.status_code == 404


async def test_create_loan_negative_balance_rejected(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    resp = await client.post(
        "/loans", json={"name": "X", "currency": "EUR", "balance": "-100"}, headers=headers,
    )
    assert resp.status_code == 422
