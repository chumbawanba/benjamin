from decimal import Decimal

from tests.conftest import login

from app.models import ChecklistItem, ChecklistTemplate, WatchlistItem


async def _setup(db_session, user, stock):
    """Checklist 'Value simples' do SPEC + stock na watchlist."""
    template = ChecklistTemplate(user_id=user.id, name="Value simples")
    db_session.add(template)
    await db_session.flush()
    db_session.add_all([
        ChecklistItem(template_id=template.id, name="RSI sobrevendido", metric="RSI_14",
                      operator="<", threshold_value=Decimal("30"), weight=Decimal("2"),
                      direction="buy_signal"),
        ChecklistItem(template_id=template.id, name="P/E barato", metric="PE_RATIO",
                      operator="<", threshold_value=Decimal("15"), weight=Decimal("1"),
                      direction="buy_signal"),
        ChecklistItem(template_id=template.id, name="RSI sobrecomprado", metric="RSI_14",
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
    headers = await login(client, "a@test.local", "password-a")

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


async def test_run_with_foreign_template(client, db_session, user_a, user_b, seeded_stock):
    template = await _setup(db_session, user_a, seeded_stock)
    headers_b = await login(client, "b@test.local", "password-b")
    resp = await client.post("/evaluations/run", json={"template_id": str(template.id)},
                             headers=headers_b)
    assert resp.status_code == 404
