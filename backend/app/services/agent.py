"""Agente: liga checklist + indicadores + BD. A logica de score vive em agent_core."""
import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ChecklistItem, ChecklistTemplate, Evaluation, EvaluationDetail, Stock
from app.services import indicators, market_data
from app.services.agent_core import compute_evaluation


async def evaluate(
    db: AsyncSession, stock_id: uuid.UUID, template_id: uuid.UUID, user_id: uuid.UUID
) -> Evaluation:
    stock = (await db.execute(select(Stock).where(Stock.id == stock_id))).scalar_one()
    await market_data.ensure_fresh(db, stock)

    items_rows = (
        await db.execute(
            select(ChecklistItem)
            .where(ChecklistItem.template_id == template_id, ChecklistItem.is_active.is_(True))
            .order_by(ChecklistItem.display_order.asc().nulls_last())
        )
    ).scalars().all()

    items = [
        {
            "id": i.id, "metric": i.metric, "operator": i.operator,
            "threshold_value": i.threshold_value, "threshold_value_max": i.threshold_value_max,
            "weight": i.weight, "direction": i.direction,
        }
        for i in items_rows
    ]

    metrics = {i["metric"] for i in items} | {"PRICE_CLOSE"}
    observed: dict[str, float | None] = {}
    for metric in metrics:
        observed[metric] = await indicators.get_indicator(db, stock_id, metric)

    result = compute_evaluation(items, observed)

    evaluation = Evaluation(
        user_id=user_id, stock_id=stock_id, checklist_template_id=template_id,
        buy_score=Decimal(str(result.buy_score)), sell_score=Decimal(str(result.sell_score)),
        recommendation=result.recommendation,
        price_at_evaluation=(
            Decimal(str(observed["PRICE_CLOSE"])) if observed.get("PRICE_CLOSE") is not None else None
        ),
    )
    db.add(evaluation)
    await db.flush()
    for d in result.details:
        db.add(EvaluationDetail(
            evaluation_id=evaluation.id, checklist_item_id=d.item_id,
            observed_value=Decimal(str(d.observed_value)) if d.observed_value is not None else None,
            passed=d.passed,
            contribution=Decimal(str(d.contribution)),
        ))
    await db.flush()
    return evaluation
