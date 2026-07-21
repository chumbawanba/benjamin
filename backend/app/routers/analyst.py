import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.schemas.common import (
    AnalystAskIn, AnalystAskOut, AnalystPromptIn, AnalystPromptOut, AnalystSummaryOut,
)
from app.security import get_current_user
from app.services import analyst

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analyst", tags=["analyst"])


def _as_utc(dt: datetime | None) -> datetime | None:
    """Alguns drivers de BD (nomeadamente SQLite/aiosqlite, usado nos testes)
    devolvem datetimes sem tzinfo mesmo em colunas DateTime(timezone=True),
    o que faz a serialização variar consoante o valor vem direto da memória
    ou de uma query. Normalizamos sempre para UTC explícito aqui."""
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


@router.get("/summary", response_model=AnalystSummaryOut)
async def get_summary(user: User = Depends(get_current_user)):
    """Devolve o último resumo gerado (cache no User) — nunca chama o LLM.
    A atualização é sempre manual, via POST /analyst/summary/refresh."""
    return AnalystSummaryOut(
        summary=user.analyst_summary, generated_at=_as_utc(user.analyst_summary_generated_at),
    )


@router.post("/ask", response_model=AnalystAskOut)
async def ask(
    body: AnalystAskIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    """Pergunta ao Benjamin com o contexto completo (portfólio + watchlist +
    detalhe critério-a-critério das avaliações + mercado). Sem persistência —
    o histórico da conversa vem do frontend a cada pedido."""
    try:
        answer = await analyst.generate_answer(db, user, body.question, body.history)
    except analyst.AnalystNotConfigured as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        logger.warning("Falha ao responder pergunta do analista para %s", user.id, exc_info=True)
        raise HTTPException(
            status_code=502, detail="Não foi possível obter resposta (serviço de IA indisponível).",
        ) from e
    return AnalystAskOut(answer=answer)


@router.get("/prompt", response_model=AnalystPromptOut)
async def get_prompt(user: User = Depends(get_current_user)):
    """Devolve o prompt de sistema atualmente em uso (personalizado, se
    existir, senão a predefinição) — para pré-preencher o editor no frontend."""
    is_default = not (user.analyst_prompt and user.analyst_prompt.strip())
    return AnalystPromptOut(prompt=analyst.effective_prompt(user), is_default=is_default)


@router.put("/prompt", response_model=AnalystPromptOut)
async def update_prompt(
    body: AnalystPromptIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    if body.prompt and len(body.prompt) > analyst.MAX_PROMPT_LENGTH:
        raise HTTPException(
            status_code=422,
            detail=f"Prompt demasiado longo (máximo {analyst.MAX_PROMPT_LENGTH} caracteres)",
        )
    user.analyst_prompt = body.prompt.strip() if body.prompt and body.prompt.strip() else None
    await db.commit()
    is_default = user.analyst_prompt is None
    return AnalystPromptOut(prompt=analyst.effective_prompt(user), is_default=is_default)


@router.post("/summary/refresh", response_model=AnalystSummaryOut)
async def refresh_summary(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    try:
        await analyst.generate_summary(db, user)
    except analyst.AnalystNotConfigured as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        logger.warning("Falha ao gerar resumo do analista para %s", user.id, exc_info=True)
        raise HTTPException(
            status_code=502, detail="Não foi possível gerar o resumo (serviço de IA indisponível).",
        ) from e
    return AnalystSummaryOut(
        summary=user.analyst_summary, generated_at=_as_utc(user.analyst_summary_generated_at),
    )
