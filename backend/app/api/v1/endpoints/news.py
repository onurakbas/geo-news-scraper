"""
News endpoints – list, detail, filters, and map markers.
Business logic lives in the service layer, not here (see §5 arch rules).
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.client import get_database

router = APIRouter()


@router.get("")
async def list_news(
    date_from: Optional[str] = Query(default=None, description="ISO date, e.g. 2024-01-01"),
    date_to: Optional[str] = Query(default=None, description="ISO date, e.g. 2024-12-31"),
    type: Optional[str] = Query(default=None),
    district: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> dict:
    """Return a paginated list of news items with optional filters."""
    # TODO: delegate to NewsService
    return {"items": [], "total": 0, "page": page, "page_size": page_size}


@router.get("/filters")
async def get_filters(
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> dict:
    """Return distinct values for type and district dropdowns."""
    # TODO: delegate to NewsService
    return {"types": [], "districts": []}


@router.get("/map/markers")
async def get_map_markers(
    date_from: Optional[str] = Query(default=None),
    date_to: Optional[str] = Query(default=None),
    type: Optional[str] = Query(default=None),
    district: Optional[str] = Query(default=None),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> dict:
    """Return lightweight marker data optimised for map rendering."""
    # TODO: delegate to NewsService
    return {"markers": []}


@router.get("/{news_id}")
async def get_news_detail(
    news_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> dict:
    """Return full detail for a single news item."""
    # TODO: delegate to NewsService
    return {}
