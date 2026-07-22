from decimal import Decimal

from tests.conftest import login

from app.models import StrategyItem, StrategyTemplate, WatchlistItem


async def _setup(db_session, user, stock):
    """Estratégia 'Value simples' do SPEC + stock na watchlist."""
    template = StrategyTemplate(user_id=user.id, name="Value simples")
    db_session.add(template)
    await db_session.flush()
    db_session.add_all([
        StrategyItem(template_id=template.id, name="RSI sobrevendido", metric="RSI_14",
                     operator="<", threshold_value=Decimal("30"), weight=Decimal("2"),
                     direction="buy_signal"),
        StrategyItem(template_id=template.id, name="P/E barato", metric="PE_RATIO",
                     operator="<", threshold_value=Decimal("15"), weight=Decimal("1"),
                     direction="buy_signal"),
        StrategyItem(template_id=template.id, name="RSI sobrecomprado", metric="RSI_14",
                     operator=">", threshold_value=Decimal("70"), weight=Decimal("1"),
                     direction="sell_signal"),
    ])
    db_session.add(WatchlistItem(user_id=user.id, stock_id=stock.id))
    await db_session.commit()
    return template


async def test_run_evaluation_on_watchlist(client, db_session, user_a, seeded_stock):
    """Precos sinteticos sempre a subir -> RSI=100 -> sinal de venda dispara.
    PE=12 passa; RSI<30 falha. buy=1/3=33.33, sell=100 -> SELL."""
    template = await _setup(db_session, user_a, seeded_stock)
    headers = await login(client, "a@test.dev", "password-a")

    resp = await client.post("/evaluations/run", json={"template_id": str(template.id)},
                             headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    ev = body[0]
    assert float(ev["sell_score"]) == 100.0
    assert round(float(ev["buy_score"]), 2) == 33.33
    assert ev["recommendation"] == "SELL"
    assert len(ev["details"]) == 3
    assert ev["price_at_evaluation"] is not None

    resp = await client.get("/evaluations/latest", headers=headers)
    assert len(resp.json()) == 1

    resp = await client.get(f"/evaluations?stock_id={seeded_stock.id}", headers=headers)
    assert len(resp.json()) == 1


async def test_latest_evaluations_filters_by_template(client, db_session, user_a, seeded_stock):
    """Bug real: sem template_id, /evaluations/latest devolvia a avaliação
    mais recente entre TODAS as estratégias por ação, sem indicar qual -
    não correspondia ao que o utilizador tinha selecionado no Feed. Duas
    estratégias diferentes sobre a mesma ação devem dar recomendações
    distintas e recuperáveis em separado."""
    template_sell = await _setup(db_session, user_a, seeded_stock)  # Value simples -> SELL

    template_buy = StrategyTemplate(user_id=user_a.id, name="Sempre compra")
    db_session.add(template_buy)
    await db_session.flush()
    db_session.add(StrategyItem(
        template_id=template_buy.id, name="RSI qualquer", metric="RSI_14",
        operator=">", threshold_value=Decimal("0"), weight=Decimal("1"),
        direction="buy_signal",
    ))
    await db_session.commit()

    headers = await login(client, "a@test.dev", "password-a")
    await client.post("/evaluations/run", json={"template_id": str(template_sell.id)}, headers=headers)
    await client.post("/evaluations/run", json={"template_id": str(template_buy.id)}, headers=headers)

    resp_sell = await client.get(f"/evaluations/latest?template_id={template_sell.id}", headers=headers)
    assert resp_sell.status_code == 200
    body_sell = resp_sell.json()
    assert len(body_sell) == 1
    assert body_sell[0]["strategy_template_id"] == str(template_sell.id)
    assert body_sell[0]["recommendation"] == "SELL"

    resp_buy = await client.get(f"/evaluations/latest?template_id={template_buy.id}", headers=headers)
    assert resp_buy.status_code == 200
    body_buy = resp_buy.json()
    assert len(body_buy) == 1
    assert body_buy[0]["strategy_template_id"] == str(template_buy.id)
    assert body_buy[0]["recommendation"] == "BUY"


async def test_run_with_foreign_template(client, db_session, user_a, user_b, seeded_stock):
    template = await _setup(db_session, user_a, seeded_stock)
    headers_b = await login(client, "b@test.dev", "password-b")
    resp = await client.post("/evaluations/run", json={"template_id": str(template.id)},
                             headers=headers_b)
    assert resp.status_code == 404


async def test_latest_by_strategy_groups_and_excludes_hold(client, db_session, user_a, seeded_stock):
    """Agrupa por estrategia ativa; HOLD fica de fora dos sinais; estrategia
    inativa nao aparece nada (nem o grupo)."""
    template = await _setup(db_session, user_a, seeded_stock)  # Value simples -> SELL

    hold_template = StrategyTemplate(user_id=user_a.id, name="Nunca dispara", horizon="long_term")
    db_session.add(hold_template)
    await db_session.flush()
    db_session.add(StrategyItem(
        template_id=hold_template.id, name="Impossivel", metric="PE_RATIO",
        operator=">", threshold_value=Decimal("1000"), weight=Decimal("1"),
        direction="buy_signal",
    ))
    inactive_template = StrategyTemplate(user_id=user_a.id, name="Inativa", is_active=False)
    db_session.add(inactive_template)
    await db_session.commit()

    headers = await login(client, "a@test.dev", "password-a")
    await client.post("/evaluations/run", json={"template_id": str(template.id)}, headers=headers)
    await client.post("/evaluations/run", json={"template_id": str(hold_template.id)}, headers=headers)

    resp = await client.get("/evaluations/latest-by-strategy", headers=headers)
    assert resp.status_code == 200
    body = resp.json()

    names = {g["strategy_name"] for g in body}
    assert names == {"Value simples", "Nunca dispara"}  # "Inativa" fica de fora

    value_group = next(g for g in body if g["strategy_name"] == "Value simples")
    assert len(value_group["signals"]) == 1
    assert value_group["signals"][0]["recommendation"] == "SELL"
    assert value_group["horizon"] is None

    hold_group = next(g for g in body if g["strategy_name"] == "Nunca dispara")
    assert hold_group["signals"] == []
    assert hold_group["horizon"] == "long_term"
