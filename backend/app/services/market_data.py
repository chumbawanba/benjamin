"""Ingestao de dados de mercado via yfinance, com gravacao idempotente."""
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import FundamentalsSnapshot, PriceSnapshot, Stock

FRESHNESS_DAYS = 3
HISTORY_PERIOD = "1y"


def _yf_ticker(ticker: str):
    import yfinance as yf  # import local: facilita mock nos testes
    return yf.Ticker(ticker)


async def validate_and_create_stock(db: AsyncSession, ticker: str) -> Stock | None:
    """Devolve a stock existente ou cria-a validando o ticker via yfinance.
    Devolve None se o ticker nao existir."""
    ticker = ticker.upper().strip()
    existing = (await db.execute(select(Stock).where(Stock.ticker == ticker))).scalar_one_or_none()
    if existing:
        return existing
    try:
        info = _yf_ticker(ticker).info or {}
    except Exception:
        return None
    if not info.get("shortName") and not info.get("longName"):
        return None
    stock = Stock(
        ticker=ticker,
        name=info.get("longName") or info.get("shortName"),
        exchange=info.get("exchange"),
        sector=info.get("sector"),
        currency=info.get("currency"),
    )
    db.add(stock)
    await db.flush()
    return stock


async def ensure_fresh(db: AsyncSession, stock: Stock) -> None:
    """Atualiza snapshots se o mais recente tiver mais de FRESHNESS_DAYS."""
    latest = (
        await db.execute(
            select(func.max(PriceSnapshot.date)).where(PriceSnapshot.stock_id == stock.id)
        )
    ).scalar_one_or_none()
    today = datetime.now(timezone.utc).date()
    if latest is not None and (today - latest) <= timedelta(days=FRESHNESS_DAYS):
        return
    await refresh_prices(db, stock)
    await refresh_fundamentals(db, stock)


async def refresh_prices(db: AsyncSession, stock: Stock) -> int:
    t = _yf_ticker(stock.ticker)
    hist = t.history(period=HISTORY_PERIOD, auto_adjust=True)
    if hist is None or hist.empty:
        return 0
    existing_dates = set(
        (await db.execute(
            select(PriceSnapshot.date).where(PriceSnapshot.stock_id == stock.id)
        )).scalars().all()
    )
    inserted = 0
    for idx, row in hist.iterrows():
        d: date = idx.date()
        if d in existing_dates:
            continue
        db.add(PriceSnapshot(
            stock_id=stock.id, date=d,
            open=_dec(row.get("Open")), high=_dec(row.get("High")),
            low=_dec(row.get("Low")), close=_dec(row.get("Close")),
            volume=int(row["Volume"]) if row.get("Volume") == row.get("Volume") else None,
        ))
        inserted += 1
    await db.flush()
    return inserted


async def refresh_fundamentals(db: AsyncSession, stock: Stock) -> None:
    today = datetime.now(timezone.utc).date()
    existing = (
        await db.execute(select(FundamentalsSnapshot).where(
            FundamentalsSnapshot.stock_id == stock.id, FundamentalsSnapshot.date == today
        ))
    ).scalar_one_or_none()
    if existing:
        return
    try:
        info = _yf_ticker(stock.ticker).info or {}
    except Exception:
        return
    db.add(FundamentalsSnapshot(
        stock_id=stock.id, date=today,
        pe_ratio=_dec(info.get("trailingPE")),
        eps=_dec(info.get("trailingEps")),
        debt_to_equity=_dec(info.get("debtToEquity")),
        dividend_yield=_dec(info.get("dividendYield")),
        market_cap=info.get("marketCap"),
    ))
    await db.flush()


def _dec(value) -> Decimal | None:
    if value is None or value != value:  # NaN check
        return None
    return Decimal(str(round(float(value), 6)))
