"""
News endpoints – list, detail, filters, and map markers.
Business logic lives in the repository layer (db/repositories/news_repository.py).
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.client import get_database
from app.db.repositories import news_repository
from app.api.v1.schemas import (
    FiltersResponse,
    MarkersResponse,
    MarkerOut,
    NewsListResponse,
    NewsItemOut,
)

router = APIRouter()


# ── GET /news ─────────────────────────────────────────────────────────────────

@router.get("", response_model=NewsListResponse, summary="List news articles")
async def list_news(
    date_from: Optional[str] = Query(
        default=None, description="Filter from date (ISO 8601), e.g. 2024-01-01"
    ),
    date_to: Optional[str] = Query(
        default=None, description="Filter to date (ISO 8601), e.g. 2024-12-31"
    ),
    type: Optional[str] = Query(
        default=None, description="Category filter (one of the 5 mandatory types)"
    ),
    district: Optional[str] = Query(
        default=None, description="Kocaeli district name, e.g. İzmit"
    ),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> NewsListResponse:
    """
    Return a paginated list of news articles.

    - Filters by the 5 mandatory categories only (excludes 'Diğer').
    - Deduplicated articles are grouped: their sources and urls are merged
      into arrays so the frontend can display all origin sites.
    """
    items, total = await news_repository.get_news_list(
        db,
        date_from=date_from,
        date_to=date_to,
        type_filter=type,
        district=district,
        page=page,
        page_size=page_size,
    )

    news_items = [NewsItemOut(**item) for item in items]

    return NewsListResponse(
        items=news_items,
        total=total,
        page=page,
        page_size=page_size,
    )


# ── GET /filters ──────────────────────────────────────────────────────────────

@router.get("/filters", response_model=FiltersResponse, summary="Get filter options")
async def get_filters(
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> FiltersResponse:
    """
    Return distinct values for type and district dropdown menus.
    Only includes the 5 mandatory categories.
    """
    options = await news_repository.get_filter_options(db)
    return FiltersResponse(**options)


# ── GET /map/markers ──────────────────────────────────────────────────────────

@router.get(
    "/map/markers",
    response_model=MarkersResponse,
    summary="Get map marker data",
)
async def get_map_markers(
    date_from: Optional[str] = Query(default=None, description="Filter from date (ISO 8601)"),
    date_to: Optional[str] = Query(default=None, description="Filter to date (ISO 8601)"),
    type: Optional[str] = Query(default=None, description="Category filter"),
    district: Optional[str] = Query(default=None, description="District filter"),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> MarkersResponse:
    """
    Return lightweight marker objects for all geocoded articles.
    No pagination – client-side clustering is used for large sets.
    Only articles with coordinates are included.
    """
    markers_raw = await news_repository.get_map_markers(
        db,
        date_from=date_from,
        date_to=date_to,
        type_filter=type,
        district=district,
    )

    markers = [MarkerOut(**m) for m in markers_raw]

    return MarkersResponse(markers=markers, total=len(markers))


# ── GET /news/{news_id} ───────────────────────────────────────────────────────

@router.get("/{news_id}", summary="Get single news article")
async def get_news_detail(
    news_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> dict:
    """Return full detail for a single news item by its MongoDB _id."""
    doc = await news_repository.get_news_by_id(db, news_id)
    if not doc:
        raise HTTPException(status_code=404, detail="News article not found.")
    return doc
