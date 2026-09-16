from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, WaitlistEntry


async def get_stats(db: AsyncSession) -> dict:
    """Contagens simples para o endpoint operacional GET /admin/stats (ver
    routers/admin.py) - sem paginação nem histórico, só o número atual de
    registos em cada tabela. Ver CLAUDE.md: nada de abstrações para o futuro
    além do que este endpoint precisa agora."""
    users_total = (await db.execute(select(func.count()).select_from(User))).scalar_one()
    waitlist_total = (await db.execute(select(func.count()).select_from(WaitlistEntry))).scalar_one()
    return {"users_total": users_total, "waitlist_total": waitlist_total}
