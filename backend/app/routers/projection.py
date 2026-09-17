from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.schemas.common import ProjectionOut
from app.security import get_current_user
from app.services import projection as projection_service

router = APIRouter(prefix="/projection", tags=["projection"])


@router.get("", response_model=ProjectionOut)
async def get_projection(
    years: int = Query(20, ge=1, le=60),
    annual_return_pct: Decimal = Query(Decimal("5")),
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    result = await projection_service.compute(db, user, years, annual_return_pct)
    await db.commit()  # ensure_fresh/get_rate podem ter gravado cache novo
    return result
