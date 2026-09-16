from datetime import datetime, timezone

from app.config import settings
from app.models import User, WaitlistEntry
from app.security import hash_password


async def test_admin_stats_returns_counts_lists_and_daily(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "admin_api_key", "test-admin-key")
    db_session.add(User(email="a@test.dev", password_hash=hash_password("password-a")))
    db_session.add(User(email="b@test.dev", password_hash=hash_password("password-b")))
    db_session.add(WaitlistEntry(email="c@test.dev"))
    await db_session.commit()

    resp = await client.get("/admin/stats", headers={"X-Admin-Key": "test-admin-key"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["users_total"] == 2
    assert body["waitlist_total"] == 1
    assert {u["email"] for u in body["users"]} == {"a@test.dev", "b@test.dev"}
    assert [w["email"] for w in body["waitlist"]] == ["c@test.dev"]

    today = datetime.now(timezone.utc).date().isoformat()
    assert body["daily_registrations"] == [{"date": today, "users": 2, "waitlist": 1}]


async def test_admin_stats_no_key_header_rejected(client, monkeypatch):
    monkeypatch.setattr(settings, "admin_api_key", "test-admin-key")

    resp = await client.get("/admin/stats")

    assert resp.status_code == 401


async def test_admin_stats_wrong_key_rejected(client, monkeypatch):
    monkeypatch.setattr(settings, "admin_api_key", "test-admin-key")

    resp = await client.get("/admin/stats", headers={"X-Admin-Key": "chave-errada"})

    assert resp.status_code == 401


async def test_admin_stats_unconfigured_key_always_rejects(client, monkeypatch):
    """Fail-closed: mesmo com o header certo, sem ADMIN_API_KEY definida no
    servidor o endpoint nunca autoriza (ver security.py::require_admin)."""
    monkeypatch.setattr(settings, "admin_api_key", "")

    resp = await client.get("/admin/stats", headers={"X-Admin-Key": ""})

    assert resp.status_code == 401


async def test_admin_stats_empty_when_no_registrations(client, monkeypatch):
    monkeypatch.setattr(settings, "admin_api_key", "test-admin-key")

    resp = await client.get("/admin/stats", headers={"X-Admin-Key": "test-admin-key"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["users_total"] == 0
    assert body["waitlist_total"] == 0
    assert body["users"] == []
    assert body["waitlist"] == []
    assert body["daily_registrations"] == []
