"""
FastAPI application entry point for Geo News Scraper.
Initialises the app, registers routers, and exposes /health endpoint.
"""
import sys
import asyncio

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.api.v1.router import api_router
from app.core.config import settings
from app.db.client import connect_db, disconnect_db, get_database
from app.db.indexes import create_all_indexes
from app.services.scraper.runner import run_spiders_background

# Windows üzerinde paralel subprocess çalıştırmak için şart:
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    await create_all_indexes(get_database())
    # Fire-and-forget: fetch fresh news on every startup
    logger.info("🚀 Server started – launching background scrape...")
    asyncio.create_task(run_spiders_background())
    yield
    await disconnect_db()


app = FastAPI(
    title="Geo News Scraper API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.CORS_ORIGINS) + ["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["health"])
async def health_check() -> dict:
    """Liveness probe – returns 200 when the service is up."""
    return {"status": "ok"}
