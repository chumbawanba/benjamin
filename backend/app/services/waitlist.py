from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import WaitlistEntry


async def join_waitlist(db: AsyncSession, email: str) -> None:
    """Regista um email na waitlist. Idempotente - um email repetido não gera
    erro nem duplicado, só é ignorado (não queremos confirmar/negar a um
    visitante anónimo se um email já está ou não na lista). A validação de
    accepted_terms é feita no router (routers/waitlist.py), antes de chamar
    esta função - aqui só gravamos o timestamp da aceitação."""
    exists = (await db.execute(select(WaitlistEntry).where(WaitlistEntry.email == email))).scalar_one_or_none()
    if exists is not None:
        return
    db.add(WaitlistEntry(email=email, accepted_terms_at=datetime.now(timezone.utc)))
    await db.commit()
