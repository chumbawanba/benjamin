from tests.conftest import login

from app.models import WatchlistItem

ITEM = {"name": "RSI sobrevendido", "metric": "RSI_14", "operator": "<",
        "threshold_value": 30, "weight": 2, "direction": "buy_signal"}


async def test_crud_strategy_and_items(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    resp = await client.post("/strategies", json={"name": "Value simples"}, headers=headers)
    assert resp.status_code == 201
    template_id = resp.json()["id"]

    resp = await client.post(f"/strategies/{template_id}/items", json=ITEM, headers=headers)
    assert resp.status_code == 201

    resp = await client.get("/strategies", headers=headers)
    assert len(resp.json()) == 1
    assert len(resp.json()[0]["items"]) == 1


async def test_invalid_metric_rejected(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    resp = await client.post("/strategies", json={"name": "T"}, headers=headers)
    template_id = resp.json()["id"]
    bad = dict(ITEM, metric="INVENTADO_99")
    resp = await client.post(f"/strategies/{template_id}/items", json=bad, headers=headers)
    assert resp.status_code == 422


async def test_metrics_endpoint(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    resp = await client.get("/strategies/metrics", headers=headers)
    keys = {m["key"] for m in resp.json()}
    assert "RSI_14" in keys and "PE_RATIO" in keys


async def test_create_strategy_with_horizon(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    resp = await client.post(
        "/strategies", json={"name": "Swing trade", "horizon": "short_term"}, headers=headers
    )
    assert resp.status_code == 201
    assert resp.json()["horizon"] == "short_term"


async def test_invalid_horizon_rejected(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    resp = await client.post(
        "/strategies", json={"name": "T", "horizon": "medio_prazo"}, headers=headers
    )
    assert resp.status_code == 422


async def test_strategy_isolation(client, user_a, user_b):
    headers_a = await login(client, "a@test.dev", "password-a")
    headers_b = await login(client, "b@test.dev", "password-b")
    resp = await client.post("/strategies", json={"name": "Privada"}, headers=headers_a)
    template_id = resp.json()["id"]
    resp = await client.put(f"/strategies/{template_id}", json={"name": "Hack"}, headers=headers_b)
    assert resp.status_code == 404


async def test_delete_item_after_evaluation_does_not_error(client, db_session, user_a, seeded_stock):
    """Bug real reproduzido ao vivo: apagar um StrategyItem já avaliado pelo
    menos uma vez falhava com IntegrityError (evaluation_details.strategy_item_id
    sem ON DELETE CASCADE) — no ambiente do utilizador isto não aparecia como
    um 500 normal, o browser via como "Failed to fetch". Ativa o enforcement
    de FKs no SQLite de teste (desligado por omissão) para apanhar a
    regressão aqui também, não só em Postgres."""
    from sqlalchemy import text

    await db_session.execute(text("PRAGMA foreign_keys=ON"))
    db_session.add(WatchlistItem(user_id=user_a.id, stock_id=seeded_stock.id))
    await db_session.commit()

    headers = await login(client, "a@test.dev", "password-a")
    resp = await client.post("/strategies", json={"name": "T"}, headers=headers)
    template_id = resp.json()["id"]
    resp = await client.post(f"/strategies/{template_id}/items", json=ITEM, headers=headers)
    item_id = resp.json()["id"]

    resp = await client.post("/evaluations/run", json={"template_id": template_id}, headers=headers)
    assert resp.status_code == 200

    resp = await client.delete(f"/strategies/items/{item_id}", headers=headers)
    assert resp.status_code == 204


async def test_delete_template_after_evaluation_does_not_error(client, db_session, user_a, seeded_stock):
    """Mesmo bug, desta vez ao apagar a estratégia inteira
    (evaluations.strategy_template_id também sem cascade)."""
    from sqlalchemy import text

    await db_session.execute(text("PRAGMA foreign_keys=ON"))
    db_session.add(WatchlistItem(user_id=user_a.id, stock_id=seeded_stock.id))
    await db_session.commit()

    headers = await login(client, "a@test.dev", "password-a")
    resp = await client.post("/strategies", json={"name": "T"}, headers=headers)
    template_id = resp.json()["id"]
    await client.post(f"/strategies/{template_id}/items", json=ITEM, headers=headers)
    resp = await client.post("/evaluations/run", json={"template_id": template_id}, headers=headers)
    assert resp.status_code == 200

    resp = await client.delete(f"/strategies/{template_id}", headers=headers)
    assert resp.status_code == 204


async def test_optimize_requires_watchlist(client, user_a):
    headers = await login(client, "a@test.dev", "password-a")
    resp = await client.post("/strategies", json={"name": "T"}, headers=headers)
    template_id = resp.json()["id"]
    resp = await client.post(f"/strategies/{template_id}/optimize", headers=headers)
    assert resp.status_code == 400


async def test_optimize_returns_proposal(client, db_session, user_a, seeded_stock):
    """seeded_stock tem 60 dias de precos sinteticos sempre a subir -> buy&hold
    positivo; o otimizador nunca deve escolher um conjunto pior que o
    baseline vazio (retorno 0), logo backtest_return_pct >= 0."""
    db_session.add(WatchlistItem(user_id=user_a.id, stock_id=seeded_stock.id))
    await db_session.commit()

    headers = await login(client, "a@test.dev", "password-a")
    resp = await client.post("/strategies", json={"name": "T"}, headers=headers)
    template_id = resp.json()["id"]

    resp = await client.post(f"/strategies/{template_id}/optimize", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["stocks_evaluated"] == 1
    assert len(body["items"]) <= 6
    assert float(body["backtest_return_pct"]) >= 0.0
    assert float(body["buy_and_hold_return_pct"]) > 0.0
    for item in body["items"]:
        assert item["metric"] in {"RSI_14", "PE_RATIO", "DEBT_TO_EQUITY", "DIVIDEND_YIELD", "EPS", "MARKET_CAP"}


async def test_optimize_insufficient_history(client, db_session, user_a):
    from datetime import datetime, timedelta, timezone
    from decimal import Decimal

    from app.models import PriceSnapshot, Stock

    stock = Stock(ticker="NEW", name="Novata", currency="USD")
    db_session.add(stock)
    await db_session.flush()
    today = datetime.now(timezone.utc).date()
    for i in range(5, 0, -1):
        db_session.add(PriceSnapshot(
            stock_id=stock.id, date=today - timedelta(days=i), close=Decimal("10.0"),
        ))
    db_session.add(WatchlistItem(user_id=user_a.id, stock_id=stock.id))
    await db_session.commit()

    headers = await login(client, "a@test.dev", "password-a")
    resp = await client.post("/strategies", json={"name": "T"}, headers=headers)
    template_id = resp.json()["id"]
    resp = await client.post(f"/strategies/{template_id}/optimize", headers=headers)
    assert resp.status_code == 400
