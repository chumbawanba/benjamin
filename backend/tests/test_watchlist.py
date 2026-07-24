from decimal import Decimal

from tests.conftest import login, mock_market_data_valid

from app.routers.watchlist import _rolling_sma


def test_rolling_sma_matches_manual_average():
    closes = [Decimal(str(i)) for i in range(1, 251)]  # 1..250
    result = _rolling_sma(200, closes)
    assert len(result) == 250
    assert all(v is None for v in result[:199])  # <200 pontos ainda -> None
    # janela dos primeiros 200 valores (1..200): média = 100.5
    assert result[199] == 100.5
    # última janela (51..250): média = 150.5
    assert result[249] == 150.5


def test_rolling_sma_handles_none_closes():
    closes = [Decimal("10")] * 5 + [None] + [Decimal("10")] * 194  # type: ignore[list-item]
    result = _rolling_sma(200, closes)
    assert len(result) == 200
    assert result[-1] is None  # janela ainda contém o None


async def test_add_and_list(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    with mock_market_data_valid():
        resp = await client.post("/watchlist", json={"ticker": "aapl"}, headers=headers)
    assert resp.status_code == 201
    assert resp.json()["stock"]["ticker"] == "AAPL"

    resp = await client.get("/watchlist", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


async def test_duplicate_rejected(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    with mock_market_data_valid():
        await client.post("/watchlist", json={"ticker": "AAPL"}, headers=headers)
        resp = await client.post("/watchlist", json={"ticker": "AAPL"}, headers=headers)
    assert resp.status_code == 422


async def test_invalid_ticker(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    from unittest.mock import AsyncMock, patch

    with patch("app.services.market_data._finnhub_get", new=AsyncMock(return_value={})):
        resp = await client.post("/watchlist", json={"ticker": "XXXXXX"}, headers=headers)
    assert resp.status_code == 422


async def test_add_ticker_when_finnhub_unavailable(client, user_a):
    """Se a Finnhub estiver em baixo/rate-limited (excepção), o ticker é aceite na
    mesma, sem metadados, em vez de rejeitado (ver services/market_data.py)."""
    headers = await login(client, "a@test.dev", "password-a")
    from unittest.mock import AsyncMock, patch

    with patch(
        "app.services.market_data._finnhub_get",
        new=AsyncMock(side_effect=Exception("429 Too Many Requests")),
    ):
        resp = await client.post("/watchlist", json={"ticker": "AAPL"}, headers=headers)
    assert resp.status_code == 201
    assert resp.json()["stock"]["ticker"] == "AAPL"
    assert resp.json()["stock"]["name"] is None


async def test_search_stocks(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    from unittest.mock import AsyncMock, patch

    fake_response = {
        "count": 1,
        "result": [
            {"symbol": "AAPL", "description": "Apple Inc.", "displaySymbol": "AAPL", "type": "Common Stock"},
        ],
    }
    with patch("app.services.market_data._finnhub_get", new=AsyncMock(return_value=fake_response)):
        resp = await client.get("/watchlist/search?q=apple", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body[0]["ticker"] == "AAPL"
    assert body[0]["name"] == "Apple Inc."


async def test_search_stocks_failure_returns_empty(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    from unittest.mock import AsyncMock, patch

    with patch(
        "app.services.market_data._finnhub_get",
        new=AsyncMock(side_effect=Exception("429 Too Many Requests")),
    ):
        resp = await client.get("/watchlist/search?q=apple", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []


async def test_watchlist_news(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    from unittest.mock import AsyncMock, patch

    with mock_market_data_valid():
        await client.post("/watchlist", json={"ticker": "AAPL"}, headers=headers)

    fake_news = [
        {
            "headline": "Apple anuncia resultados",
            "summary": "resumo",
            "url": "https://example.com/a",
            "source": "Reuters",
            "datetime": 1750000000,
        },
    ]
    with patch("app.services.market_data._finnhub_get", new=AsyncMock(return_value=fake_news)):
        resp = await client.get("/watchlist/news", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["ticker"] == "AAPL"
    assert body[0]["headline"] == "Apple anuncia resultados"


async def test_watchlist_news_dedupes_same_story_across_tickers(client, user_a):
    """A Finnhub devolve por vezes a mesma noticia (ex: mercado em geral) para
    varios tickers diferentes — nao deve aparecer duplicada no feed."""
    headers = await login(client, "a@test.dev", "password-a")
    from unittest.mock import AsyncMock, patch

    with mock_market_data_valid():
        await client.post("/watchlist", json={"ticker": "AAPL"}, headers=headers)
        await client.post("/watchlist", json={"ticker": "MSFT"}, headers=headers)

    fake_news = [
        {
            "headline": "Stock Market Today: Stocks Slide",
            "summary": "resumo",
            "url": "https://example.com/mercado-em-queda",
            "source": "Yahoo",
            "datetime": 1750000000,
        },
    ]
    with patch("app.services.market_data._finnhub_get", new=AsyncMock(return_value=fake_news)):
        resp = await client.get("/watchlist/news", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1  # apareceria 2x (uma por ticker) sem o dedup


async def test_watchlist_news_empty_watchlist(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    resp = await client.get("/watchlist/news", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []


async def test_watchlist_news_failure_returns_empty(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    from unittest.mock import AsyncMock, patch

    with mock_market_data_valid():
        await client.post("/watchlist", json={"ticker": "AAPL"}, headers=headers)

    with patch(
        "app.services.market_data._finnhub_get",
        new=AsyncMock(side_effect=Exception("429 Too Many Requests")),
    ):
        resp = await client.get("/watchlist/news", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []


async def test_suggestions_empty_watchlist(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    resp = await client.get("/watchlist/suggestions", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []


async def test_suggestions_returns_peers_excluding_existing(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    from unittest.mock import AsyncMock, patch

    with mock_market_data_valid():
        await client.post("/watchlist", json={"ticker": "AAPL"}, headers=headers)
        await client.post("/watchlist", json={"ticker": "MSFT"}, headers=headers)

    # AAPL sugere MSFT (já na watchlist, deve ser excluído) e GOOGL;
    # MSFT sugere AAPL (já na watchlist) e GOOGL (repetido, deve ser dedup).
    with patch(
        "app.services.market_data._finnhub_get",
        new=AsyncMock(return_value=["MSFT", "GOOGL"]),
    ):
        resp = await client.get("/watchlist/suggestions", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    tickers = [s["ticker"] for s in body]
    assert "MSFT" not in tickers
    assert "AAPL" not in tickers
    assert tickers.count("GOOGL") == 1
    assert body[0]["based_on"] in ("AAPL", "MSFT")


async def test_suggestions_failure_returns_empty(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    from unittest.mock import AsyncMock, patch

    with mock_market_data_valid():
        await client.post("/watchlist", json={"ticker": "AAPL"}, headers=headers)

    with patch(
        "app.services.market_data._finnhub_get",
        new=AsyncMock(side_effect=Exception("429 Too Many Requests")),
    ):
        resp = await client.get("/watchlist/suggestions", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []


async def test_suggestions_isolated_between_users(client, user_a, user_b):
    headers_a = await login(client, "a@test.dev", "password-a")
    headers_b = await login(client, "b@test.dev", "password-b")
    from unittest.mock import AsyncMock, patch

    with mock_market_data_valid():
        await client.post("/watchlist", json={"ticker": "AAPL"}, headers=headers_a)

    with patch(
        "app.services.market_data._finnhub_get",
        new=AsyncMock(return_value=["GOOGL"]),
    ):
        resp = await client.get("/watchlist/suggestions", headers=headers_b)
    assert resp.status_code == 200
    assert resp.json() == []  # user_b não tem watchlist, sem peers a agregar


async def test_reorder(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    with mock_market_data_valid():
        r1 = await client.post("/watchlist", json={"ticker": "AAPL"}, headers=headers)
        r2 = await client.post("/watchlist", json={"ticker": "MSFT"}, headers=headers)
    id1, id2 = r1.json()["id"], r2.json()["id"]

    # Ordem inicial: ordem de inserção (AAPL, depois MSFT) — novos itens são
    # sempre acrescentados ao fim (display_order = max+1).
    resp = await client.get("/watchlist", headers=headers)
    assert [i["stock"]["ticker"] for i in resp.json()] == ["AAPL", "MSFT"]

    resp = await client.put("/watchlist/reorder", json={"ordered_ids": [id2, id1]}, headers=headers)
    assert resp.status_code == 204

    resp = await client.get("/watchlist", headers=headers)
    assert [i["stock"]["ticker"] for i in resp.json()] == ["MSFT", "AAPL"]


async def test_reorder_ignores_other_users_ids(client, user_a, user_b):
    headers_a = await login(client, "a@test.dev", "password-a")
    headers_b = await login(client, "b@test.dev", "password-b")
    with mock_market_data_valid():
        r1 = await client.post("/watchlist", json={"ticker": "AAPL"}, headers=headers_a)
        r2 = await client.post("/watchlist", json={"ticker": "MSFT"}, headers=headers_b)

    resp = await client.put(
        "/watchlist/reorder", json={"ordered_ids": [r2.json()["id"], r1.json()["id"]]}, headers=headers_a
    )
    assert resp.status_code == 204

    resp = await client.get("/watchlist", headers=headers_a)
    assert len(resp.json()) == 1
    assert resp.json()[0]["stock"]["ticker"] == "AAPL"


async def test_add_to_watchlist_runs_active_strategies_immediately(client, db_session, user_a, seeded_stock):
    """Ao adicionar uma acao, corre logo as estrategias ativas do utilizador —
    sem isto a acao ficava com Buy 0/Sell 0 sem contexto ate se ir ao Feed."""
    from decimal import Decimal

    from app.models import StrategyItem, StrategyTemplate

    template = StrategyTemplate(user_id=user_a.id, name="Value simples")
    db_session.add(template)
    await db_session.flush()
    db_session.add(StrategyItem(
        template_id=template.id, name="RSI sobrecomprado", metric="RSI_14",
        operator=">", threshold_value=Decimal("70"), weight=Decimal("1"),
        direction="sell_signal",
    ))
    await db_session.commit()

    headers = await login(client, "a@test.dev", "password-a")
    resp = await client.post("/watchlist", json={"ticker": "AAPL"}, headers=headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["latest_evaluation"] is not None
    # seeded_stock tem precos sempre a subir -> RSI alto -> sinal de venda dispara.
    assert float(body["latest_evaluation"]["sell_score"]) == 100.0

    resp = await client.get(f"/evaluations?stock_id={body['stock']['id']}", headers=headers)
    assert len(resp.json()) == 1


async def test_add_to_watchlist_survives_evaluation_failure(client, db_session, user_a):
    """Se a avaliacao automatica falhar (ex: Finnhub em baixo), o add a
    watchlist nao deve rebentar — a acao fica so sem latest_evaluation."""
    from unittest.mock import AsyncMock, patch

    from app.models import StrategyTemplate

    template = StrategyTemplate(user_id=user_a.id, name="Value simples")
    db_session.add(template)
    await db_session.commit()

    headers = await login(client, "a@test.dev", "password-a")
    with mock_market_data_valid():
        with patch("app.services.agent.evaluate", new=AsyncMock(side_effect=Exception("boom"))):
            resp = await client.post("/watchlist", json={"ticker": "AAPL"}, headers=headers)
    assert resp.status_code == 201
    assert resp.json()["latest_evaluation"] is None


async def test_watchlist_item_detail(client, db_session, user_a, seeded_stock):
    headers = await login(client, "a@test.dev", "password-a")
    with mock_market_data_valid():
        resp = await client.post("/watchlist", json={"ticker": "AAPL"}, headers=headers)
    item_id = resp.json()["id"]

    resp = await client.get(f"/watchlist/{item_id}/detail", headers=headers)
    assert resp.status_code == 200
    body = resp.json()

    assert body["stock"]["ticker"] == "AAPL"
    assert len(body["price_history"]) > 0
    assert body["last_price"] is not None
    # seeded_stock só tem 60 dias de histórico - sem os 200 necessários, a
    # SMA_200 fica None em todos os pontos (mas o campo existe).
    assert "sma_200" in body["price_history"][0]
    assert all(p["sma_200"] is None for p in body["price_history"])

    keys = {i["key"] for i in body["indicators"]}
    assert {"RSI_14", "PE_RATIO", "EPS", "DEBT_TO_EQUITY", "MARKET_CAP"} <= keys
    rsi = next(i for i in body["indicators"] if i["key"] == "RSI_14")
    assert rsi["description"]  # tem explicação

    assert body["fundamentals"] is not None
    assert float(body["fundamentals"]["pe_ratio"]) == 12.0

    assert body["latest_evaluation"] is None  # nenhuma estrategia ativa nesta suite
    assert body["criteria"] == []

    # síntese: seeded_stock só define pe_ratio (12.0, favorável) nos
    # fundamentais - crescimento/rendibilidade ficam sem dados (None), não
    # desfavoráveis. RSI fica sobrecomprado (uptrend sintético constante) mas
    # o preço está bem acima da SMA_50, por isso momentum sai "misto".
    synthesis = body["synthesis"]
    assert synthesis["score"] is not None
    by_category = {c["category"]: c for c in synthesis["categories"]}
    assert by_category["valuation"]["classification"] == "favoravel"
    assert by_category["momentum"]["classification"] == "misto"
    assert by_category["growth"]["classification"] is None
    assert by_category["profitability"]["classification"] is None


async def test_watchlist_item_detail_not_found_for_other_user(client, db_session, user_a, user_b, seeded_stock):
    headers_a = await login(client, "a@test.dev", "password-a")
    with mock_market_data_valid():
        resp = await client.post("/watchlist", json={"ticker": "AAPL"}, headers=headers_a)
    item_id = resp.json()["id"]

    headers_b = await login(client, "b@test.dev", "password-b")
    resp = await client.get(f"/watchlist/{item_id}/detail", headers=headers_b)
    assert resp.status_code == 404


async def test_user_isolation(client, user_a, user_b):
    """Utilizador B não vê nem apaga itens do utilizador A."""
    headers_a = await login(client, "a@test.dev", "password-a")
    headers_b = await login(client, "b@test.dev", "password-b")
    with mock_market_data_valid():
        resp = await client.post("/watchlist", json={"ticker": "AAPL"}, headers=headers_a)
    item_id = resp.json()["id"]

    resp = await client.get("/watchlist", headers=headers_b)
    assert resp.json() == []

    resp = await client.delete(f"/watchlist/{item_id}", headers=headers_b)
    assert resp.status_code == 404  # 404, não 403 — não revela existência
