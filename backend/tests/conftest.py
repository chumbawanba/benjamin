"""Fixtures pytest. BD de teste: SQLite em memoria (aiosqlite).

NOTA: os modelos usam UUID do dialeto postgres; SQLAlchemy mapeia para CHAR(32)
em SQLite automaticamente com as_uuid=True.
Finnhub/Twelve Data SAO SEMPRE mockados - nunca chamados nos testes.
"""
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.database as database_module
from app.database import Base
from app.models import FundamentalsSnapshot, PriceSnapshot, Stock, User
from app.security import hash_password


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    maker = async_sessionmaker(db_engine, expire_on_commit=False)
    async with maker() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_engine, monkeypatch):
    """Cliente HTTP com a BD de teste injetada e scheduler desligado."""
    maker = async_sessionmaker(db_engine, expire_on_commit=False)
    monkeypatch.setattr(database_module, "SessionLocal", maker)
    monkeypatch.setattr(database_module, "engine", db_engine)

    from app.config import settings
    monkeypatch.setattr(settings, "scheduler_enabled", False)
    monkeypatch.setattr(settings, "allow_registration", True)

    from app.main import app
    from app.database import get_db

    async def override_get_db():
        async with maker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test/api/v1") as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def user_a(db_session):
    user = User(email="a@test.dev", password_hash=hash_password("password-a"))
    db_session.add(user)
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def user_b(db_session):
    user = User(email="b@test.dev", password_hash=hash_password("password-b"))
    db_session.add(user)
    await db_session.commit()
    return user


async def login(client, email, password):
    resp = await client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest_asyncio.fixture
async def seeded_stock(db_session):
    """Stock AAPL com 60 dias de precos sinteticos + fundamentais (sem yfinance)."""
    stock = Stock(ticker="AAPL", name="Apple Inc.", currency="USD")
    db_session.add(stock)
    await db_session.flush()
    today = datetime.now(timezone.utc).date()
    price = 150.0
    for i in range(60, 0, -1):
        price += 0.5  # tendencia ascendente estavel
        db_session.add(PriceSnapshot(
            stock_id=stock.id, date=today - timedelta(days=i),
            open=Decimal(str(price)), high=Decimal(str(price + 1)),
            low=Decimal(str(price - 1)), close=Decimal(str(price)), volume=1000,
        ))
    db_session.add(FundamentalsSnapshot(
        stock_id=stock.id, date=today, pe_ratio=Decimal("12.0"),
        dividend_yield=Decimal("0.005"),
    ))
    await db_session.commit()
    return stock


def mock_market_data_valid(ticker_name="Apple Inc."):
    """Patch de _finnhub_get devolvendo um perfil valido, sem tocar na rede."""
    profile = {
        "name": ticker_name, "currency": "USD",
        "exchange": "NASDAQ", "finnhubIndustry": "Technology",
    }
    return patch("app.services.market_data._finnhub_get", new=AsyncMock(return_value=profile))
