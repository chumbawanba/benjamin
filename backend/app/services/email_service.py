"""Emails via SMTP: resumo periódico da watchlist + alertas de preço/sinal.
Se SMTP nao configurado, faz log e nao falha (nunca bloqueia o job)."""
import logging
import smtplib
from email.mime.text import MIMEText

from app.config import settings

logger = logging.getLogger(__name__)


def _unsubscribe_footer(unsubscribe_token: str) -> str:
    # Link sem login (obrigatório em qualquer email periódico/tipo-alerta) -
    # ver app/routers/notifications.py::unsubscribe.
    url = f"{settings.app_base_url}/unsubscribe/{unsubscribe_token}"
    return f'<p style="font-size:12px;color:#888">Não queres receber estes emails? ' \
           f'<a href="{url}">Cancelar subscrição</a>.</p>'


def _send(to_email: str, subject: str, html_body: str) -> bool:
    if not settings.smtp_host:
        logger.warning("SMTP não configurado — email '%s' não enviado para %s.", subject, to_email)
        return False
    msg = MIMEText(html_body, "html", "utf-8")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_user
    msg["To"] = to_email
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.starttls()
        server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(msg)
    logger.info("Email '%s' enviado para %s", subject, to_email)
    return True


def build_summary_html(rows: list[dict]) -> str:
    """rows: [{ticker, buy_score, sell_score, recommendation, price, strategy_name}]"""
    by_strategy: dict[str, list[dict]] = {}
    for r in rows:
        by_strategy.setdefault(r["strategy_name"], []).append(r)
    parts = ["<h2>Benjamin — Resumo da tua watchlist</h2>"]
    for name, group in by_strategy.items():
        parts.append(f"<h3>{name}</h3>")
        parts.append("<table border='1' cellpadding='6' cellspacing='0'>")
        parts.append("<tr><th>Ticker</th><th>Buy</th><th>Sell</th><th>Recomendação</th><th>Preço</th></tr>")
        for r in sorted(group, key=lambda x: -x["buy_score"]):
            parts.append(
                f"<tr><td>{r['ticker']}</td><td>{r['buy_score']:.0f}</td>"
                f"<td>{r['sell_score']:.0f}</td><td>{r['recommendation']}</td>"
                f"<td>{r['price'] if r['price'] is not None else '—'}</td></tr>"
            )
        parts.append("</table>")
    parts.append("<p><em>Resultados dos teus critérios — não é aconselhamento financeiro.</em></p>")
    return "".join(parts)


def send_summary(to_email: str, rows: list[dict], unsubscribe_token: str) -> bool:
    """Resumo periódico (ver scheduler.py::report_job) - um email por
    utilizador, só com as avaliações dele (antes desta função ser
    parametrizada por utilizador, ia tudo misturado para um único
    SUMMARY_EMAIL_TO fixo - bug de quando a app ainda era single-user)."""
    if not rows:
        logger.info("Resumo periódico: watchlist vazia, email não enviado para %s.", to_email)
        return False
    html = build_summary_html(rows) + _unsubscribe_footer(unsubscribe_token)
    return _send(to_email, "Benjamin — Resumo da tua watchlist", html)


def send_notification_email(to_email: str, message: str, unsubscribe_token: str) -> bool:
    """Email de alerta (preço-alvo atingido ou mudança de sinal) - ver
    app/services/alerts.py e app/services/notifications.py."""
    html = f"<p>{message}</p>" + _unsubscribe_footer(unsubscribe_token)
    return _send(to_email, "Benjamin — Alerta", html)
