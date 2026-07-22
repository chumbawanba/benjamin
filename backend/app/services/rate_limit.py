"""Rate limiting simples em memória, por utilizador autenticado.

Protege endpoints que chamam APIs externas pagas ou com quota (OpenAI,
Finnhub, TwelveData) contra uso excessivo — não é defesa contra DDoS, é só um
limite de bom senso por utilizador, para controlar custo (OpenAI) e não
esgotar as quotas grátis do Finnhub/TwelveData.

Em memória: reinicia ao reiniciar o container e não é partilhado entre várias
instâncias da API — suficiente para o deployment atual (uma única instância
de `api`, ver docker-compose.prod.yml). Se um dia houver múltiplas instâncias,
isto precisa de passar para Redis; não construído agora, sem essa necessidade.
"""
import time
from collections import defaultdict, deque

from fastapi import Depends, HTTPException

from app.models import User
from app.security import get_current_user

_hits: dict[str, deque[float]] = defaultdict(deque)


def rate_limit_user(name: str, max_calls: int, window_seconds: int):
    """Dependency factory: no máximo `max_calls` chamadas a este endpoint por
    utilizador, em cada janela de `window_seconds`. Substitui diretamente
    `Depends(get_current_user)` na assinatura da rota (devolve o User)."""

    async def dependency(user: User = Depends(get_current_user)) -> User:
        key = f"{name}:{user.id}"
        now = time.monotonic()
        hits = _hits[key]
        while hits and now - hits[0] > window_seconds:
            hits.popleft()
        if len(hits) >= max_calls:
            retry_after = int(window_seconds - (now - hits[0])) + 1
            raise HTTPException(
                status_code=429,
                detail=f"Demasiados pedidos — tenta novamente daqui a {retry_after}s.",
                headers={"Retry-After": str(retry_after)},
            )
        hits.append(now)
        return user

    return dependency
