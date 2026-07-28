"""Testes de app/services/reports.py - resumo periódico enviado no dia/hora
escolhidos por cada utilizador (ver GET/PUT /notifications/preferences)."""
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

from tests.conftest import mock_market_data_valid

from app.models import StrategyItem, StrategyTemplate, WatchlistItem
from app.services import reports
from decimal import Decimal

# Sábado (mesmo valor que o antigo cron fixo), 08:00 UTC - qualquer data serve,
# só o weekday()/hour importam.
FIXED_NOW = datetime(2026, 8, 1, 8, 0, tzinfo=timezone.utc)
assert FIXED_NOW.weekday() == 5  # confirma a data escolhida é mesmo um sábado


async def _add_active_template(db_session, user, stock):
    template = StrategyTemplate(user_id=user.id, name="Value simples")
    db_session.add(template)
    await db_session.flush()
    db_session.add(StrategyItem(
        template_id=template.id, name="RSI sobrecomprado", metric="RSI_14",
        operator=">", threshold_value=Decimal("70"), weight=Decimal("1"),
        direction="sell_signal",
    ))
    db_session.add(WatchlistItem(user_id=user.id, stock_id=stock.id))
    await db_session.commit()
    return template


async def test_report_sent_when_day_and_hour_match(db_session, user_a, seeded_stock):
    await _add_active_template(db_session, user_a, seeded_stock)
    user_a.report_day_of_week = FIXED_NOW.weekday()
    user_a.report_hour = FIXED_NOW.hour
    await db_session.commit()

    with mock_market_data_valid(), patch("app.services.reports.email_service.send_summary", new=Mock()) as mocked:
        rows = await reports.generate_and_send_reports(db_session, now=FIXED_NOW)

    assert len(rows) == 1
    assert rows[0]["ticker"] == seeded_stock.ticker
    mocked.assert_called_once()
    await db_session.refresh(user_a)
    # SQLite (aiosqlite) devolve o datetime sem tzinfo - o valor gravado era UTC.
    assert user_a.last_report_sent_at.replace(tzinfo=timezone.utc) == FIXED_NOW


async def test_report_skipped_when_hour_does_not_match(db_session, user_a, seeded_stock):
    await _add_active_template(db_session, user_a, seeded_stock)
    user_a.report_day_of_week = FIXED_NOW.weekday()
    user_a.report_hour = (FIXED_NOW.hour + 1) % 24
    await db_session.commit()

    with patch("app.services.reports.email_service.send_summary", new=Mock()) as mocked:
        rows = await reports.generate_and_send_reports(db_session, now=FIXED_NOW)

    assert rows == []
    mocked.assert_not_called()
    await db_session.refresh(user_a)
    assert user_a.last_report_sent_at is None


async def test_report_skipped_when_day_does_not_match(db_session, user_a, seeded_stock):
    await _add_active_template(db_session, user_a, seeded_stock)
    user_a.report_day_of_week = (FIXED_NOW.weekday() + 1) % 7
    user_a.report_hour = FIXED_NOW.hour
    await db_session.commit()

    with patch("app.services.reports.email_service.send_summary", new=Mock()) as mocked:
        rows = await reports.generate_and_send_reports(db_session, now=FIXED_NOW)

    assert rows == []
    mocked.assert_not_called()


async def test_report_skipped_when_email_reports_disabled(db_session, user_a, seeded_stock):
    await _add_active_template(db_session, user_a, seeded_stock)
    user_a.report_day_of_week = FIXED_NOW.weekday()
    user_a.report_hour = FIXED_NOW.hour
    user_a.email_reports_enabled = False
    await db_session.commit()

    with patch("app.services.reports.email_service.send_summary", new=Mock()) as mocked:
        rows = await reports.generate_and_send_reports(db_session, now=FIXED_NOW)

    assert rows == []
    mocked.assert_not_called()


async def test_report_not_resent_within_min_interval(db_session, user_a, seeded_stock):
    await _add_active_template(db_session, user_a, seeded_stock)
    user_a.report_day_of_week = FIXED_NOW.weekday()
    user_a.report_hour = FIXED_NOW.hour
    user_a.last_report_sent_at = FIXED_NOW - timedelta(days=1)  # enviado ontem
    await db_session.commit()

    with patch("app.services.reports.email_service.send_summary", new=Mock()) as mocked:
        rows = await reports.generate_and_send_reports(db_session, now=FIXED_NOW)

    assert rows == []
    mocked.assert_not_called()


async def test_report_resent_after_min_interval_passes(db_session, user_a, seeded_stock):
    await _add_active_template(db_session, user_a, seeded_stock)
    user_a.report_day_of_week = FIXED_NOW.weekday()
    user_a.report_hour = FIXED_NOW.hour
    user_a.last_report_sent_at = FIXED_NOW - timedelta(days=7)  # há mais de uma semana
    await db_session.commit()

    with mock_market_data_valid(), patch("app.services.reports.email_service.send_summary", new=Mock()) as mocked:
        rows = await reports.generate_and_send_reports(db_session, now=FIXED_NOW)

    assert len(rows) == 1
    mocked.assert_called_once()


async def test_report_isolated_between_users(db_session, user_a, user_b, seeded_stock):
    await _add_active_template(db_session, user_a, seeded_stock)
    await _add_active_template(db_session, user_b, seeded_stock)
    user_a.report_day_of_week = FIXED_NOW.weekday()
    user_a.report_hour = FIXED_NOW.hour
    user_b.report_day_of_week = (FIXED_NOW.weekday() + 1) % 7  # dia diferente
    user_b.report_hour = FIXED_NOW.hour
    await db_session.commit()

    with mock_market_data_valid(), patch("app.services.reports.email_service.send_summary", new=Mock()) as mocked:
        rows = await reports.generate_and_send_reports(db_session, now=FIXED_NOW)

    assert len(rows) == 1  # só o user_a calha nesta hora
    mocked.assert_called_once()
    call_args = mocked.call_args[0]
    assert call_args[0] == user_a.email
