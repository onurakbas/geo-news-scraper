"""
Top-level v1 router – sub-routers for each resource are registered here.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import news
from app.api.v1.endpoints import scrape

api_router = APIRouter()

api_router.include_router(news.router, prefix="/news", tags=["news"])
api_router.include_router(scrape.router, prefix="/scrape", tags=["scrape"])
