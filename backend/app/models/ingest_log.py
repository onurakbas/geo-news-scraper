"""Pydantic model for the ingest_logs collection."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class IngestLog(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    source_name: str
    started_at: datetime = Field(default_factory=datetime.utcnow)
    finished_at: Optional[datetime] = None
    scraped_count: int = 0
    inserted_count: int = 0
    duplicate_count: int = 0
    error_count: int = 0
    errors: list[str] = Field(default_factory=list)

    model_config = {"populate_by_name": True}
