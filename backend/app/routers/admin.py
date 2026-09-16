from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import AdminStatsOut
from app.security import require_admin
from app.services import admin

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("/stats", response_model=AdminStatsOut)
async def stats(db: AsyncSession = Depends(get_db)):
    return await admin.get_stats(db)
