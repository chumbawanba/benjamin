from sqlalchemy import select

from app.models import WaitlistEntry


async def test_join_waitlist(client, db_session):
    resp = await client.post(
        "/waitlist", json={"email": "interessado@test.dev", "accepted_terms": True}
    )
    assert resp.status_code == 204

    entries = (await db_session.execute(select(WaitlistEntry))).scalars().all()
    assert len(entries) == 1
    assert entries[0].email == "interessado@test.dev"
    assert entries[0].accepted_terms_at is not None


async def test_join_waitlist_duplicate_is_idempotent(client, db_session):
    resp1 = await client.post(
        "/waitlist", json={"email": "repetido@test.dev", "accepted_terms": True}
    )
    resp2 = await client.post(
        "/waitlist", json={"email": "repetido@test.dev", "accepted_terms": True}
    )
    assert resp1.status_code == 204
    assert resp2.status_code == 204

    entries = (await db_session.execute(select(WaitlistEntry))).scalars().all()
    assert len(entries) == 1


async def test_join_waitlist_invalid_email_rejected(client):
    resp = await client.post(
        "/waitlist", json={"email": "não-é-email", "accepted_terms": True}
    )
    assert resp.status_code == 422


async def test_join_waitlist_no_auth_required(client):
    """Endpoint público - não deve exigir Authorization."""
    resp = await client.post(
        "/waitlist", json={"email": "publico@test.dev", "accepted_terms": True}
    )
    assert resp.status_code == 204


async def test_join_waitlist_without_accepting_terms_rejected(client, db_session):
    resp = await client.post("/waitlist", json={"email": "semaceite@test.dev"})
    assert resp.status_code == 422

    resp2 = await client.post(
        "/waitlist", json={"email": "semaceite@test.dev", "accepted_terms": False}
    )
    assert resp2.status_code == 422

    entries = (await db_session.execute(select(WaitlistEntry))).scalars().all()
    assert entries == []
