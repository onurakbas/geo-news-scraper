"""
Top-level v1 router – sub-routers for each resource are registered here.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import news

api_router = APIRouter()

api_router.include_router(news.router, prefix="/news", tags=["news"])
