from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from tests.conftest import login

from app.config import settings
from app.models import Position, StrategyItem, StrategyTemplate, WatchlistItem


def _mock_openai_response(text: str):
    choice = MagicMock()
    choice.message.content = text
    response = MagicMock()
    response.choices = [choice]
    return response


def mock_openai(text: str = "Resumo gerado de teste."):
    """Substitui AsyncOpenAI por um cliente falso cujo chat.completions.create
    devolve `text`, sem tocar na rede."""
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=_mock_openai_response(text))
    return patch("app.services.analyst.AsyncOpenAI", return_value=mock_client)


def mock_market_pulse():
    return patch(
        "app.services.analyst.market_data.get_market_pulse",
        new=AsyncMock(return_value={
            "indices": [{"symbol": "SPY", "label": "S&P 500", "change_pct": 0.5}],
            "news": [{"headline": "Mercado sobe", "source": "Reuters", "url": "http://x"}],
        }),
    )


async def test_get_summary_returns_null_when_never_generated(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    resp = await client.get("/analyst/summary", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == {"summary": None, "generated_at": None}


async def test_refresh_without_api_key_returns_503(client, user_a, monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")
    headers = await login(client, "a@test.dev", "password-a")
    resp = await client.post("/analyst/summary/refresh", headers=headers)
    assert resp.status_code == 503


async def test_refresh_generates_and_persists_summary(client, db_session, user_a, seeded_stock, monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "fake-key")
    db_session.add(WatchlistItem(user_id=user_a.id, stock_id=seeded_stock.id))
    await db_session.commit()

    headers = await login(client, "a@test.dev", "password-a")
    with mock_market_pulse(), mock_openai("AAPL está a subir de forma consistente."):
        resp = await client.post("/analyst/summary/refresh", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["summary"] == "AAPL está a subir de forma consistente."
    assert body["generated_at"] is not None

    # persistiu — o GET seguinte devolve o mesmo texto sem chamar o LLM outra vez
    resp2 = await client.get("/analyst/summary", headers=headers)
    assert resp2.status_code == 200
    assert resp2.json()["summary"] == body["summary"]
    assert resp2.json()["generated_at"] == body["generated_at"]


async def test_refresh_handles_openai_failure(client, user_a, monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "fake-key")
    headers = await login(client, "a@test.dev", "password-a")
    with mock_market_pulse():
        with patch("app.services.analyst.AsyncOpenAI", side_effect=Exception("boom")):
            resp = await client.post("/analyst/summary/refresh", headers=headers)
    assert resp.status_code == 502


async def test_get_prompt_defaults_to_builtin(client, user_a):
    from app.services.analyst import DEFAULT_SYSTEM_PROMPT

    headers = await login(client, "a@test.dev", "password-a")
    resp = await client.get("/analyst/prompt", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_default"] is True
    assert body["prompt"] == DEFAULT_SYSTEM_PROMPT
    assert "Benjamin" in body["prompt"]


async def test_update_prompt_persists_custom_text(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    resp = await client.put("/analyst/prompt", json={"prompt": "Sê muito conciso, 1 frase só."}, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_default"] is False
    assert body["prompt"] == "Sê muito conciso, 1 frase só."

    resp2 = await client.get("/analyst/prompt", headers=headers)
    assert resp2.json()["prompt"] == "Sê muito conciso, 1 frase só."


async def test_update_prompt_empty_resets_to_default(client, user_a):
    from app.services.analyst import DEFAULT_SYSTEM_PROMPT

    headers = await login(client, "a@test.dev", "password-a")
    await client.put("/analyst/prompt", json={"prompt": "algo personalizado"}, headers=headers)
    resp = await client.put("/analyst/prompt", json={"prompt": "   "}, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_default"] is True
    assert body["prompt"] == DEFAULT_SYSTEM_PROMPT


async def test_update_prompt_too_long_rejected(client, user_a):
    from app.services.analyst import MAX_PROMPT_LENGTH

    headers = await login(client, "a@test.dev", "password-a")
    resp = await client.put(
        "/analyst/prompt", json={"prompt": "x" * (MAX_PROMPT_LENGTH + 1)}, headers=headers,
    )
    assert resp.status_code == 422


async def test_refresh_uses_custom_prompt(client, user_a, monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "fake-key")
    headers = await login(client, "a@test.dev", "password-a")
    await client.put("/analyst/prompt", json={"prompt": "Instrução personalizada única."}, headers=headers)

    with mock_market_pulse():
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=_mock_openai_response("ok"))
        with patch("app.services.analyst.AsyncOpenAI", return_value=mock_client):
            resp = await client.post("/analyst/summary/refresh", headers=headers)
    assert resp.status_code == 200

    sent_messages = mock_client.chat.completions.create.call_args.kwargs["messages"]
    assert sent_messages[0]["role"] == "system"
    assert sent_messages[0]["content"] == "Instrução personalizada única."


async def test_refresh_context_includes_portfolio_exposure(client, db_session, user_a, seeded_stock, monkeypatch):
    """O contexto enviado ao LLM deve incluir as posições reais do utilizador
    (não só a watchlist) e sinalizar se uma ação da watchlist já é possuída,
    para o Benjamin poder falar de exposição e oportunidades."""
    monkeypatch.setattr(settings, "openai_api_key", "fake-key")
    db_session.add(Position(user_id=user_a.id, stock_id=seeded_stock.id, quantity=10, avg_cost=100))
    db_session.add(WatchlistItem(user_id=user_a.id, stock_id=seeded_stock.id))
    await db_session.commit()

    headers = await login(client, "a@test.dev", "password-a")
    with mock_market_pulse():
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=_mock_openai_response("ok"))
        with patch("app.services.analyst.AsyncOpenAI", return_value=mock_client):
            resp = await client.post("/analyst/summary/refresh", headers=headers)
    assert resp.status_code == 200

    context = mock_client.chat.completions.create.call_args.kwargs["messages"][1]["content"]
    assert "Portfólio do utilizador" in context
    assert "AAPL" in context
    assert "já possui" in context


async def test_refresh_context_includes_fundamentals(client, db_session, user_a, seeded_stock, monkeypatch):
    """seeded_stock grava P/E=12.0 e dividend_yield=0.005 (0.5%) - devem
    aparecer no contexto enviado ao LLM (antes só ia preço/variação/sinal)."""
    monkeypatch.setattr(settings, "openai_api_key", "fake-key")
    db_session.add(WatchlistItem(user_id=user_a.id, stock_id=seeded_stock.id))
    await db_session.commit()

    headers = await login(client, "a@test.dev", "password-a")
    with mock_market_pulse():
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=_mock_openai_response("ok"))
        with patch("app.services.analyst.AsyncOpenAI", return_value=mock_client):
            resp = await client.post("/analyst/summary/refresh", headers=headers)
    assert resp.status_code == 200

    context = mock_client.chat.completions.create.call_args.kwargs["messages"][1]["content"]
    assert "P/E 12.0" in context
    assert "dividendo 0.5%" in context


async def test_ask_requires_auth(client):
    resp = await client.post("/analyst/ask", json={"question": "Alguma coisa?"})
    assert resp.status_code == 401


async def test_ask_without_api_key_returns_503(client, user_a, monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")
    headers = await login(client, "a@test.dev", "password-a")
    resp = await client.post("/analyst/ask", json={"question": "Alguma coisa?"}, headers=headers)
    assert resp.status_code == 503


async def test_ask_question_too_long_rejected(client, user_a, monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "fake-key")
    headers = await login(client, "a@test.dev", "password-a")
    resp = await client.post("/analyst/ask", json={"question": "x" * 1001}, headers=headers)
    assert resp.status_code == 422


async def test_ask_uses_context_criteria_and_history(client, db_session, user_a, seeded_stock, monkeypatch):
    """O contexto enviado ao LLM deve incluir o detalhe critério-a-critério da
    avaliação (não só o sinal final, ao contrário do resumo), o histórico da
    conversa é reenviado tal como veio, e a pergunta nova é a última mensagem."""
    monkeypatch.setattr(settings, "openai_api_key", "fake-key")
    template = StrategyTemplate(user_id=user_a.id, name="Value simples")
    db_session.add(template)
    await db_session.flush()
    db_session.add(StrategyItem(
        template_id=template.id, name="RSI sobrevendido", metric="RSI_14",
        operator="<", threshold_value=Decimal("30"), weight=Decimal("2"), direction="buy_signal",
    ))
    db_session.add(WatchlistItem(user_id=user_a.id, stock_id=seeded_stock.id))
    await db_session.commit()

    headers = await login(client, "a@test.dev", "password-a")
    run_resp = await client.post(
        "/evaluations/run", json={"template_id": str(template.id)}, headers=headers
    )
    assert run_resp.status_code == 200

    with mock_market_pulse():
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            return_value=_mock_openai_response("Não tens sinal de compra porque o RSI não está sobrevendido.")
        )
        with patch("app.services.analyst.AsyncOpenAI", return_value=mock_client):
            resp = await client.post(
                "/analyst/ask",
                json={
                    "question": "Porque não tenho sinal de compra na AAPL?",
                    "history": [
                        {"role": "user", "content": "Olá"},
                        {"role": "assistant", "content": "Olá, em que posso ajudar?"},
                    ],
                },
                headers=headers,
            )
    assert resp.status_code == 200
    assert "RSI" in resp.json()["answer"]

    messages = mock_client.chat.completions.create.call_args.kwargs["messages"]
    assert messages[0]["role"] == "system"
    assert "critério-a-critério" in messages[0]["content"]
    assert messages[1]["role"] == "user"
    assert "RSI sobrevendido" in messages[1]["content"]  # detalhe critério-a-critério
    assert messages[2] == {"role": "user", "content": "Olá"}
    assert messages[3] == {"role": "assistant", "content": "Olá, em que posso ajudar?"}
    assert messages[-1] == {"role": "user", "content": "Porque não tenho sinal de compra na AAPL?"}


async def test_summary_isolated_between_users(client, db_session, user_a, user_b, seeded_stock, monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "fake-key")
    db_session.add(WatchlistItem(user_id=user_a.id, stock_id=seeded_stock.id))
    await db_session.commit()

    headers_a = await login(client, "a@test.dev", "password-a")
    headers_b = await login(client, "b@test.dev", "password-b")

    with mock_market_pulse(), mock_openai("Resumo do utilizador A"):
        await client.post("/analyst/summary/refresh", headers=headers_a)

    resp_b = await client.get("/analyst/summary", headers=headers_b)
    assert resp_b.json()["summary"] is None
