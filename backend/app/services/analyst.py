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
from app.models import (
    Evaluation, FundamentalsSnapshot, Position, StrategyItem, StrategyTemplate, User, WatchlistItem,
)
from app.schemas.common import AnalystChatMessageIn
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

ASK_SYSTEM_PROMPT = (
    "Chamas-te Benjamin e és o analista financeiro pessoal do utilizador, agora "
    "numa conversa de perguntas e respostas. Recebes o mesmo contexto do resumo "
    "(portfólio, watchlist, mercado geral) mais o detalhe critério-a-critério de "
    "cada avaliação (nome do critério, métrica, threshold, valor observado, se "
    "passou ou falhou, contribuição para o score). Respondes de forma direta e "
    "curta (poucas frases, sem bullet points nem markdown) à pergunta do "
    "utilizador - por exemplo, para explicar porque uma ação tem ou não sinal de "
    "compra/venda, aponta os critérios concretos que passaram ou falharam; para "
    "perguntas sobre lucros ou posição financeira de uma ação (crescimento de "
    "receita, margem, ROE, rácio corrente, dívida/capital, etc.), usa os "
    "fundamentais fornecidos no contexto. "
    "Também tens um papel educativo: podes explicar conceitos, métricas e "
    "estratégias de investimento em geral - incluindo a abordagem de Benjamin "
    "Graham (value investing, margem de segurança, P/E, dívida/capital, etc.) e "
    "outras abordagens conhecidas (growth investing, dividend investing, "
    "indexação, etc.) - mesmo quando a pergunta não tem relação direta com os "
    "dados concretos do utilizador. Nestas respostas educativas, é claro que "
    "estás a explicar um conceito ou estratégia em geral, não a fazer uma "
    "recomendação sobre o portfólio dele. "
    "O que não podes fazer é inventar factos concretos que não estão nos dados "
    "fornecidos - por exemplo, se perguntarem que mercados estão a crescer agora "
    "e os dados de mercado geral fornecidos não cobrirem isso, di-lo em vez de "
    "inventar números ou eventos. Não dás conselhos de investimento diretos - "
    "nem no contexto do portfólio do utilizador, nem em respostas educativas -  "
    "descreves o que os dados ou a teoria mostram, deixando a decisão para o "
    "utilizador."
)

MAX_QUESTION_LENGTH = 1000  # espelha AnalystAskIn.question em schemas/common.py
MAX_HISTORY_MESSAGES = 20  # espelha AnalystAskIn.history em schemas/common.py - defesa extra no serviço


class AnalystNotConfigured(Exception):
    """OPENAI_API_KEY não está definida - feature indisponível, não é erro."""


def effective_prompt(user: User) -> str:
    """Prompt de sistema a usar: o personalizado do utilizador, se existir e
    não for só espaços em branco, senão o DEFAULT_SYSTEM_PROMPT."""
    if user.analyst_prompt and user.analyst_prompt.strip():
        return user.analyst_prompt
    return DEFAULT_SYSTEM_PROMPT


def _format_fundamentals(row: FundamentalsSnapshot | None) -> str:
    """Linha compacta com os fundamentais disponíveis (só os que existem) -
    mesmos campos já usados nas estratégias (PE_RATIO, DIVIDEND_YIELD, EPS,
    DEBT_TO_EQUITY, MARKET_CAP) mais métricas de "posição financeira"
    (crescimento de receita, margem líquida, ROE, rácio corrente, margem
    bruta, margem operacional, crescimento de EPS, crescimento de dividendo a
    5 anos) - permitem ao Benjamin responder a perguntas sobre lucros/saúde
    financeira de uma ação, não só os critérios de estratégia. Formatação
    como no registry de indicadores (indicators_core.py): dividend_yield é
    fração (0.02 = 2%), market_cap em USD (mostrado em B$); todos os
    restantes já vêm em percentagem/rácio direto (ver
    market_data.refresh_fundamentals)."""
    if row is None:
        return "sem fundamentais"
    parts = []
    if row.pe_ratio is not None:
        parts.append(f"P/E {row.pe_ratio}")
    if row.dividend_yield is not None:
        parts.append(f"dividendo {float(row.dividend_yield) * 100:.1f}%")
    if row.eps is not None:
        parts.append(f"EPS {row.eps}")
    if row.debt_to_equity is not None:
        parts.append(f"dívida/capital {row.debt_to_equity}")
    if row.market_cap is not None:
        parts.append(f"cap. mercado {row.market_cap / 1_000_000_000:.1f}B$")
    if row.revenue_growth is not None:
        parts.append(f"crescimento receita {row.revenue_growth}%")
    if row.net_margin is not None:
        parts.append(f"margem líquida {row.net_margin}%")
    if row.roe is not None:
        parts.append(f"ROE {row.roe}%")
    if row.current_ratio is not None:
        parts.append(f"rácio corrente {row.current_ratio}")
    if row.gross_margin is not None:
        parts.append(f"margem bruta {row.gross_margin}%")
    if row.operating_margin is not None:
        parts.append(f"margem operacional {row.operating_margin}%")
    if row.eps_growth is not None:
        parts.append(f"crescimento EPS {row.eps_growth}%")
    if row.dividend_growth_5y is not None:
        parts.append(f"crescimento dividendo 5A {row.dividend_growth_5y}%")
    return ", ".join(parts) if parts else "sem fundamentais"


async def _latest_fundamentals(db: AsyncSession, stock_id) -> FundamentalsSnapshot | None:
    return (
        await db.execute(
            select(FundamentalsSnapshot).where(FundamentalsSnapshot.stock_id == stock_id)
            .order_by(FundamentalsSnapshot.date.desc()).limit(1)
        )
    ).scalar_one_or_none()


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
        fundamentals_str = _format_fundamentals(await _latest_fundamentals(db, p.stock_id))
        lines.append(
            f"- {p.stock.ticker} ({p.stock.name or 'nome desconhecido'}): "
            f"{p.quantity} unidades a custo médio {p.avg_cost}, preço atual {price_str}, {pl_str}{weight_str} "
            f"[{fundamentals_str}]"
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
        fundamentals_str = _format_fundamentals(await _latest_fundamentals(db, item.stock_id))
        lines.append(
            f"- {item.stock.ticker} ({item.stock.name or 'nome desconhecido'}): "
            f"preço {price_str}, variação hoje {change_str}, sinal: {signal} ({ownership}) "
            f"[{fundamentals_str}]"
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


async def _build_criteria_context(db: AsyncSession, user: User) -> str:
    """Detalhe critério-a-critério da avaliação mais recente de cada ação da
    watchlist, por estratégia ativa - permite ao Benjamin explicar o 'porquê'
    de um sinal quando questionado (ex: 'porque não tenho compra na
    Microsoft?'), o que o resumo normal não inclui (só o sinal final). Reusa a
    mesma informação de GET /watchlist/{id}/detail, mas para toda a watchlist
    de uma vez, não só uma ação."""
    items = (
        await db.execute(
            select(WatchlistItem).options(selectinload(WatchlistItem.stock))
            .where(WatchlistItem.user_id == user.id)
            .order_by(WatchlistItem.display_order.asc())
        )
    ).scalars().all()
    if not items:
        return ""

    lines = ["\n## Detalhe critério-a-critério das avaliações mais recentes"]
    any_detail = False
    for item in items:
        evaluations = (
            await db.execute(
                select(Evaluation).options(selectinload(Evaluation.details))
                .where(Evaluation.user_id == user.id, Evaluation.stock_id == item.stock_id)
                .order_by(Evaluation.run_at.desc())
            )
        ).scalars().all()
        # última avaliação por estratégia - pode haver mais que uma estratégia ativa
        latest_by_template: dict = {}
        for ev in evaluations:
            latest_by_template.setdefault(ev.strategy_template_id, ev)

        for template_id, ev in latest_by_template.items():
            template = (
                await db.execute(select(StrategyTemplate).where(StrategyTemplate.id == template_id))
            ).scalar_one_or_none()
            if template is None or not template.is_active:
                continue
            item_ids = [d.strategy_item_id for d in ev.details]
            strategy_items = (
                await db.execute(select(StrategyItem).where(StrategyItem.id.in_(item_ids)))
            ).scalars().all()
            items_by_id = {si.id: si for si in strategy_items}
            if not items_by_id:
                continue
            any_detail = True
            lines.append(
                f"\n### {item.stock.ticker} - {template.name} "
                f"({ev.recommendation}, compra={ev.buy_score}, venda={ev.sell_score})"
            )
            for d in ev.details:
                si = items_by_id.get(d.strategy_item_id)
                if si is None:
                    continue
                status = "passou" if d.passed else ("falhou" if d.passed is False else "sem dados")
                threshold = f"{si.operator} {si.threshold_value}"
                if si.threshold_value_max is not None:
                    threshold += f" a {si.threshold_value_max}"
                lines.append(
                    f"- {si.name} ({si.metric} {threshold}): observado {d.observed_value}, "
                    f"{status}, contribuição {d.contribution}"
                )

    return "\n".join(lines) if any_detail else ""


async def generate_answer(
    db: AsyncSession, user: User, question: str, history: list[AnalystChatMessageIn],
) -> str:
    """Responde a uma pergunta do utilizador com o mesmo contexto do resumo
    (portfólio + watchlist + mercado) mais o detalhe critério-a-critério das
    avaliações, e o histórico da conversa até agora (vindo do frontend, sem
    persistência em BD). Lança AnalystNotConfigured se não houver chave, ou
    deixa propagar erros da OpenAI (o router traduz para um 502)."""
    if not settings.openai_api_key:
        raise AnalystNotConfigured("OPENAI_API_KEY não configurada")

    context = await _build_context(db, user) + await _build_criteria_context(db, user)

    messages = [
        {"role": "system", "content": ASK_SYSTEM_PROMPT},
        {"role": "user", "content": context},
    ]
    for msg in history[-MAX_HISTORY_MESSAGES:]:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": question})

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    response = await client.chat.completions.create(
        model=settings.openai_model, messages=messages, max_tokens=500,
    )
    text = response.choices[0].message.content if response.choices else None
    if not text or not text.strip():
        raise RuntimeError("Resposta vazia da OpenAI")
    return text.strip()


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
