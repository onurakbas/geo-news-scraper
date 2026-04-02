"""
Pydantic response schemas for the News API.

Separated from DB models (models/news.py) to keep API contract
independent from the internal storage representation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Shared sub-models ─────────────────────────────────────────────────────────

class CoordinatesSchema(BaseModel):
    """GeoJSON Point coordinates."""
    type: str = "Point"
    coordinates: list[float]  # [longitude, latitude]


# ── News list & detail ────────────────────────────────────────────────────────

class NewsItemOut(BaseModel):
    """
    Single news item returned by the list endpoint.
    `sources` contains all source labels for deduplicated groups.
    """
    id: str = Field(alias="_id")
    title: str
    published_at: Optional[datetime] = None
    type: Optional[str] = None
    district: Optional[str] = None
    city: Optional[str] = None
    coordinates: Optional[CoordinatesSchema] = None
    sources: list[str] = Field(
        default_factory=list,
        description="All source site labels sharing the same similarity_group_id.",
    )
    urls: list[str] = Field(
        default_factory=list,
        description="All article URLs sharing the same similarity_group_id.",
    )
    similarity_group_id: Optional[str] = None

    model_config = {"populate_by_name": True}


class NewsListResponse(BaseModel):
    items: list[NewsItemOut]
    total: int
    page: int
    page_size: int


# ── Map markers ───────────────────────────────────────────────────────────────

class MarkerOut(BaseModel):
    """Lightweight payload for a single map marker pin."""
    id: str = Field(alias="_id")
    title: str
    published_at: Optional[datetime] = None
    type: Optional[str] = None
    district: Optional[str] = None
    neighborhood: Optional[str] = None
    lat: float  # extracted from GeoJSON coordinates[1]
    lon: float  # extracted from GeoJSON coordinates[0]
    sources: list[str] = Field(default_factory=list)
    urls: list[str] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class MarkersResponse(BaseModel):
    markers: list[MarkerOut]
    total: int


# ── Filters ───────────────────────────────────────────────────────────────────

class FiltersResponse(BaseModel):
    types: list[str]
    districts: list[str]
