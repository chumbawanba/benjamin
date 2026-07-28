"""Jobs agendados: refresh diário de dados de mercado, alertas diários de
preço/sinal, e resumo periódico (por utilizador)."""
import logging

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Stock, WatchlistItem
from app.services import alerts, market_data, reports

logger = logging.getLogger(__name__)


async def daily_refresh_job() -> int:
    """Atualiza os dados de mercado (preços + fundamentais) de todas as ações em
    alguma watchlist, para a app raramente precisar de consultar o Yahoo Finance em
    tempo real enquanto o utilizador a usa. Não avalia estratégias nem envia email —
    isso continua a ser feito pelo `report_job`. Devolve o nº de ações processadas
    (para testes)."""
    processed = 0
    async with SessionLocal() as db:
        stock_ids = (await db.execute(select(WatchlistItem.stock_id).distinct())).scalars().all()
        for stock_id in stock_ids:
            stock = (await db.execute(select(Stock).where(Stock.id == stock_id))).scalar_one_or_none()
            if stock is None:
                continue
            try:
                await market_data.ensure_fresh(db, stock)
                processed += 1
            except Exception:
                logger.exception("Falha ao atualizar dados de %s", stock.ticker)
        await db.commit()
    return processed


async def alerts_job() -> int:
    """Deteta alertas de preço-alvo atingido e mudança de sinal (ver
    app/services/alerts.py), independente do report_job - corre diariamente
    para os alertas serem atempados. Devolve o nº de notificações criadas
    (para testes)."""
    async with SessionLocal() as db:
        created = await alerts.check_alerts(db)
    return len(created)


async def report_job() -> list[dict]:
    """Corre todas as horas (ver main.py) - a lógica de quem recebe o quê
    (dia/hora escolhidos, guarda anti-duplicação) vive em
    app/services/reports.py::generate_and_send_reports, para poder ser
    testada com uma hora injetada. Devolve as linhas de todos os
    utilizadores para quem o resumo foi gerado nesta corrida (para testes)."""
    async with SessionLocal() as db:
        return await reports.generate_and_send_reports(db)
