"""Pydantic model for the geocode_cache collection."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class GeocodeCache(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    # Normalised query string used as cache key (unique index)
    address: str
    # Raw Google Geocoding API response coordinates
    lat: float
    lng: float
    formatted_address: str
    cached_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"populate_by_name": True}
