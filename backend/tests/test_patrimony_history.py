from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from tests.conftest import login


@pytest.fixture(autouse=True)
def _mock_fx_rate():
    """seeded_stock é USD e User.preferred_currency é EUR por defeito - sem
    isto, chamaria a Twelve Data a sério (ver CLAUDE.md). Mesmo padrão de
    test_projection.py/test_other_assets.py."""
    with patch("app.services.market_data._twelvedata_get", new=AsyncMock(return_value={"rate": "0.9"})):
        yield


async def test_current_totals_with_no_data_is_zero(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    resp = await client.get("/patrimony-history/current-totals", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["currency"] == "EUR"
    for field in ("stocks_value", "cash_value", "other_assets_value", "loans_balance"):
        assert Decimal(body[field]) == Decimal("0")


async def test_current_totals_splits_stocks_cash_other_assets_and_loans(client, user_a, seeded_stock):
    headers = await login(client, "a@test.dev", "password-a")
    await client.post("/portfolio", json={"ticker": "AAPL", "quantity": "10", "avg_cost": "150"}, headers=headers)
    await client.post("/portfolio/cash", json={"currency": "EUR", "amount": "1000"}, headers=headers)
    await client.post(
        "/other-assets", json={"category": "imovel", "name": "Casa", "currency": "EUR", "value": "200000"},
        headers=headers,
    )
    await client.post(
        "/loans", json={"name": "Crédito", "currency": "EUR", "balance": "50000"}, headers=headers,
    )

    resp = await client.get("/patrimony-history/current-totals", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert Decimal(body["stocks_value"]) > 0
    assert Decimal(body["cash_value"]) == Decimal("1000")
    assert Decimal(body["other_assets_value"]) == Decimal("200000")
    assert Decimal(body["loans_balance"]) == Decimal("50000")


async def test_create_and_list_snapshot(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    resp = await client.post(
        "/patrimony-history",
        json={
            "date": "2025-01-01", "currency": "EUR", "stocks_value": "10000", "cash_value": "1000",
            "other_assets_value": "0", "loans_balance": "0",
        },
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["date"] == "2025-01-01"
    assert Decimal(body["net_worth"]) == Decimal("11000")
    assert body["note"] is None

    resp_list = await client.get("/patrimony-history", headers=headers)
    assert resp_list.status_code == 200
    assert len(resp_list.json()) == 1


async def test_snapshot_with_note(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    resp = await client.post(
        "/patrimony-history",
        json={
            "date": "2025-06-15", "currency": "EUR", "stocks_value": "20000", "cash_value": "5000",
            "other_assets_value": "180000", "loans_balance": "140000",
            "note": "Compra de casa: cash -40k, imóvel +180k, dívida +140k",
        },
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["note"] == "Compra de casa: cash -40k, imóvel +180k, dívida +140k"
    assert Decimal(body["net_worth"]) == Decimal("20000") + Decimal("5000") + Decimal("180000") - Decimal("140000")


async def test_upsert_same_date_replaces_entry(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    await client.post(
        "/patrimony-history",
        json={
            "date": "2025-01-01", "currency": "EUR", "stocks_value": "1000", "cash_value": "0",
            "other_assets_value": "0", "loans_balance": "0",
        },
        headers=headers,
    )
    resp = await client.post(
        "/patrimony-history",
        json={
            "date": "2025-01-01", "currency": "EUR", "stocks_value": "2000", "cash_value": "500",
            "other_assets_value": "0", "loans_balance": "0",
        },
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert Decimal(body["stocks_value"]) == Decimal("2000")

    resp_list = await client.get("/patrimony-history", headers=headers)
    # Continua a ser uma única entrada para essa data, não duas.
    assert len(resp_list.json()) == 1


async def test_list_ordered_by_date(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    for d in ("2025-03-01", "2025-01-01", "2025-02-01"):
        await client.post(
            "/patrimony-history",
            json={
                "date": d, "currency": "EUR", "stocks_value": "1000", "cash_value": "0",
                "other_assets_value": "0", "loans_balance": "0",
            },
            headers=headers,
        )
    resp = await client.get("/patrimony-history", headers=headers)
    dates = [s["date"] for s in resp.json()]
    assert dates == ["2025-01-01", "2025-02-01", "2025-03-01"]


async def test_delete_snapshot(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    create = await client.post(
        "/patrimony-history",
        json={
            "date": "2025-01-01", "currency": "EUR", "stocks_value": "1000", "cash_value": "0",
            "other_assets_value": "0", "loans_balance": "0",
        },
        headers=headers,
    )
    snap_id = create.json()["id"]

    resp = await client.delete(f"/patrimony-history/{snap_id}", headers=headers)
    assert resp.status_code == 204

    resp_list = await client.get("/patrimony-history", headers=headers)
    assert resp_list.json() == []


async def test_delete_snapshot_not_found(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.delete(f"/patrimony-history/{fake_id}", headers=headers)
    assert resp.status_code == 404


async def test_patrimony_history_requires_auth(client):
    resp_list = await client.get("/patrimony-history")
    assert resp_list.status_code == 401
    resp_totals = await client.get("/patrimony-history/current-totals")
    assert resp_totals.status_code == 401
    resp_create = await client.post(
        "/patrimony-history",
        json={
            "date": "2025-01-01", "currency": "EUR", "stocks_value": "0", "cash_value": "0",
            "other_assets_value": "0", "loans_balance": "0",
        },
    )
    assert resp_create.status_code == 401


async def test_patrimony_history_isolated_between_users(client, user_a, user_b):
    headers_a = await login(client, "a@test.dev", "password-a")
    headers_b = await login(client, "b@test.dev", "password-b")

    create = await client.post(
        "/patrimony-history",
        json={
            "date": "2025-01-01", "currency": "EUR", "stocks_value": "1000", "cash_value": "0",
            "other_assets_value": "0", "loans_balance": "0",
        },
        headers=headers_a,
    )
    snap_id = create.json()["id"]

    resp_b_list = await client.get("/patrimony-history", headers=headers_b)
    assert resp_b_list.json() == []

    resp_b_delete = await client.delete(f"/patrimony-history/{snap_id}", headers=headers_b)
    assert resp_b_delete.status_code == 404


async def test_create_snapshot_negative_value_rejected(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    resp = await client.post(
        "/patrimony-history",
        json={
            "date": "2025-01-01", "currency": "EUR", "stocks_value": "-100", "cash_value": "0",
            "other_assets_value": "0", "loans_balance": "0",
        },
        headers=headers,
    )
    assert resp.status_code == 422
