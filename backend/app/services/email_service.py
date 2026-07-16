"""Email resumo semanal via SMTP. Se SMTP nao configurado, faz log e nao falha."""
import logging
import smtplib
from email.mime.text import MIMEText

from app.config import settings

logger = logging.getLogger(__name__)


def build_summary_html(rows: list[dict]) -> str:
    """rows: [{ticker, buy_score, sell_score, recommendation, price, checklist_name}]"""
    by_checklist: dict[str, list[dict]] = {}
    for r in rows:
        by_checklist.setdefault(r["checklist_name"], []).append(r)
    parts = ["<h2>Benjamin — Resumo semanal</h2>"]
    for name, group in by_checklist.items():
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


def send_summary(rows: list[dict]) -> bool:
    if not rows:
        logger.info("Resumo semanal: watchlist vazia, email não enviado.")
        return False
    if not settings.smtp_host or not settings.summary_email_to:
        logger.warning("SMTP não configurado — resumo semanal não enviado.")
        return False
    msg = MIMEText(build_summary_html(rows), "html", "utf-8")
    msg["Subject"] = "Benjamin — Resumo semanal da watchlist"
    msg["From"] = settings.smtp_user
    msg["To"] = settings.summary_email_to
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.starttls()
        server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(msg)
    logger.info("Resumo semanal enviado para %s", settings.summary_email_to)
    return True
