import time

import pytest
from fastapi import HTTPException

from app.services.rate_limit import rate_limit_user


class _DummyUser:
    def __init__(self, id: str):
        self.id = id


async def test_rate_limit_blocks_after_max_calls():
    dep = rate_limit_user("t_blocks", max_calls=3, window_seconds=60)
    user = _DummyUser("user-1")
    for _ in range(3):
        result = await dep(user=user)
        assert result is user
    with pytest.raises(HTTPException) as exc_info:
        await dep(user=user)
    assert exc_info.value.status_code == 429
    assert "Retry-After" in exc_info.value.headers


async def test_rate_limit_resets_after_window(monkeypatch):
    dep = rate_limit_user("t_resets", max_calls=1, window_seconds=10)
    user = _DummyUser("user-2")
    await dep(user=user)
    with pytest.raises(HTTPException):
        await dep(user=user)

    import app.services.rate_limit as rl
    real_now = time.monotonic()
    monkeypatch.setattr(rl.time, "monotonic", lambda: real_now + 11)
    result = await dep(user=user)
    assert result is user


async def test_rate_limit_is_per_user():
    dep = rate_limit_user("t_per_user", max_calls=1, window_seconds=60)
    user_a = _DummyUser("user-3a")
    user_b = _DummyUser("user-3b")
    await dep(user=user_a)
    result = await dep(user=user_b)
    assert result is user_b


async def test_rate_limit_is_per_endpoint_name():
    """O mesmo utilizador não fica bloqueado num endpoint por causa de chamadas
    a outro — cada `name` tem o seu próprio contador."""
    dep_a = rate_limit_user("t_endpoint_a", max_calls=1, window_seconds=60)
    dep_b = rate_limit_user("t_endpoint_b", max_calls=1, window_seconds=60)
    user = _DummyUser("user-4")
    await dep_a(user=user)
    result = await dep_b(user=user)
    assert result is user


async def test_analyst_ask_rate_limited(client, user_a):
    """Integração: exceder o limite em /analyst/ask devolve 429."""
    from tests.conftest import login
    headers = await login(client, "a@test.dev", "password-a")

    for _ in range(10):
        resp = await client.post(
            "/analyst/ask", json={"question": "?", "history": []}, headers=headers,
        )
        assert resp.status_code in (503, 502, 200)

    resp = await client.post(
        "/analyst/ask", json={"question": "?", "history": []}, headers=headers,
    )
    assert resp.status_code == 429
