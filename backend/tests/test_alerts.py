"""Testes de app/services/alerts.py - deteção de alertas de preço-alvo e
mudança de sinal (edge-triggered, ver docstring do módulo)."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import Mock, patch

from sqlalchemy import select

from tests.conftest import mock_market_data_valid

from app.models import Evaluation, Notification, PriceSnapshot, StrategyItem, StrategyTemplate, WatchlistItem
from app.services import alerts


async def _add_watchlist_item(db_session, user, stock, **kwargs):
    item = WatchlistItem(user_id=user.id, stock_id=stock.id, **kwargs)
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)
    return item


async def test_price_buy_alert_triggers_when_price_at_or_below_target(db_session, user_a, seeded_stock):
    # seeded_stock: último fecho = 180.0 (ver conftest.py::seeded_stock)
    item = await _add_watchlist_item(db_session, user_a, seeded_stock, target_buy_price=Decimal("181"))

    with mock_market_data_valid():
        created = await alerts.check_alerts(db_session, user_id=user_a.id)

    assert len(created) == 1
    assert created[0].kind == "price_buy"
    await db_session.refresh(item)
    assert item.buy_alert_triggered is True


async def test_price_buy_alert_does_not_repeat_while_still_triggered(db_session, user_a, seeded_stock):
    await _add_watchlist_item(db_session, user_a, seeded_stock, target_buy_price=Decimal("181"))

    with mock_market_data_valid():
        await alerts.check_alerts(db_session, user_id=user_a.id)
        created_again = await alerts.check_alerts(db_session, user_id=user_a.id)

    assert created_again == []


async def test_price_buy_alert_resets_and_refires_after_moving_away(db_session, user_a, seeded_stock):
    item = await _add_watchlist_item(db_session, user_a, seeded_stock, target_buy_price=Decimal("181"))
    today = datetime.now(timezone.utc).date()

    with mock_market_data_valid():
        first = await alerts.check_alerts(db_session, user_id=user_a.id)
        assert len(first) == 1

        # preço sobe para bem acima do alvo -> reset do "já disparado"
        db_session.add(PriceSnapshot(stock_id=seeded_stock.id, date=today, close=Decimal("200")))
        await db_session.commit()
        second = await alerts.check_alerts(db_session, user_id=user_a.id)
        assert second == []
        await db_session.refresh(item)
        assert item.buy_alert_triggered is False

        # volta a cair para o alvo -> dispara outra vez
        db_session.add(PriceSnapshot(stock_id=seeded_stock.id, date=today + timedelta(days=1), close=Decimal("178")))
        await db_session.commit()
        third = await alerts.check_alerts(db_session, user_id=user_a.id)
        assert len(third) == 1
        assert third[0].kind == "price_buy"


async def test_price_sell_alert_triggers_when_price_at_or_above_target(db_session, user_a, seeded_stock):
    await _add_watchlist_item(db_session, user_a, seeded_stock, target_sell_price=Decimal("175"))

    with mock_market_data_valid():
        created = await alerts.check_alerts(db_session, user_id=user_a.id)

    assert len(created) == 1
    assert created[0].kind == "price_sell"


async def test_no_price_alert_without_target_price(db_session, user_a, seeded_stock):
    await _add_watchlist_item(db_session, user_a, seeded_stock)

    with mock_market_data_valid():
        created = await alerts.check_alerts(db_session, user_id=user_a.id)

    assert created == []


async def test_signal_alert_fires_on_recommendation_change(db_session, user_a, seeded_stock):
    """RSI sempre alto no seeded_stock -> a estrategia dispara SELL. Insere-se
    manualmente uma avaliacao anterior com HOLD para simular a transicao -
    e' essa mudanca (HOLD -> SELL) que deve gerar o alerta."""
    template = StrategyTemplate(user_id=user_a.id, name="Sobrecomprado")
    db_session.add(template)
    await db_session.flush()
    db_session.add(StrategyItem(
        template_id=template.id, name="RSI sobrecomprado", metric="RSI_14",
        operator=">", threshold_value=Decimal("70"), weight=Decimal("1"),
        direction="sell_signal",
    ))
    db_session.add(Evaluation(
        user_id=user_a.id, stock_id=seeded_stock.id, strategy_template_id=template.id,
        recommendation="HOLD", buy_score=Decimal("0"), sell_score=Decimal("0"),
    ))
    item = await _add_watchlist_item(db_session, user_a, seeded_stock, alert_on_signal=True)

    with mock_market_data_valid():
        created = await alerts.check_alerts(db_session, user_id=user_a.id)

    signal_alerts = [n for n in created if n.kind in ("signal_buy", "signal_sell")]
    assert len(signal_alerts) == 1
    assert signal_alerts[0].kind == "signal_sell"
    assert seeded_stock.ticker in signal_alerts[0].message
    assert item.alert_on_signal is True


async def test_no_signal_alert_when_opted_out(db_session, user_a, seeded_stock):
    template = StrategyTemplate(user_id=user_a.id, name="Sobrecomprado")
    db_session.add(template)
    await db_session.flush()
    db_session.add(StrategyItem(
        template_id=template.id, name="RSI sobrecomprado", metric="RSI_14",
        operator=">", threshold_value=Decimal("70"), weight=Decimal("1"),
        direction="sell_signal",
    ))
    db_session.add(Evaluation(
        user_id=user_a.id, stock_id=seeded_stock.id, strategy_template_id=template.id,
        recommendation="HOLD", buy_score=Decimal("0"), sell_score=Decimal("0"),
    ))
    await _add_watchlist_item(db_session, user_a, seeded_stock, alert_on_signal=False)

    with mock_market_data_valid():
        created = await alerts.check_alerts(db_session, user_id=user_a.id)

    assert created == []
    # não avaliou de todo - só a avaliação HOLD inserida manualmente existe
    evaluations = (await db_session.execute(select(Evaluation))).scalars().all()
    assert len(evaluations) == 1


async def test_alert_sends_email_when_enabled(db_session, user_a, seeded_stock):
    await _add_watchlist_item(db_session, user_a, seeded_stock, target_buy_price=Decimal("181"))

    with mock_market_data_valid(), patch(
        "app.services.notifications.email_service.send_notification_email", new=Mock()
    ) as mocked:
        await alerts.check_alerts(db_session, user_id=user_a.id)

    mocked.assert_called_once()


async def test_alert_skips_email_when_disabled(db_session, user_a, seeded_stock):
    user_a.email_alerts_enabled = False
    await db_session.commit()
    await _add_watchlist_item(db_session, user_a, seeded_stock, target_buy_price=Decimal("181"))

    with mock_market_data_valid(), patch(
        "app.services.notifications.email_service.send_notification_email", new=Mock()
    ) as mocked:
        created = await alerts.check_alerts(db_session, user_id=user_a.id)

    assert len(created) == 1  # notificação in-app continua a ser criada
    mocked.assert_not_called()
