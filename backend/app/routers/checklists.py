import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import ChecklistItem, ChecklistTemplate, User
from app.schemas.common import (
    VALID_DIRECTIONS, VALID_OPERATORS,
    ChecklistItemIn, ChecklistItemOut, ChecklistTemplateIn, ChecklistTemplateOut,
)
from app.security import get_current_user
from app.services.indicators_core import INDICATORS

router = APIRouter(prefix="/checklists", tags=["checklists"])


def _validate_item(body: ChecklistItemIn) -> None:
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


async def _get_owned_template(
    db: AsyncSession, template_id: uuid.UUID, user_id: uuid.UUID
) -> ChecklistTemplate:
    template = (
        await db.execute(
            select(ChecklistTemplate).options(selectinload(ChecklistTemplate.items))
            .where(ChecklistTemplate.id == template_id, ChecklistTemplate.user_id == user_id)
        )
    ).scalar_one_or_none()
    if template is None:
        raise HTTPException(status_code=404, detail="Não encontrado")
    return template


@router.get("/metrics")
async def list_metrics(user: User = Depends(get_current_user)):
    return [
        {"key": key, "kind": spec["kind"], "lookback_days": spec["lookback_days"]}
        for key, spec in INDICATORS.items()
    ]


@router.get("", response_model=list[ChecklistTemplateOut])
async def list_checklists(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    templates = (
        await db.execute(
            select(ChecklistTemplate).options(selectinload(ChecklistTemplate.items))
            .where(ChecklistTemplate.user_id == user.id)
            .order_by(ChecklistTemplate.created_at.desc())
        )
    ).scalars().all()
    return templates


@router.post("", response_model=ChecklistTemplateOut, status_code=201)
async def create_checklist(
    body: ChecklistTemplateIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    template = ChecklistTemplate(user_id=user.id, **body.model_dump())
    db.add(template)
    await db.commit()
    return await _get_owned_template(db, template.id, user.id)


@router.put("/{template_id}", response_model=ChecklistTemplateOut)
async def update_checklist(
    template_id: uuid.UUID, body: ChecklistTemplateIn,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    template = await _get_owned_template(db, template_id, user.id)
    for key, value in body.model_dump().items():
        setattr(template, key, value)
    await db.commit()
    return await _get_owned_template(db, template_id, user.id)


@router.delete("/{template_id}", status_code=204)
async def delete_checklist(
    template_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    template = await _get_owned_template(db, template_id, user.id)
    await db.delete(template)
    await db.commit()


@router.post("/{template_id}/items", response_model=ChecklistItemOut, status_code=201)
async def add_item(
    template_id: uuid.UUID, body: ChecklistItemIn,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    await _get_owned_template(db, template_id, user.id)
    _validate_item(body)
    item = ChecklistItem(template_id=template_id, **body.model_dump())
    db.add(item)
    await db.commit()
    return ChecklistItemOut.model_validate(item)


@router.put("/items/{item_id}", response_model=ChecklistItemOut)
async def update_item(
    item_id: uuid.UUID, body: ChecklistItemIn,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    item = (
        await db.execute(
            select(ChecklistItem).join(ChecklistTemplate)
            .where(ChecklistItem.id == item_id, ChecklistTemplate.user_id == user.id)
        )
    ).scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Não encontrado")
    _validate_item(body)
    for key, value in body.model_dump().items():
        setattr(item, key, value)
    await db.commit()
    return ChecklistItemOut.model_validate(item)


@router.delete("/items/{item_id}", status_code=204)
async def delete_item(
    item_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    item = (
        await db.execute(
            select(ChecklistItem).join(ChecklistTemplate)
            .where(ChecklistItem.id == item_id, ChecklistTemplate.user_id == user.id)
        )
    ).scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Não encontrado")
    await db.delete(item)
    await db.commit()
