"""Pydantic model for the sources collection."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class Source(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    name: str
    base_url: HttpUrl
    spider_name: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"populate_by_name": True}
