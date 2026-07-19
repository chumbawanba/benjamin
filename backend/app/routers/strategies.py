import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import StrategyItem, StrategyTemplate, User, WatchlistItem
from app.schemas.common import (
    VALID_DIRECTIONS, VALID_HORIZONS, VALID_OPERATORS,
    OptimizeResultOut, StrategyItemIn, StrategyItemOut, StrategyTemplateIn, StrategyTemplateOut,
)
from app.security import get_current_user
from app.services import backtest_core, market_data
from app.services.indicators_core import INDICATORS

router = APIRouter(prefix="/strategies", tags=["strategies"])


def _validate_item(body: StrategyItemIn) -> None:
    if body.metric not in INDICATORS:
        raise HTTPException(status_code=422, detail=f"Métrica desconhecida: {body.metric}")
    if body.operator not in VALID_OPERATORS:
        raise HTTPException(status_code=422, detail=f"Operador inválido: {body.operator}")
    if body.direction not in VALID_DIRECTIONS:
        raise HTTPException(status_code=422, detail=f"Direção inválida: {body.direction}")
    if body.operator == "between" and (body.threshold_value is None or body.threshold_value_max is None):
        raise HTTPException(status_code=422, detail="'between' requer threshold_value e threshold_value_max")
    if body.operator != "between" and body.threshold_value is None:
        raise HTTPException(status_code=422, detail="threshold_value é obrigatório")


def _validate_template(body: StrategyTemplateIn) -> None:
    if body.horizon is not None and body.horizon not in VALID_HORIZONS:
        raise HTTPException(status_code=422, detail=f"Horizonte inválido: {body.horizon}")


async def _get_owned_template(
    db: AsyncSession, template_id: uuid.UUID, user_id: uuid.UUID
) -> StrategyTemplate:
    template = (
        await db.execute(
            select(StrategyTemplate).options(selectinload(StrategyTemplate.items))
            .where(StrategyTemplate.id == template_id, StrategyTemplate.user_id == user_id)
        )
    ).scalar_one_or_none()
    if template is None:
        raise HTTPException(status_code=404, detail="Não encontrado")
    return template


@router.get("/metrics")
async def list_metrics(user: User = Depends(get_current_user)):
    return [
        {
            "key": key, "kind": spec["kind"], "lookback_days": spec["lookback_days"],
            "description": spec.get("description"),
        }
        for key, spec in INDICATORS.items()
    ]


@router.get("", response_model=list[StrategyTemplateOut])
async def list_strategies(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    templates = (
        await db.execute(
            select(StrategyTemplate).options(selectinload(StrategyTemplate.items))
            .where(StrategyTemplate.user_id == user.id)
            .order_by(StrategyTemplate.created_at.desc())
        )
    ).scalars().all()
    return templates


@router.post("", response_model=StrategyTemplateOut, status_code=201)
async def create_strategy(
    body: StrategyTemplateIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    _validate_template(body)
    template = StrategyTemplate(user_id=user.id, **body.model_dump())
    db.add(template)
    await db.commit()
    return await _get_owned_template(db, template.id, user.id)


@router.put("/{template_id}", response_model=StrategyTemplateOut)
async def update_strategy(
    template_id: uuid.UUID, body: StrategyTemplateIn,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    _validate_template(body)
    template = await _get_owned_template(db, template_id, user.id)
    for key, value in body.model_dump().items():
        setattr(template, key, value)
    await db.commit()
    return await _get_owned_template(db, template_id, user.id)


@router.post("/{template_id}/optimize", response_model=OptimizeResultOut)
async def optimize_strategy(
    template_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    """Sugere um conjunto de critérios (dentro de um catálogo de indicadores
    comparáveis entre ações) que teria maximizado o retorno simulado nos
    últimos ~12 meses de histórico de preços da watchlist inteira. Não altera
    a estratégia — devolve uma proposta; o cliente decide se a aplica via os
    endpoints normais de items (POST/DELETE .../items).

    Backtest simplificado: fundamentais tratados como constantes (só existe o
    snapshot mais recente), sem custos de transação. Serve como ponto de
    partida, não como garantia de desempenho futuro."""
    await _get_owned_template(db, template_id, user.id)

    stock_rows = (
        await db.execute(
            select(WatchlistItem).options(selectinload(WatchlistItem.stock))
            .where(WatchlistItem.user_id == user.id)
        )
    ).scalars().all()
    if not stock_rows:
        raise HTTPException(status_code=400, detail="A watchlist está vazia — adiciona ações antes de otimizar.")

    series_list = []
    for item in stock_rows:
        snapshots = await market_data.get_price_history(db, item.stock_id, days=365)
        if len(snapshots) < backtest_core.MIN_HISTORY_DAYS:
            continue
        closes = [float(s.close) for s in snapshots]
        fundamentals_row = await market_data.get_latest_fundamentals(db, item.stock_id)
        observed_fundamentals = backtest_core.fundamentals_to_observed(fundamentals_row)
        series_list.append(backtest_core.build_stock_series(item.stock.ticker, closes, observed_fundamentals))

    if not series_list:
        raise HTTPException(
            status_code=400,
            detail=f"Histórico de preços insuficiente para otimizar (mínimo {backtest_core.MIN_HISTORY_DAYS} dias por ação).",
        )

    return backtest_core.optimize(series_list)


@router.delete("/{template_id}", status_code=204)
async def delete_strategy(
    template_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    template = await _get_owned_template(db, template_id, user.id)
    await db.delete(template)
    await db.commit()


@router.post("/{template_id}/items", response_model=StrategyItemOut, status_code=201)
async def add_item(
    template_id: uuid.UUID, body: StrategyItemIn,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    await _get_owned_template(db, template_id, user.id)
    _validate_item(body)
    item = StrategyItem(template_id=template_id, **body.model_dump())
    db.add(item)
    await db.commit()
    return StrategyItemOut.model_validate(item)


@router.put("/items/{item_id}", response_model=StrategyItemOut)
async def update_item(
    item_id: uuid.UUID, body: StrategyItemIn,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    item = (
        await db.execute(
            select(StrategyItem).join(StrategyTemplate)
            .where(StrategyItem.id == item_id, StrategyTemplate.user_id == user.id)
        )
    ).scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Não encontrado")
    _validate_item(body)
    for key, value in body.model_dump().items():
        setattr(item, key, value)
    await db.commit()
    return StrategyItemOut.model_validate(item)


@router.delete("/items/{item_id}", status_code=204)
async def delete_item(
    item_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    item = (
        await db.execute(
            select(StrategyItem).join(StrategyTemplate)
            .where(StrategyItem.id == item_id, StrategyTemplate.user_id == user.id)
        )
    ).scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Não encontrado")
    await db.delete(item)
    await db.commit()
