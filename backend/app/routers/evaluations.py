import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import ChecklistTemplate, Evaluation, User, WatchlistItem
from app.schemas.common import EvaluationOut, RunEvaluationIn
from app.security import get_current_user
from app.services import agent

router = APIRouter(prefix="/evaluations", tags=["evaluations"])


@router.post("/run", response_model=list[EvaluationOut])
async def run_evaluation(
    body: RunEvaluationIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    template = (
        await db.execute(select(ChecklistTemplate).where(
            ChecklistTemplate.id == body.template_id, ChecklistTemplate.user_id == user.id
        ))
    ).scalar_one_or_none()
    if template is None:
        raise HTTPException(status_code=404, detail="Checklist não encontrada")

    if body.stock_id is not None:
        in_watchlist = (
            await db.execute(select(WatchlistItem).where(
                WatchlistItem.user_id == user.id, WatchlistItem.stock_id == body.stock_id
            ))
        ).scalar_one_or_none()
        if in_watchlist is None:
            raise HTTPException(status_code=404, detail="Ação não está na watchlist")
        stock_ids = [body.stock_id]
    else:
        stock_ids = (
            await db.execute(
                select(WatchlistItem.stock_id).where(WatchlistItem.user_id == user.id)
            )
        ).scalars().all()

    results = []
    for stock_id in stock_ids:
        evaluation = await agent.evaluate(db, stock_id, template.id, user.id)
        results.append(evaluation.id)
    await db.commit()

    rows = (
        await db.execute(
            select(Evaluation).options(selectinload(Evaluation.details))
            .where(Evaluation.id.in_(results))
        )
    ).scalars().all()
    return rows


@router.get("/latest", response_model=list[EvaluationOut])
async def latest_evaluations(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    stock_ids = (
        await db.execute(select(WatchlistItem.stock_id).where(WatchlistItem.user_id == user.id))
    ).scalars().all()
    out = []
    for stock_id in stock_ids:
        row = (
            await db.execute(
                select(Evaluation).options(selectinload(Evaluation.details))
                .where(Evaluation.user_id == user.id, Evaluation.stock_id == stock_id)
                .order_by(Evaluation.run_at.desc()).limit(1)
            )
        ).scalar_one_or_none()
        if row:
            out.append(row)
    out.sort(key=lambda e: float(e.buy_score), reverse=True)
    return out


@router.get("", response_model=list[EvaluationOut])
async def evaluation_history(
    stock_id: uuid.UUID | None = None,
    limit: int = Query(default=20, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(Evaluation).options(selectinload(Evaluation.details))
        .where(Evaluation.user_id == user.id)
        .order_by(Evaluation.run_at.desc()).limit(limit)
    )
    if stock_id is not None:
        query = query.where(Evaluation.stock_id == stock_id)
    return (await db.execute(query)).scalars().all()
