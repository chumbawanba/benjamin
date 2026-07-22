"""Conversão de moeda para o portfolio (posições em várias moedas, ex: ações US
em USD e europeias em EUR - ver User.preferred_currency e routers/portfolio.py).

Taxas via Twelve Data /exchange_rate, com cache de 1 dia em FxRateSnapshot -
mesmo padrão de "freshness" já usado em market_data.py para preços, só que com
uma janela mais curta (câmbio interessa mais atualizado do que fundamentais)."""
import logging
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import FxRateSnapshot
from app.services import market_data

logger = logging.getLogger(__name__)

FRESHNESS_DAYS = 1


async def get_rate(db: AsyncSession, base_currency: str, quote_currency: str) -> Decimal | None:
    """Devolve quantas unidades de `quote_currency` valem 1 unidade de
    `base_currency` (ex: get_rate(db, "USD", "EUR") ~ 0.92). None só se nunca
    tiver sido possível obter a taxa (Twelve Data indisponível e sem cache)."""
    base_currency = base_currency.upper().strip()
    quote_currency = quote_currency.upper().strip()
    if base_currency == quote_currency:
        return Decimal("1")

    today = datetime.now(timezone.utc).date()
    latest = (
        await db.execute(
            select(FxRateSnapshot)
            .where(
                FxRateSnapshot.base_currency == base_currency,
                FxRateSnapshot.quote_currency == quote_currency,
            )
            .order_by(FxRateSnapshot.date.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if latest is not None and (today - latest.date).days <= FRESHNESS_DAYS:
        return latest.rate

    try:
        data = await market_data._twelvedata_get(
            "exchange_rate", {"symbol": f"{base_currency}/{quote_currency}"},
        )
        rate = Decimal(str(data["rate"]))
    except Exception:
        logger.warning(
            "Falha ao obter câmbio %s/%s via Twelve Data", base_currency, quote_currency, exc_info=True,
        )
        return latest.rate if latest is not None else None

    db.add(FxRateSnapshot(base_currency=base_currency, quote_currency=quote_currency, date=today, rate=rate))
    await db.commit()
    return rate
