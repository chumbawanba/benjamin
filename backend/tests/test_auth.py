from tests.conftest import login


async def test_register_and_login(client):
    resp = await client.post("/auth/register", json={
        "email": "novo@test.dev", "password": "12345678"})
    assert resp.status_code == 201
    assert "access_token" in resp.json()

    resp = await client.post("/auth/login", json={
        "email": "novo@test.dev", "password": "12345678"})
    assert resp.status_code == 200


async def test_login_wrong_password(client, user_a):
    resp = await client.post("/auth/login", json={
        "email": "a@test.dev", "password": "errada123"})
    assert resp.status_code == 401


async def test_registration_disabled(client, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "allow_registration", False)
    resp = await client.post("/auth/register", json={
        "email": "x@test.dev", "password": "12345678"})
    assert resp.status_code == 403


async def test_protected_endpoint_without_token(client):
    resp = await client.get("/watchlist")
    assert resp.status_code == 401
