from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import WaitlistIn
from app.services import waitlist

router = APIRouter(prefix="/waitlist", tags=["waitlist"])


@router.post("", status_code=204)
async def join(body: WaitlistIn, db: AsyncSession = Depends(get_db)) -> None:
    if not body.accepted_terms:
        raise HTTPException(
            status_code=422, detail="É necessário aceitar a Política de Privacidade e de Cookies"
        )
    await waitlist.join_waitlist(db, body.email)
