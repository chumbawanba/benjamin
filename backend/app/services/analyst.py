"""Resumo estilo analista financeiro, gerado por LLM (OpenAI), combinando os
sinais já calculados pelo motor de regras (agent_core.py) para a watchlist do
utilizador com uma visão geral do mercado (índices + notícias gerais).

Importante: isto NÃO substitui o motor de avaliação determinístico - é só uma
camada de texto em cima dos números que ele já produz, mais contexto de
mercado. Atualizado manualmente pelo utilizador (botão "Atualizar análise" no
Overview) - nunca corre em background/scheduler, ao contrário do resto da app.
"""
import logging
from datetime import datetime, timezone

from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models import Evaluation, Position, User, WatchlistItem
from app.services import market_data

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = (
    "Chamas-te Benjamin e és o analista financeiro pessoal do utilizador. "
    "Escreves um resumo curto (3 a 5 parágrafos, sem bullet points nem "
    "markdown) em português europeu sobre a situação dele agora: o que "
    "realmente possui (portfólio), o que está a acompanhar (watchlist) e o "
    "contexto geral do mercado. Usas os dados fornecidos (posições reais com "
    "peso no portfólio e P&L, preços, variações, sinais de compra/venda já "
    "calculados por um motor de regras determinístico, notícias). "
    "Prestas particular atenção à exposição real: concentração excessiva numa "
    "ação ou setor, posições com sinal de venda ativo, e sinais de compra na "
    "watchlist em ações que o utilizador ainda não possui - aponta essas "
    "situações como pontos a considerar. Sintetizas e destacas o que parece "
    "mais relevante - não te limitas a listar tudo outra vez. Não dás "
    "conselhos de investimento diretos nem dizes 'deves comprar' ou 'deves "
    "vender' - descreves o que os dados mostram e porque pode ser relevante, "
    "deixando a decisão para o utilizador. Terminas sempre com uma frase "
    "curta a lembrar que isto é apenas informativo, gerado automaticamente, "
    "e não é aconselhamento financeiro."
)

MAX_PROMPT_LENGTH = 4000  # ~1000 tokens - suficiente para instruções, evita custos descontrolados


class AnalystNotConfigured(Exception):
    """OPENAI_API_KEY não está definida - feature indisponível, não é erro."""


def effective_prompt(user: User) -> str:
    """Prompt de sistema a usar: o personalizado do utilizador, se existir e
    não for só espaços em branco, senão o DEFAULT_SYSTEM_PROMPT."""
    if user.analyst_prompt and user.analyst_prompt.strip():
        return user.analyst_prompt
    return DEFAULT_SYSTEM_PROMPT


async def _build_context(db: AsyncSession, user: User) -> str:
    positions = (
        await db.execute(
            select(Position).options(selectinload(Position.stock))
            .where(Position.user_id == user.id)
            .order_by(Position.created_at.asc())
        )
    ).scalars().all()

    position_rows = []  # (position, last_price, market_value | None)
    total_market_value = 0.0
    for p in positions:
        last_price, _ = await market_data.get_price_change(db, p.stock_id)
        market_value = float(p.quantity) * float(last_price) if last_price is not None else None
        if market_value is not None:
            total_market_value += market_value
        position_rows.append((p, last_price, market_value))

    lines = ["## Portfólio do utilizador (posições reais)"]
    if not positions:
        lines.append("(sem posições registadas - o utilizador ainda não introduziu o que possui)")
    for p, last_price, market_value in position_rows:
        cost_total = float(p.quantity) * float(p.avg_cost)
        pl_pct = ((market_value - cost_total) / cost_total * 100) if market_value is not None and cost_total else None
        weight_pct = (market_value / total_market_value * 100) if market_value is not None and total_market_value else None
        price_str = f"{last_price}" if last_price is not None else "sem preço"
        pl_str = f"P&L {pl_pct:+.1f}%" if pl_pct is not None else "P&L desconhecido"
        weight_str = f", {weight_pct:.0f}% do portfólio" if weight_pct is not None else ""
        lines.append(
            f"- {p.stock.ticker} ({p.stock.name or 'nome desconhecido'}): "
            f"{p.quantity} unidades a custo médio {p.avg_cost}, preço atual {price_str}, {pl_str}{weight_str}"
        )
    if total_market_value:
        lines.append(f"Valor total de mercado do portfólio: {total_market_value:.2f}")

    owned_stock_ids = {p.stock_id for p in positions}

    items = (
        await db.execute(
            select(WatchlistItem).options(selectinload(WatchlistItem.stock))
            .where(WatchlistItem.user_id == user.id)
            .order_by(WatchlistItem.display_order.asc(), WatchlistItem.added_at.desc())
        )
    ).scalars().all()

    lines.append("\n## Watchlist do utilizador")
    if not items:
        lines.append("(vazia)")
    for item in items:
        last_price, change_pct = await market_data.get_price_change(db, item.stock_id)
        latest = (
            await db.execute(
                select(Evaluation).where(
                    Evaluation.user_id == user.id, Evaluation.stock_id == item.stock_id,
                ).order_by(Evaluation.run_at.desc()).limit(1)
            )
        ).scalar_one_or_none()
        if latest is not None:
            signal = f"{latest.recommendation} (compra={latest.buy_score}, venda={latest.sell_score})"
        else:
            signal = "sem avaliação ainda"
        price_str = f"{last_price}" if last_price is not None else "sem preço"
        change_str = f"{float(change_pct):+.2f}%" if change_pct is not None else "sem variação"
        ownership = "já possui" if item.stock_id in owned_stock_ids else "não possui"
        lines.append(
            f"- {item.stock.ticker} ({item.stock.name or 'nome desconhecido'}): "
            f"preço {price_str}, variação hoje {change_str}, sinal: {signal} ({ownership})"
        )

    pulse = await market_data.get_market_pulse()
    lines.append("\n## Mercado geral (índices, variação % hoje)")
    for idx in pulse["indices"]:
        change = f"{idx['change_pct']:+.2f}%" if idx["change_pct"] is not None else "sem dados"
        lines.append(f"- {idx['label']} ({idx['symbol']}): {change}")

    lines.append("\n## Notícias gerais recentes")
    if not pulse["news"]:
        lines.append("(sem notícias disponíveis)")
    for n in pulse["news"]:
        lines.append(f"- {n['headline']} — {n['source'] or 'fonte desconhecida'}")

    return "\n".join(lines)


async def generate_summary(db: AsyncSession, user: User) -> str:
    """Gera e persiste um novo resumo, substituindo o anterior. Lança
    AnalystNotConfigured se não houver chave, ou deixa propagar erros da
    OpenAI (o router traduz para um 502 com mensagem amigável)."""
    if not settings.openai_api_key:
        raise AnalystNotConfigured("OPENAI_API_KEY não configurada")

    context = await _build_context(db, user)
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    response = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": effective_prompt(user)},
            {"role": "user", "content": context},
        ],
        max_tokens=700,
    )
    text = response.choices[0].message.content if response.choices else None
    if not text or not text.strip():
        raise RuntimeError("Resposta vazia da OpenAI")

    user.analyst_summary = text.strip()
    user.analyst_summary_generated_at = datetime.now(timezone.utc)
    await db.commit()
    return user.analyst_summary
