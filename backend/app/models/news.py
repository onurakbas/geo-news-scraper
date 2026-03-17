"""
Pydantic models for the news collection.
Mirrors the schema defined in copilot-instructions.md §6.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class Coordinates(BaseModel):
    type: str = "Point"
    coordinates: list[float]  # [longitude, latitude]


class NewsBase(BaseModel):
    source: str
    url: HttpUrl
    title: str
    content: str
    published_at: datetime
    type: Optional[str] = None
    district: Optional[str] = None
    city: Optional[str] = None
    locations: list[str] = Field(default_factory=list)
    coordinates: Optional[Coordinates] = None


class NewsInDB(NewsBase):
    id: Optional[str] = Field(default=None, alias="_id")
    embedding: Optional[list[float]] = None
    similarity_group_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"populate_by_name": True}


class NewsOut(NewsBase):
    id: str = Field(alias="_id")

    model_config = {"populate_by_name": True}
