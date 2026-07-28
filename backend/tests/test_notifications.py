from tests.conftest import login

from app.models import Notification


async def _add_notification(db_session, user, **kwargs):
    kwargs.setdefault("kind", "price_buy")
    kwargs.setdefault("message", "AAPL atingiu o teu preço-alvo de compra")
    notification = Notification(user_id=user.id, **kwargs)
    db_session.add(notification)
    await db_session.commit()
    await db_session.refresh(notification)
    return notification


async def test_list_notifications_requires_auth(client):
    resp = await client.get("/notifications")
    assert resp.status_code == 401


async def test_list_notifications_returns_most_recent_first(client, db_session, user_a):
    n1 = await _add_notification(db_session, user_a, message="primeira")
    n2 = await _add_notification(db_session, user_a, message="segunda")

    headers = await login(client, "a@test.dev", "password-a")
    resp = await client.get("/notifications", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert [n["id"] for n in body] == [str(n2.id), str(n1.id)]


async def test_list_notifications_isolated_between_users(client, db_session, user_a, user_b):
    await _add_notification(db_session, user_a)

    headers_b = await login(client, "b@test.dev", "password-b")
    resp = await client.get("/notifications", headers=headers_b)
    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_notifications_unread_only(client, db_session, user_a):
    from datetime import datetime, timezone

    read = await _add_notification(db_session, user_a, message="lida")
    read.read_at = datetime.now(timezone.utc)
    await db_session.commit()
    await _add_notification(db_session, user_a, message="não lida")

    headers = await login(client, "a@test.dev", "password-a")
    resp = await client.get("/notifications?unread_only=true", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["message"] == "não lida"


async def test_mark_notification_read(client, db_session, user_a):
    notification = await _add_notification(db_session, user_a)
    headers = await login(client, "a@test.dev", "password-a")

    resp = await client.put(f"/notifications/{notification.id}/read", headers=headers)
    assert resp.status_code == 204

    resp = await client.get("/notifications", headers=headers)
    assert resp.json()[0]["read_at"] is not None


async def test_mark_notification_read_not_found_for_other_user(client, db_session, user_a, user_b):
    notification = await _add_notification(db_session, user_a)
    headers_b = await login(client, "b@test.dev", "password-b")

    resp = await client.put(f"/notifications/{notification.id}/read", headers=headers_b)
    assert resp.status_code == 404


async def test_get_preferences_defaults_enabled(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    resp = await client.get("/notifications/preferences", headers=headers)
    assert resp.status_code == 200
    # report_day_of_week=5/report_hour=8 (sábado 08:00 UTC) preserva o
    # comportamento do antigo cron fixo para quem nunca alterou a preferência.
    assert resp.json() == {
        "email_reports_enabled": True, "email_alerts_enabled": True,
        "report_day_of_week": 5, "report_hour": 8,
    }


async def test_update_preferences(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    resp = await client.put(
        "/notifications/preferences",
        json={
            "email_reports_enabled": False, "email_alerts_enabled": True,
            "report_day_of_week": 2, "report_hour": 19,
        },
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json() == {
        "email_reports_enabled": False, "email_alerts_enabled": True,
        "report_day_of_week": 2, "report_hour": 19,
    }

    resp = await client.get("/notifications/preferences", headers=headers)
    body = resp.json()
    assert body["email_reports_enabled"] is False
    assert body["report_day_of_week"] == 2
    assert body["report_hour"] == 19


async def test_update_preferences_rejects_invalid_day_of_week(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    resp = await client.put(
        "/notifications/preferences",
        json={
            "email_reports_enabled": True, "email_alerts_enabled": True,
            "report_day_of_week": 7, "report_hour": 8,
        },
        headers=headers,
    )
    assert resp.status_code == 422


async def test_update_preferences_rejects_invalid_hour(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    resp = await client.put(
        "/notifications/preferences",
        json={
            "email_reports_enabled": True, "email_alerts_enabled": True,
            "report_day_of_week": 0, "report_hour": 24,
        },
        headers=headers,
    )
    assert resp.status_code == 422


async def test_unsubscribe_disables_both_email_toggles(client, db_session, user_a):
    token = user_a.unsubscribe_token
    resp = await client.get(f"/notifications/unsubscribe/{token}")
    assert resp.status_code == 204

    await db_session.refresh(user_a)
    assert user_a.email_reports_enabled is False
    assert user_a.email_alerts_enabled is False


async def test_unsubscribe_invalid_token(client):
    resp = await client.get("/notifications/unsubscribe/does-not-exist")
    assert resp.status_code == 404


async def test_unsubscribe_is_idempotent(client, user_a):
    token = user_a.unsubscribe_token
    resp1 = await client.get(f"/notifications/unsubscribe/{token}")
    resp2 = await client.get(f"/notifications/unsubscribe/{token}")
    assert resp1.status_code == 204
    assert resp2.status_code == 204
