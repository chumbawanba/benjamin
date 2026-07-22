from tests.conftest import login


async def test_register_and_login(client):
    resp = await client.post("/auth/register", json={
        "email": "novo@test.dev", "password": "12345678", "accepted_terms": True})
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
        "email": "x@test.dev", "password": "12345678", "accepted_terms": True})
    assert resp.status_code == 403


async def test_register_without_accepting_terms_rejected(client):
    resp = await client.post("/auth/register", json={
        "email": "semaceite@test.dev", "password": "12345678"})
    assert resp.status_code == 422

    resp2 = await client.post("/auth/register", json={
        "email": "semaceite@test.dev", "password": "12345678", "accepted_terms": False})
    assert resp2.status_code == 422


async def test_register_records_accepted_terms_at(client, db_session):
    from sqlalchemy import select
    from app.models import User

    resp = await client.post("/auth/register", json={
        "email": "aceitou@test.dev", "password": "12345678", "accepted_terms": True})
    assert resp.status_code == 201

    user = (
        await db_session.execute(select(User).where(User.email == "aceitou@test.dev"))
    ).scalar_one()
    assert user.accepted_terms_at is not None


async def test_protected_endpoint_without_token(client):
    resp = await client.get("/watchlist")
    assert resp.status_code == 401
