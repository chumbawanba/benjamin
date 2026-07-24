"""Ingestão de dados de mercado via Finnhub (preço atual + fundamentais + pesquisa)
e Twelve Data (histórico diário, usado só para o backfill inicial por ação).

Substitui o yfinance (Fase 3 original): o Yahoo Finance não tem API oficial e
bloqueia pedidos com 429 de forma imprevisível e persistente. Ver HANDOFF.md.

Nomes dos campos de `/stock/metric` confirmados com payload real (MSFT,
2026-07-17): peTTM, currentDividendYieldTTM/dividendYieldIndicatedAnnual (em
percentagem, daí a divisão por 100), marketCapitalization (em milhões, daí a
multiplicação por 1_000_000), epsTTM, totalDebt/totalEquityAnnual. Confirmados
de novo em 2026-07-23 (MSFT): roeTTM, netProfitMarginTTM, revenueGrowthTTMYoy
existem mesmo no payload - a razão de aparecerem vazios na app não era nome de
campo errado, era refresh_fundamentals nunca ser chamado para ações maduras
(ver ensure_fresh/FUNDAMENTALS_RETRY_COOLDOWN).
"""
import logging
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import FundamentalsSnapshot, PriceSnapshot, Stock

logger = logging.getLogger(__name__)


def _as_utc(dt: datetime | None) -> datetime | None:
    """SQLite/aiosqlite (usado nos testes) devolve datetimes sem tzinfo mesmo
    em colunas DateTime(timezone=True) - normaliza para UTC explícito antes de
    subtrair (mesmo padrão de app/routers/analyst.py::_as_utc)."""
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


FRESHNESS_DAYS = 3
MIN_HISTORY_ROWS = 200  # cobre SMA_200; abaixo disto tenta backfill via Twelve Data
BACKFILL_RETRY_COOLDOWN = timedelta(hours=6)  # ver ensure_fresh
QUOTE_REFRESH_COOLDOWN = timedelta(minutes=15)  # ver ensure_fresh/_record_latest_quote
FUNDAMENTALS_RETRY_COOLDOWN = timedelta(hours=6)  # ver refresh_fundamentals
HTTP_TIMEOUT = 10.0

FINNHUB_BASE = "https://finnhub.io/api/v1"
TWELVEDATA_BASE = "https://api.twelvedata.com"


async def _finnhub_get(path: str, params: dict) -> dict:
    """GET a um endpoint da Finnhub. Função isolada: facilita mock nos testes."""
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        resp = await client.get(
            f"{FINNHUB_BASE}/{path}", params={**params, "token": settings.finnhub_api_key}
        )
        resp.raise_for_status()
        return resp.json()


async def _twelvedata_get(path: str, params: dict) -> dict:
    """GET a um endpoint da Twelve Data. Função isolada: facilita mock nos testes."""
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        resp = await client.get(
            f"{TWELVEDATA_BASE}/{path}", params={**params, "apikey": settings.twelvedata_api_key}
        )
        resp.raise_for_status()
        return resp.json()


async def get_company_news(ticker: str, days: int = 7, limit: int = 5) -> list[dict]:
    """Notícias recentes de uma ação via Finnhub /company-news. Nunca lança
    exceção — devolve lista vazia se falhar (mesmo padrão de search_tickers)."""
    today = datetime.now(timezone.utc).date()
    since = today - timedelta(days=days)
    try:
        data = await _finnhub_get(
            "company-news",
            {"symbol": ticker, "from": since.isoformat(), "to": today.isoformat()},
        )
    except Exception:
        logger.warning("Finnhub indisponível a obter notícias de %s", ticker, exc_info=True)
        return []
    if not isinstance(data, list):
        return []
    out = []
    for item in data[:limit]:
        ts = item.get("datetime")
        out.append({
            "ticker": ticker,
            "headline": item.get("headline"),
            "summary": item.get("summary"),
            "url": item.get("url"),
            "source": item.get("source"),
            "published_at": datetime.fromtimestamp(ts, tz=timezone.utc) if ts else None,
        })
    return out


async def get_peers(ticker: str) -> list[str]:
    """Símbolos de empresas "parecidas" (mesma indústria) via Finnhub
    /stock/peers — usado para sugerir novas ações a partir das que já estão
    na watchlist do utilizador. O endpoint devolve uma lista simples de
    símbolos (não um dict), ao contrário da generalidade dos endpoints da
    Finnhub usados neste ficheiro. Nunca lança exceção — devolve lista vazia
    se falhar (mesmo padrão de search_tickers/get_company_news)."""
    try:
        data = await _finnhub_get("stock/peers", {"symbol": ticker})
    except Exception:
        logger.warning("Finnhub indisponível a obter peers de %s", ticker, exc_info=True)
        return []
    if not isinstance(data, list):
        return []
    return [p.upper() for p in data if isinstance(p, str) and p.upper() != ticker.upper()]


PEERS_REFRESH_COOLDOWN = timedelta(days=7)  # peers mudam raramente - cooldown bem maior que os outros campos deste ficheiro


async def get_peers_cached(db: AsyncSession, stock: Stock) -> list[str]:
    """Peers com cache em Stock.peers_cache/peers_fetched_at
    (PEERS_REFRESH_COOLDOWN) - evita gastar uma chamada Finnhub extra em
    toda visita à StockDetail, já que a composição de peers de uma empresa
    não muda de um dia para o outro (mesmo padrão dos outros campos
    last_*_attempt_at deste ficheiro, só que com um cooldown em dias)."""
    last_fetch = _as_utc(stock.peers_fetched_at)
    if last_fetch is not None and datetime.now(timezone.utc) - last_fetch < PEERS_REFRESH_COOLDOWN:
        return stock.peers_cache.split(",") if stock.peers_cache else []

    peers = (await get_peers(stock.ticker))[:10]  # cap - Stock.peers_cache é String(200)
    stock.peers_fetched_at = datetime.now(timezone.utc)
    stock.peers_cache = ",".join(peers) if peers else None
    await db.flush()
    return peers


MARKET_INDEX_PROXIES = [
    ("SPY", "S&P 500 (EUA, mercado amplo)"),
    ("QQQ", "Nasdaq 100 (tecnologia EUA)"),
    ("IWM", "Russell 2000 (small caps EUA)"),
    ("VGK", "Europa"),
    ("EEM", "Mercados emergentes"),
    ("XLK", "Setor tecnológico"),
    ("XLF", "Setor financeiro"),
    ("XLE", "Setor energético"),
    ("XLV", "Setor saúde"),
]


async def get_market_pulse(news_limit: int = 8) -> dict:
    """Visão geral do mercado: variação % de hoje de ETFs-proxy de índices,
    regiões e setores (ver MARKET_INDEX_PROXIES, via Finnhub /quote) + notícias
    gerais recentes (Finnhub /news?category=general). Usado pelo resumo e pelo
    chat do analista (analyst.py) - a variedade de regiões/setores permite
    responder a perguntas tipo "que mercados estão a crescer", não só EUA.
    Nunca lança exceção — degrada graciosamente (mesmo padrão de
    search_tickers/get_company_news), já que isto é só contexto extra para o
    LLM, não deve impedir a geração do resumo."""
    indices = []
    for symbol, label in MARKET_INDEX_PROXIES:
        change_pct = None
        try:
            quote = await _finnhub_get("quote", {"symbol": symbol})
            if isinstance(quote, dict):
                change_pct = quote.get("dp")
        except Exception:
            logger.warning("Finnhub indisponível a obter cotação de %s", symbol, exc_info=True)
        indices.append({"symbol": symbol, "label": label, "change_pct": change_pct})

    try:
        data = await _finnhub_get("news", {"category": "general"})
    except Exception:
        logger.warning("Finnhub indisponível a obter notícias gerais", exc_info=True)
        data = []
    news = []
    if isinstance(data, list):
        for item in data[:news_limit]:
            if not item.get("headline"):
                continue
            news.append({
                "headline": item.get("headline"),
                "source": item.get("source"),
                "url": item.get("url"),
            })
    return {"indices": indices, "news": news}


# Sufixo do ticker -> mercado/bolsa, para ajudar a escolher entre várias
# listagens do mesmo instrumento (ex: um ETF UCITS cotado em 8+ bolsas
# europeias em simultâneo). Aproximação a partir do sufixo devolvido pela
# Finnhub /search - a própria Finnhub não devolve o nome da bolsa nesse
# endpoint, só o `type` do instrumento (ver _finnhub_get("search", ...)),
# por isso isto é best-effort e não cobre todos os sufixos possíveis.
_EXCHANGE_SUFFIX_HINTS: dict[str, str] = {
    "L": "Londres", "DE": "Alemanha (Xetra)", "F": "Frankfurt", "SG": "Estugarda",
    "HM": "Hamburgo", "MU": "Munique", "BE": "Berlim", "DU": "Dusseldorf",
    "HA": "Hanôver", "PA": "Paris", "AS": "Amesterdão", "BR": "Bruxelas",
    "LS": "Lisboa", "MI": "Milão", "MC": "Madrid", "SW": "Suíça", "VX": "Suíça (SIX)",
    "TO": "Toronto", "HK": "Hong Kong", "T": "Tóquio", "AX": "Austrália",
    "SA": "Brasil (B3)", "MX": "México",
}


def _market_hint_from_ticker(ticker: str) -> str | None:
    """Ex: 'VWCE.LS' -> 'Lisboa'; 'AAPL' (sem sufixo) -> 'EUA'."""
    if "." not in ticker:
        return "EUA"
    suffix = ticker.rsplit(".", 1)[-1].upper()
    return _EXCHANGE_SUFFIX_HINTS.get(suffix, suffix)


async def search_tickers(query: str, limit: int = 8) -> list[dict]:
    """Pesquisa tickers por nome ou símbolo via Finnhub /search. Nunca lança
    exceção — devolve lista vazia se a pesquisa falhar (ex: sem rede, key inválida).

    Para instrumentos cross-listados em várias bolsas (comum em ETFs UCITS
    europeus - ex: um único fundo listado em 8+ bolsas), a Finnhub devolve
    todas as listagens misturadas, o que dificulta escolher a certa. Prioriza-
    se listagens sem sufixo de bolsa (tipicamente EUA, mais prováveis de ter
    cotação/histórico disponível nos fornecedores usados, Finnhub/Twelve Data)
    antes das restantes, e devolve-se `market_hint` para o frontend mostrar
    a bolsa de cada opção."""
    query = query.strip()
    if not query:
        return []
    try:
        data = await _finnhub_get("search", {"q": query})
    except Exception:
        logger.warning("Pesquisa de tickers falhou para '%s'", query, exc_info=True)
        return []
    out = []
    for r in data.get("result") or []:
        symbol = r.get("symbol")
        if not symbol:
            continue
        out.append({
            "ticker": symbol,
            "name": r.get("description"),
            "type": r.get("type"),
            "market_hint": _market_hint_from_ticker(symbol),
        })
    out.sort(key=lambda r: ("." in r["ticker"], r["ticker"]))
    return out[:limit]


def _looks_like_etf_hint(asset_type_hint: str | None) -> bool:
    """Normaliza o campo `type` da Finnhub /search para saber se a pesquisa
    já identificou o instrumento como fundo. "ETP" (Exchange Traded Product)
    é o valor que a Finnhub devolve tipicamente para ETFs UCITS europeus
    (ver test_search_tickers_prioritizes_listings_without_exchange_suffix,
    ex: VWCE.DE) - "ETF" também aparece para fundos americanos."""
    if not asset_type_hint:
        return False
    normalized = asset_type_hint.lower()
    return "etf" in normalized or "etp" in normalized


async def validate_and_create_stock(
    db: AsyncSession, ticker: str, asset_type_hint: str | None = None,
) -> Stock | None:
    """Devolve a stock existente ou cria-a.

    Sem `asset_type_hint`: tenta validar/enriquecer via Finnhub - primeiro
    como acção (stock/profile2); se essa vier vazia (símbolo não é uma
    acção), tenta como ETF (etf/profile) antes de desistir. Se algum pedido
    falhar (rede, rate limit, key inválida) aceita o ticker na mesma sem
    metadados — só rejeita quando a Finnhub responde com sucesso a dizer que
    o símbolo não existe em nenhum dos dois formatos.

    Com `asset_type_hint` a indicar ETF (campo `type` da Finnhub /search,
    quando o ticker vem dos resultados de pesquisa - ver TickerSearchResult):
    salta o stock/profile2 (que seria sempre vazio para um ETF, uma chamada
    desperdiçada) e, sobretudo, ACEITA o ticker mesmo que o etf/profile não
    tenha dados nenhuns - bug real corrigido em 2026-07-24: ETFs UCITS
    europeus fora da cobertura do plano gratuito da Finnhub (ex: VUSA.F)
    ficavam de fora mesmo sendo tickers válidos, só porque nem stock/profile2
    nem etf/profile tinham metadados para eles. A pesquisa já sabe que é um
    ETF real - não faz sentido voltar a exigir prova disso ao profile."""
    ticker = ticker.upper().strip()
    if not ticker:
        return None
    existing = (await db.execute(select(Stock).where(Stock.ticker == ticker))).scalar_one_or_none()
    if existing:
        return existing

    hint_is_etf = _looks_like_etf_hint(asset_type_hint)
    asset_type = "etf" if hint_is_etf else "stock"
    profile: dict | None = None

    if not hint_is_etf:
        try:
            profile = await _finnhub_get("stock/profile2", {"symbol": ticker})
        except Exception:
            logger.warning(
                "Finnhub indisponível a validar '%s' — a adicionar sem metadados por agora",
                ticker, exc_info=True,
            )
            profile = None

    if hint_is_etf or (profile is not None and not profile):
        # Não é uma acção reconhecida (ou já sabemos pela pesquisa que é um
        # ETF) - tenta como ETF antes de rejeitar.
        try:
            etf_data = await _finnhub_get("etf/profile", {"symbol": ticker})
        except Exception:
            logger.warning(
                "Finnhub indisponível a validar '%s' como ETF — a adicionar sem metadados por agora",
                ticker, exc_info=True,
            )
            etf_data = None
        # Nomes de campos do /etf/profile não confirmados com payload real
        # (ao contrário de stock/profile2 e stock/metric, ver topo do
        # ficheiro) - a documentação pública da Finnhub sugere a forma
        # {"profile": {...}}. Se 'name'/'currency' vierem sempre vazios
        # para ETFs válidos, confirmar o formato real e ajustar aqui.
        etf_profile = (etf_data.get("profile") or etf_data) if etf_data else {}
        if etf_profile:
            profile = etf_profile
            asset_type = "etf"
        elif hint_is_etf:
            profile = None  # aceita sem metadados - a pesquisa já confirmou que é um ETF
        else:
            return None  # nem acção nem ETF - símbolo não existe

    profile = profile or {}
    stock = Stock(
        ticker=ticker,
        name=profile.get("name"),
        exchange=profile.get("exchange"),
        sector=profile.get("finnhubIndustry"),
        currency=profile.get("currency"),
        asset_type=asset_type,
    )
    db.add(stock)
    await db.flush()
    return stock


async def _backfill_profile(db: AsyncSession, stock: Stock) -> None:
    """Tenta preencher nome/exchange/sector/currency em falta (acção ou ETF,
    mesmo fallback de validate_and_create_stock).

    Cobre o caso em que `validate_and_create_stock` aceitou o ticker sem
    metadados (Finnhub indisponível/rate-limited nesse momento) — sem isto o
    nome ficava None para sempre. No-op assim que o nome já estiver definido
    (só uma tentativa de Finnhub por stock, não a cada refresh)."""
    if stock.name is not None:
        return
    try:
        profile = await _finnhub_get("stock/profile2", {"symbol": stock.ticker})
    except Exception:
        logger.warning(
            "Finnhub indisponível a preencher perfil de %s — tenta-se novamente mais tarde",
            stock.ticker, exc_info=True,
        )
        return

    asset_type = "stock"
    if not profile:
        try:
            etf_data = await _finnhub_get("etf/profile", {"symbol": stock.ticker})
        except Exception:
            logger.warning(
                "Finnhub indisponível a preencher perfil de %s como ETF — tenta-se novamente mais tarde",
                stock.ticker, exc_info=True,
            )
            return
        profile = (etf_data.get("profile") or etf_data) if etf_data else {}
        asset_type = "etf"

    if not profile:
        return
    stock.name = profile.get("name")
    stock.exchange = profile.get("exchange")
    stock.sector = profile.get("finnhubIndustry")
    stock.currency = profile.get("currency")
    stock.asset_type = asset_type
    await db.flush()


async def ensure_fresh(db: AsyncSession, stock: Stock) -> None:
    """Atualiza snapshots se o mais recente tiver mais de FRESHNESS_DAYS, OU se
    ainda não houver histórico suficiente (< MIN_HISTORY_ROWS). Com histórico
    já suficiente e recente, ainda assim tenta atualizar a cotação de hoje
    (sujeito a QUOTE_REFRESH_COOLDOWN, bem mais curto) - ver bug real: o preço
    mostrado ficava congelado no valor da 1ª consulta do dia e não refletia
    quedas/subidas intradiárias (ex: GOOG a cair ~6% e a app continuar a
    mostrar o preço de abertura até ao dia seguinte).

    A condição de histórico insuficiente é necessária por si só: uma ação com
    um snapshot de hoje (via Finnhub /quote) mas cujo backfill de 365 dias
    nunca teve sucesso (ex: symbol não reconhecido pela Twelve Data, ver
    _alt_ticker_symbol) tinha sempre `latest` = hoje, logo ficava "fresca" para
    sempre e nunca mais tentava o backfill outra vez.

    Um ticker que os provedores rejeitam de forma permanente (ex: fora de
    cobertura do plano gratuito - ver VUSA.F) nunca acumula PriceSnapshot
    rows, logo nunca satisfaz `count >= MIN_HISTORY_ROWS` e cai sempre no ramo
    de backfill abaixo, gated por BACKFILL_RETRY_COOLDOWN (protege a quota
    partilhada da Twelve Data/Finnhub) - nunca chega a tentar o refresh de
    cotação a cada 15min, que só se aplica a ações já com histórico OK.

    Fundamentais (refresh_fundamentals) são sempre tentados, em ambos os
    ramos - bug real corrigido em 2026-07-23: antes só corriam dentro do ramo
    de backfill abaixo, que uma ação madura (histórico já suficiente) nunca
    mais volta a percorrer, deixando P/E, ROE, margens, etc. congelados no
    valor da primeira vez que a ação foi adicionada. refresh_fundamentals tem
    o seu próprio cooldown interno (FUNDAMENTALS_RETRY_COOLDOWN), por isso
    chamá-lo sempre aqui é seguro/barato."""
    await _backfill_profile(db, stock)
    latest = (
        await db.execute(
            select(func.max(PriceSnapshot.date)).where(PriceSnapshot.stock_id == stock.id)
        )
    ).scalar_one_or_none()
    count = (
        await db.execute(
            select(func.count()).select_from(PriceSnapshot).where(PriceSnapshot.stock_id == stock.id)
        )
    ).scalar_one()
    today = datetime.now(timezone.utc).date()
    is_recent = latest is not None and (today - latest) <= timedelta(days=FRESHNESS_DAYS)

    if is_recent and count >= MIN_HISTORY_ROWS:
        existing_dates = set(
            (await db.execute(
                select(PriceSnapshot.date).where(PriceSnapshot.stock_id == stock.id)
            )).scalars().all()
        )
        await _record_latest_quote(db, stock, existing_dates)
        await refresh_fundamentals(db, stock)
        return

    last_attempt = _as_utc(stock.last_backfill_attempt_at)
    if last_attempt is not None and datetime.now(timezone.utc) - last_attempt < BACKFILL_RETRY_COOLDOWN:
        return

    stock.last_backfill_attempt_at = datetime.now(timezone.utc)
    await refresh_prices(db, stock)
    await refresh_fundamentals(db, stock)


async def refresh_prices(db: AsyncSession, stock: Stock) -> int:
    """Garante histórico suficiente (Twelve Data, só quando ainda faltam dados)
    e regista o preço mais recente do dia (Finnhub /quote)."""
    existing_dates = set(
        (await db.execute(
            select(PriceSnapshot.date).where(PriceSnapshot.stock_id == stock.id)
        )).scalars().all()
    )
    inserted = 0
    if len(existing_dates) < MIN_HISTORY_ROWS:
        inserted += await _backfill_history(db, stock, existing_dates)
    inserted += await _record_latest_quote(db, stock, existing_dates)
    return inserted


def _alt_ticker_symbol(ticker: str) -> str | None:
    """Símbolo alternativo a tentar quando um fornecedor não reconhece o
    ticker tal como está guardado - cobre ações de classes distintas (ex:
    Berkshire Hathaway classe B: Finnhub costuma aceitar 'BRK.B' ou 'BRK-B',
    mas a Twelve Data pode só reconhecer um dos dois formatos). O ticker é
    validado/criado via Finnhub (validate_and_create_stock), por isso pode
    ficar guardado num formato que a Twelve Data não entende, mesmo vindo da
    pesquisa - sem isto, uma ação assim ficava com histórico insuficiente
    indefinidamente (só 1 snapshot/dia via Finnhub /quote, nunca o backfill
    de 365 dias)."""
    if "." in ticker:
        return ticker.replace(".", "-")
    if "-" in ticker:
        return ticker.replace("-", ".")
    return None


# Sufixo de bolsa da Finnhub (ex: 'VUSA.F') -> mic_code ISO 10383 que a
# Twelve Data espera como parâmetro à parte (confirmado na documentação da
# Twelve Data: time_series aceita symbol + mic_code, ex: 'AAPL' + 'XNAS' -
# ver https://twelvedata.com/docs). A Finnhub cola o sufixo ao símbolo; a
# Twelve Data não entende esse formato, por isso um ticker assim ficava sem
# histórico mesmo depois do fallback ponto/hífen acima (esse só cobre classes
# de ações tipo BRK.B, não sufixos de bolsa).
#
# Só cobre as bolsas europeias mais relevantes e sem ambiguidade razoável no
# sufixo - de propósito não inclui sufixos de bolsas regionais alemãs mais
# pequenas (Estugarda, Hamburgo, Munique, Berlim, Dusseldorf) porque não há
# confirmação de que o sufixo da Finnhub corresponda de forma unívoca a essas
# praças, e devolver dados da bolsa errada é pior do que não devolver nada.
_TICKER_SUFFIX_MIC_CODES: dict[str, str] = {
    "L": "XLON",   # Londres
    "F": "XFRA",   # Frankfurt
    "DE": "XETR",  # Xetra (Alemanha)
    "PA": "XPAR",  # Paris (Euronext)
    "AS": "XAMS",  # Amesterdão (Euronext)
    "BR": "XBRU",  # Bruxelas (Euronext)
    "LS": "XLIS",  # Lisboa (Euronext)
    "MI": "XMIL",  # Milão (Borsa Italiana)
    "MC": "XMAD",  # Madrid (BME)
    "SW": "XSWX",  # Suíça (SIX)
    "TO": "XTSE",  # Toronto
    "HK": "XHKG",  # Hong Kong
    "AX": "XASX",  # Austrália (ASX)
}


def _split_ticker_suffix(ticker: str) -> tuple[str, str | None]:
    """'VUSA.F' -> ('VUSA', 'F'); 'AAPL' -> ('AAPL', None)."""
    if "." not in ticker:
        return ticker, None
    base, suffix = ticker.rsplit(".", 1)
    return base, suffix.upper()


async def _fetch_time_series_values(symbol: str, mic_code: str | None = None) -> list | None:
    params = {"symbol": symbol, "interval": "1day", "outputsize": "365"}
    if mic_code:
        params["mic_code"] = mic_code
    try:
        data = await _twelvedata_get("time_series", params)
    except Exception:
        logger.warning("Twelve Data indisponível a preencher histórico de %s", symbol, exc_info=True)
        return None
    return data.get("values") if isinstance(data, dict) else None


async def _backfill_history(db: AsyncSession, stock: Stock, existing_dates: set[date]) -> int:
    values = await _fetch_time_series_values(stock.ticker)
    if not values:
        alt = _alt_ticker_symbol(stock.ticker)
        if alt:
            values = await _fetch_time_series_values(alt)
    if not values:
        base, suffix = _split_ticker_suffix(stock.ticker)
        mic_code = _TICKER_SUFFIX_MIC_CODES.get(suffix) if suffix else None
        if mic_code:
            values = await _fetch_time_series_values(base, mic_code=mic_code)
    if not values:
        return 0
    inserted = 0
    for row in values:
        try:
            d = datetime.strptime(row["datetime"], "%Y-%m-%d").date()
        except (KeyError, ValueError):
            continue
        if d in existing_dates:
            continue
        db.add(PriceSnapshot(
            stock_id=stock.id, date=d,
            open=_dec(row.get("open")), high=_dec(row.get("high")),
            low=_dec(row.get("low")), close=_dec(row.get("close")),
            volume=_int(row.get("volume")),
        ))
        existing_dates.add(d)
        inserted += 1
    await db.flush()
    return inserted


async def _record_latest_quote(db: AsyncSession, stock: Stock, existing_dates: set[date]) -> int:
    """Regista/atualiza o snapshot de PREÇO de hoje via Finnhub /quote.

    Se já houver um snapshot de hoje (ex: criado mais cedo pelo job diário às
    6h UTC), atualiza-o com o preço mais recente em vez de o deixar congelado
    - sem isto, uma queda/subida intradiária (ex: GOOG a cair ~6%) nunca
    aparecia na app até ao dia seguinte. Sujeito a QUOTE_REFRESH_COOLDOWN via
    `stock.last_quote_at`, registado por tentativa (sucesso ou falha) para não
    martelar a Finnhub a cada visita à página."""
    last_quote = _as_utc(stock.last_quote_at)
    if last_quote is not None and datetime.now(timezone.utc) - last_quote < QUOTE_REFRESH_COOLDOWN:
        return 0
    stock.last_quote_at = datetime.now(timezone.utc)

    try:
        quote = await _finnhub_get("quote", {"symbol": stock.ticker})
    except Exception:
        logger.warning("Finnhub indisponível a obter cotação de %s", stock.ticker, exc_info=True)
        return 0
    price = quote.get("c") if isinstance(quote, dict) else None
    if not price:
        return 0

    today = datetime.now(timezone.utc).date()
    if today in existing_dates:
        row = (
            await db.execute(
                select(PriceSnapshot).where(PriceSnapshot.stock_id == stock.id, PriceSnapshot.date == today)
            )
        ).scalar_one_or_none()
        if row is None:
            return 0
        row.close = _dec(price)
        high = _dec(quote.get("h"))
        if high is not None and (row.high is None or high > row.high):
            row.high = high
        low = _dec(quote.get("l"))
        if low is not None and (row.low is None or low < row.low):
            row.low = low
        await db.flush()
        return 0
    db.add(PriceSnapshot(
        stock_id=stock.id, date=today,
        open=_dec(quote.get("o")), high=_dec(quote.get("h")),
        low=_dec(quote.get("l")), close=_dec(price), volume=None,
    ))
    existing_dates.add(today)
    await db.flush()
    return 1


async def refresh_fundamentals(db: AsyncSession, stock: Stock) -> None:
    """Regista os fundamentais de hoje (Finnhub /stock/metric), uma vez por
    dia por ação (`existing` abaixo). Chamado sempre que ensure_fresh corre -
    incluindo para ações já com histórico de preço suficiente - para que P/E,
    ROE, margens, etc. continuem a atualizar-se (ex: após resultados
    trimestrais) em vez de ficarem congeladas no valor da primeira vez que a
    ação foi adicionada (bug real corrigido em 2026-07-23).

    FUNDAMENTALS_RETRY_COOLDOWN protege contra um símbolo que a Finnhub
    rejeita sempre (ex: sem cobertura de fundamentais, ou fora do plano
    gratuito) - sem isto, sem nunca haver `existing`, tentava-se de novo em
    TODA a visita à página."""
    if stock.asset_type == "etf":
        # /stock/metric é orientado a acções - a Finnhub devolve sempre vazio
        # para ETFs, por isso nem vale a pena gastar o pedido.
        return
    today = datetime.now(timezone.utc).date()
    existing = (
        await db.execute(select(FundamentalsSnapshot).where(
            FundamentalsSnapshot.stock_id == stock.id, FundamentalsSnapshot.date == today
        ))
    ).scalar_one_or_none()
    if existing:
        return
    last_attempt = _as_utc(stock.last_fundamentals_attempt_at)
    if last_attempt is not None and datetime.now(timezone.utc) - last_attempt < FUNDAMENTALS_RETRY_COOLDOWN:
        return
    stock.last_fundamentals_attempt_at = datetime.now(timezone.utc)
    try:
        data = await _finnhub_get("stock/metric", {"symbol": stock.ticker, "metric": "all"})
    except Exception:
        logger.warning("Finnhub indisponível a obter fundamentais de %s", stock.ticker, exc_info=True)
        return
    metric = data.get("metric") if isinstance(data, dict) else None
    if not metric:
        return
    pe = metric.get("peTTM") or metric.get("peBasicExclExtraTTM") or metric.get("peNormalizedAnnual")
    dividend_yield = metric.get("currentDividendYieldTTM") or metric.get("dividendYieldIndicatedAnnual")
    market_cap = metric.get("marketCapitalization")
    db.add(FundamentalsSnapshot(
        stock_id=stock.id, date=today,
        pe_ratio=_dec(pe),
        eps=_dec(metric.get("epsTTM") or metric.get("epsBasicExclExtraItemsTTM")),
        debt_to_equity=_dec(metric.get("totalDebt/totalEquityAnnual")),
        # Finnhub devolve o yield em percentagem (ex: 0.65 = 0.65%); guardamos como fração.
        dividend_yield=_dec(dividend_yield / 100 if dividend_yield is not None else None),
        market_cap=int(market_cap * 1_000_000) if market_cap else None,
        # Estes quatro já vêm em percentagem/rácio direto da Finnhub, sem
        # conversão (ex: revenueGrowthTTMYoy=12.3 significa 12.3%).
        revenue_growth=_dec(metric.get("revenueGrowthTTMYoy") or metric.get("revenueGrowth3Y")),
        net_margin=_dec(metric.get("netProfitMarginTTM") or metric.get("netProfitMarginAnnual")),
        # "roeAnnual" não existe no payload real (confirmado 2026-07-23,
        # MSFT) - "roeRfy" (rolling four-year) é o fallback real mais próximo.
        roe=_dec(metric.get("roeTTM") or metric.get("roeRfy")),
        current_ratio=_dec(metric.get("currentRatioAnnual") or metric.get("currentRatioQuarterly")),
        # Confirmados com payload real (MSFT, 2026-07-23) - mesma convenção
        # de percentagem direta dos quatro campos acima.
        gross_margin=_dec(metric.get("grossMarginTTM") or metric.get("grossMarginAnnual")),
        operating_margin=_dec(metric.get("operatingMarginTTM") or metric.get("operatingMarginAnnual")),
        eps_growth=_dec(metric.get("epsGrowthTTMYoy") or metric.get("epsGrowth3Y")),
        dividend_growth_5y=_dec(metric.get("dividendGrowthRate5Y")),
    ))
    await db.flush()


async def get_price_history(db: AsyncSession, stock_id: uuid.UUID, days: int = 90) -> list[PriceSnapshot]:
    """Últimos `days` snapshots de preço (ordem cronológica ascendente), para
    gráficos/sparklines. Usado na página de detalhe da ação."""
    rows = (
        await db.execute(
            select(PriceSnapshot)
            .where(PriceSnapshot.stock_id == stock_id, PriceSnapshot.close.is_not(None))
            .order_by(PriceSnapshot.date.desc())
            .limit(days)
        )
    ).scalars().all()
    return list(reversed(rows))


async def get_price_change(db: AsyncSession, stock_id: uuid.UUID) -> tuple[Decimal | None, Decimal | None]:
    """Devolve (último fecho, variação % face ao fecho anterior). Usado para o
    "day change" colorido no Overview/Watchlist — independente de quando a
    última avaliação correu, ao contrário de `price_at_evaluation`."""
    rows = (
        await db.execute(
            select(PriceSnapshot.close)
            .where(PriceSnapshot.stock_id == stock_id, PriceSnapshot.close.is_not(None))
            .order_by(PriceSnapshot.date.desc())
            .limit(2)
        )
    ).scalars().all()
    if not rows:
        return None, None
    last = rows[0]
    if len(rows) < 2 or not rows[1]:
        return last, None
    previous = rows[1]
    if previous == 0:
        return last, None
    change_pct = (last - previous) / previous * 100
    return last, Decimal(str(round(float(change_pct), 4)))


async def get_latest_fundamentals(db: AsyncSession, stock_id: uuid.UUID) -> FundamentalsSnapshot | None:
    """Snapshot de fundamentais mais recente conhecido para a ação. Usado no
    backtest/otimizador (backtest_core.py), que trata os fundamentais como
    constantes ao longo de todo o período simulado — a app só guarda o
    snapshot mais recente, não um histórico diário de fundamentais."""
    return (
        await db.execute(
            select(FundamentalsSnapshot).where(FundamentalsSnapshot.stock_id == stock_id)
            .order_by(FundamentalsSnapshot.date.desc()).limit(1)
        )
    ).scalar_one_or_none()


def _dec(value) -> Decimal | None:
    if value is None:
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    if value != value:  # NaN
        return None
    return Decimal(str(round(value, 6)))


def _int(value) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None
