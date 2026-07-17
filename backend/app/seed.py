"""Seed de dev: python -m app.seed"""
import asyncio
from decimal import Decimal

from sqlalchemy import select

from app.database import SessionLocal
from app.models import StrategyItem, StrategyTemplate, User
from app.security import hash_password
from app.services import market_data

TICKERS = ["AAPL", "MSFT", "GALP.LS"]


async def seed():
    async with SessionLocal() as db:
        user = (await db.execute(select(User).where(User.email == "demo@benjamin.dev"))).scalar_one_or_none()
        if user is None:
            user = User(email="demo@benjamin.dev", name="Demo", password_hash=hash_password("demo1234"))
            db.add(user)
            await db.flush()

        template = StrategyTemplate(user_id=user.id, name="Value simples",
                                    description="Exemplo do SPEC secção 6")
        db.add(template)
        await db.flush()
        db.add_all([
            StrategyItem(template_id=template.id, name="RSI sobrevendido", metric="RSI_14",
                         operator="<", threshold_value=Decimal("30"), weight=Decimal("2"),
                         direction="buy_signal", category="technical"),
            StrategyItem(template_id=template.id, name="P/E barato", metric="PE_RATIO",
                         operator="<", threshold_value=Decimal("15"), weight=Decimal("1"),
                         direction="buy_signal", category="fundamental"),
            StrategyItem(template_id=template.id, name="RSI sobrecomprado", metric="RSI_14",
                         operator=">", threshold_value=Decimal("70"), weight=Decimal("1"),
                         direction="sell_signal", category="technical"),
        ])

        from app.models import WatchlistItem
        for ticker in TICKERS:
            stock = await market_data.validate_and_create_stock(db, ticker)
            if stock:
                exists = (await db.execute(select(WatchlistItem).where(
                    WatchlistItem.user_id == user.id, WatchlistItem.stock_id == stock.id
                ))).scalar_one_or_none()
                if not exists:
                    db.add(WatchlistItem(user_id=user.id, stock_id=stock.id))
        await db.commit()
        print("Seed concluído: demo@benjamin.dev / demo1234")


if __name__ == "__main__":
    asyncio.run(seed())
