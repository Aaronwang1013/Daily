from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import os
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

from .database import engine, Base
from .routers import aws, calendar, summary, news, investment

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all tables on startup
    Base.metadata.create_all(bind=engine)

    # Start APScheduler — daily RSS fetch at 08:00 Asia/Taipei
    scheduler = BackgroundScheduler(timezone=pytz.timezone("Asia/Taipei"))
    from .services.news_fetcher import run_fetch_job
    scheduler.add_job(
        run_fetch_job,
        trigger=CronTrigger(hour=8, minute=0, timezone=pytz.timezone("Asia/Taipei")),
        id="daily_rss_fetch",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # Seed default watchlist and schedule stock data refresh
    from .services.stock_fetcher import seed_default_watchlist, run_stock_refresh
    seed_default_watchlist()
    scheduler.add_job(
        run_stock_refresh,
        trigger=CronTrigger(
            day_of_week="mon-fri",
            hour="9,10,11,12,13,14,15,16,21,22,23",
            minute=0,
            timezone=pytz.timezone("Asia/Taipei"),
        ),
        id="stock_refresh",
        replace_existing=True,
        misfire_grace_time=900,
    )

    scheduler.start()
    logger.info("APScheduler started — daily RSS fetch at 08:00 Asia/Taipei, stock refresh on weekdays")

    yield

    scheduler.shutdown(wait=False)
    logger.info("APScheduler stopped")


app = FastAPI(
    title="Aaron's Dashboard API",
    version="1.0.0",
    lifespan=lifespan,
)

# ── Register routers ──
app.include_router(aws.router)
app.include_router(calendar.router)
app.include_router(summary.router)
app.include_router(news.router)
app.include_router(investment.router)

# ── Serve static frontend ──
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", include_in_schema=False)
async def root():
    return FileResponse(os.path.join(static_dir, "index.html"))


@app.get("/health")
def health():
    return {"status": "ok"}
