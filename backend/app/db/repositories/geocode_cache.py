"""
Repository layer for the geocode_cache collection.

Provides thin wrappers around raw pymongo operations so that higher-level
service code never touches the collection directly.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import pymongo
from loguru import logger


class GeocodeCacheRepository:
    """Sync (pymongo) repository for the geocode_cache collection."""

    def __init__(self, db: pymongo.database.Database) -> None:  # type: ignore[type-arg]
        self._col = db["geocode_cache"]

    # ── Read ──────────────────────────────────────────────────────────────

    def find_by_address(self, address: str) -> Optional[dict]:
        """Return cached document for *address*, or None on miss."""
        return self._col.find_one({"address": address})

    # ── Write ─────────────────────────────────────────────────────────────

    def upsert(
        self,
        address: str,
        lat: float,
        lng: float,
        formatted_address: str,
    ) -> None:
        """Insert or replace a geocode result keyed on *address*."""
        doc = {
            "address": address,
            "lat": lat,
            "lng": lng,
            "formatted_address": formatted_address,
            "cached_at": datetime.now(timezone.utc),
        }
        result = self._col.update_one(
            {"address": address},
            {"$set": doc},
            upsert=True,
        )
        if result.upserted_id:
            logger.debug(f"[cache] Inserted new entry for '{address}'")
        else:
            logger.debug(f"[cache] Updated existing entry for '{address}'")

    # ── Stats ─────────────────────────────────────────────────────────────

    def count(self) -> int:
        """Return total number of cached entries."""
        return self._col.count_documents({})
