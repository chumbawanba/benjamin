from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, WaitlistEntry


async def get_stats(db: AsyncSession) -> dict:
    """Dados para o endpoint operacional GET /admin/stats (ver routers/admin.py):
    listas de emails + contagens diárias para o gráfico. Sem paginação - o
    volume esperado (utilizadores beta) não justifica isso ainda (CLAUDE.md:
    nada de abstrações para o futuro além do que este endpoint precisa agora).
    A agregação por dia é feita aqui em Python, não em SQL, para não depender
    de funções de data específicas do Postgres que não existem no SQLite dos
    testes (ver conftest.py)."""
    users_rows = (
        await db.execute(select(User.email, User.created_at).order_by(User.created_at.desc()))
    ).all()
    waitlist_rows = (
        await db.execute(select(WaitlistEntry.email, WaitlistEntry.created_at).order_by(WaitlistEntry.created_at.desc()))
    ).all()

    daily: dict[str, dict[str, int]] = defaultdict(lambda: {"users": 0, "waitlist": 0})
    for row in users_rows:
        daily[row.created_at.date().isoformat()]["users"] += 1
    for row in waitlist_rows:
        daily[row.created_at.date().isoformat()]["waitlist"] += 1

    daily_registrations = [
        {"date": day, "users": counts["users"], "waitlist": counts["waitlist"]}
        for day, counts in sorted(daily.items())
    ]

    return {
        "users_total": len(users_rows),
        "waitlist_total": len(waitlist_rows),
        "users": [{"email": row.email, "created_at": row.created_at} for row in users_rows],
        "waitlist": [{"email": row.email, "created_at": row.created_at} for row in waitlist_rows],
        "daily_registrations": daily_registrations,
    }
