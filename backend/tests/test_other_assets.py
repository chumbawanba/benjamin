from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from tests.conftest import login


@pytest.fixture(autouse=True)
def _mock_fx_rate():
    """User.preferred_currency é EUR por defeito - um ativo noutra moeda (ex:
    USD) chamaria a Twelve Data a sério sem isto (ver CLAUDE.md: nunca chamar
    Finnhub/Twelve Data diretamente nos testes). Mesmo padrão de
    test_loans.py."""
    with patch("app.services.market_data._twelvedata_get", new=AsyncMock(return_value={"rate": "0.9"})):
        yield


async def test_create_and_list_other_asset(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    resp = await client.post(
        "/other-assets",
        json={"category": "imovel", "name": "Apartamento T2", "currency": "EUR", "value": "180000", "expected_return_pct": "2.5"},
        headers=headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["category"] == "imovel"
    assert body["name"] == "Apartamento T2"
    assert Decimal(body["value"]) == Decimal("180000")
    assert Decimal(body["expected_return_pct"]) == Decimal("2.5")
    assert body["display_currency"] == "EUR"
    # Mesma moeda que a preferida -> sem conversão (rate=1).
    assert Decimal(body["value_converted"]) == Decimal("180000")

    resp_list = await client.get("/other-assets", headers=headers)
    assert resp_list.status_code == 200
    assert len(resp_list.json()) == 1


async def test_create_other_asset_without_optional_fields(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    resp = await client.post(
        "/other-assets", json={"category": "outro", "name": "Certificados de aforro", "currency": "EUR", "value": "5000"},
        headers=headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["expected_return_pct"] is None


async def test_create_other_asset_invalid_category_rejected(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    resp = await client.post(
        "/other-assets", json={"category": "carro", "name": "X", "currency": "EUR", "value": "1"}, headers=headers,
    )
    assert resp.status_code == 422


async def test_other_asset_converted_to_preferred_currency(client, user_a):
    """Ativo em USD, preferred_currency por defeito é EUR - mock global deste
    ficheiro devolve sempre rate=0.9."""
    headers = await login(client, "a@test.dev", "password-a")
    resp = await client.post(
        "/other-assets", json={"category": "outro", "name": "US Treasury", "currency": "usd", "value": "10000"},
        headers=headers,
    )
    body = resp.json()
    assert body["currency"] == "USD"
    assert body["display_currency"] == "EUR"
    assert Decimal(body["value_converted"]) == Decimal("10000") * Decimal("0.9")


async def test_update_other_asset_value(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    create = await client.post(
        "/other-assets", json={"category": "imovel", "name": "Casa", "currency": "EUR", "value": "150000"},
        headers=headers,
    )
    asset_id = create.json()["id"]

    resp = await client.put(
        f"/other-assets/{asset_id}",
        json={"name": "Casa (reavaliada)", "value": "160000", "expected_return_pct": "3"},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert Decimal(body["value"]) == Decimal("160000")
    assert Decimal(body["expected_return_pct"]) == Decimal("3")
    assert body["name"] == "Casa (reavaliada)"


async def test_delete_other_asset(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    create = await client.post(
        "/other-assets", json={"category": "outro", "name": "X", "currency": "EUR", "value": "1000"}, headers=headers,
    )
    asset_id = create.json()["id"]

    resp = await client.delete(f"/other-assets/{asset_id}", headers=headers)
    assert resp.status_code == 204

    resp_list = await client.get("/other-assets", headers=headers)
    assert resp_list.json() == []


async def test_other_assets_require_auth(client):
    resp_list = await client.get("/other-assets")
    assert resp_list.status_code == 401
    resp_create = await client.post("/other-assets", json={"category": "outro", "name": "X", "currency": "EUR", "value": "1"})
    assert resp_create.status_code == 401


async def test_other_assets_isolated_between_users(client, user_a, user_b):
    headers_a = await login(client, "a@test.dev", "password-a")
    headers_b = await login(client, "b@test.dev", "password-b")

    create = await client.post(
        "/other-assets", json={"category": "imovel", "name": "Casa A", "currency": "EUR", "value": "1000"},
        headers=headers_a,
    )
    asset_id = create.json()["id"]

    resp_b_list = await client.get("/other-assets", headers=headers_b)
    assert resp_b_list.json() == []

    resp_b_update = await client.put(
        f"/other-assets/{asset_id}", json={"name": "Hack", "value": "0"}, headers=headers_b,
    )
    assert resp_b_update.status_code == 404

    resp_b_delete = await client.delete(f"/other-assets/{asset_id}", headers=headers_b)
    assert resp_b_delete.status_code == 404


async def test_update_and_delete_other_asset_not_found(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp_update = await client.put(
        f"/other-assets/{fake_id}", json={"name": "X", "value": "1"}, headers=headers,
    )
    assert resp_update.status_code == 404
    resp_delete = await client.delete(f"/other-assets/{fake_id}", headers=headers)
    assert resp_delete.status_code == 404


async def test_create_other_asset_negative_value_rejected(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    resp = await client.post(
        "/other-assets", json={"category": "outro", "name": "X", "currency": "EUR", "value": "-100"}, headers=headers,
    )
    assert resp.status_code == 422
