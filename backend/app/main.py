from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import settings
from app.database import engine
from app.routers import auth, checklists, evaluations, watchlist
from app.scheduler import weekly_job


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = None
    if settings.scheduler_enabled:
        scheduler = AsyncIOScheduler(timezone="UTC")
        scheduler.add_job(weekly_job, CronTrigger(day_of_week="sat", hour=8, minute=0))
        scheduler.start()
    yield
    if scheduler:
        scheduler.shutdown(wait=False)


app = FastAPI(title="Benjamin", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API = "/api/v1"
app.include_router(auth.router, prefix=API)
app.include_router(watchlist.router, prefix=API)
app.include_router(checklists.router, prefix=API)
app.include_router(evaluations.router, prefix=API)


@app.get("/health")
async def health():
    db_ok = True
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        db_ok = False
    return {"status": "ok", "db": db_ok}
