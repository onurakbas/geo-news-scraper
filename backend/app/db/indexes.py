"""
MongoDB index definitions for all collections.

Run once at startup (called from lifespan in main.py) or manually via:
    python -m app.db.indexes

Collections created here:
  - news          : scraped and de-duplicated news items
  - sources       : registered scrape sources / sites
  - geocode_cache : cached Google Geocoding API responses
  - ingest_logs   : per-run scrape audit trail
"""

import asyncio
from typing import TYPE_CHECKING

from loguru import logger
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, GEOSPHERE, IndexModel, TEXT

if TYPE_CHECKING:
    pass


# ──────────────────────────────────────────────────────────
# Index definitions
# ──────────────────────────────────────────────────────────

NEWS_INDEXES: list[IndexModel] = [
    # URL must be globally unique – primary duplicate guard
    IndexModel([("url", ASCENDING)], unique=True, name="url_unique"),
    # Time-range queries (most common filter)
    IndexModel([("published_at", DESCENDING)], name="published_at_desc"),
    # Filter by news type (e.g. "crime", "traffic", "fire")
    IndexModel([("type", ASCENDING)], name="type_asc"),
    # Filter by district
    IndexModel([("district", ASCENDING)], name="district_asc"),
    # Geo-spatial queries – required for 2dsphere operators ($near, $geoWithin)
    IndexModel([("coordinates", GEOSPHERE)], name="coordinates_2dsphere"),
    # Compound index for the most frequent API query pattern
    IndexModel(
        [("published_at", DESCENDING), ("type", ASCENDING), ("district", ASCENDING)],
        name="published_type_district",
    ),
    # Full-text search on title + content (optional but useful for keyword filter)
    IndexModel([("title", TEXT), ("content", TEXT)], name="text_search"),
    # Similarity group lookup
    IndexModel([("similarity_group_id", ASCENDING)], name="similarity_group_asc"),
]

SOURCES_INDEXES: list[IndexModel] = [
    # Source base-URL must be unique
    IndexModel([("base_url", ASCENDING)], unique=True, name="base_url_unique"),
    IndexModel([("name", ASCENDING)], name="name_asc"),
]

GEOCODE_CACHE_INDEXES: list[IndexModel] = [
    # Normalised address string is the cache key
    IndexModel([("address", ASCENDING)], unique=True, name="address_unique"),
    # TTL index: auto-expire cache entries after 90 days (90 * 24 * 3600 s)
    IndexModel(
        [("cached_at", ASCENDING)],
        expireAfterSeconds=60 * 60 * 24 * 90,
        name="geocode_ttl_90d",
    ),
]

INGEST_LOGS_INDEXES: list[IndexModel] = [
    IndexModel([("started_at", DESCENDING)], name="started_at_desc"),
    IndexModel([("source_name", ASCENDING)], name="source_name_asc"),
    # Compound for quick "last N runs for source X" queries
    IndexModel(
        [("source_name", ASCENDING), ("started_at", DESCENDING)],
        name="source_started_compound",
    ),
]


# ──────────────────────────────────────────────────────────
# Public helper
# ──────────────────────────────────────────────────────────

async def create_all_indexes(db: AsyncIOMotorDatabase) -> None:
    """Create all indexes for every collection.

    Uses create_indexes() which is idempotent – safe to call on every startup.
    Existing indexes with the same name and options are left untouched.
    """
    tasks = {
        "news": (db["news"], NEWS_INDEXES),
        "sources": (db["sources"], SOURCES_INDEXES),
        "geocode_cache": (db["geocode_cache"], GEOCODE_CACHE_INDEXES),
        "ingest_logs": (db["ingest_logs"], INGEST_LOGS_INDEXES),
    }

    for collection_name, (collection, index_list) in tasks.items():
        try:
            created = await collection.create_indexes(index_list)
            logger.info(
                "Indexes ensured for '{}': {}", collection_name, created
            )
        except Exception as exc:
            logger.error(
                "Failed to create indexes for '{}': {}", collection_name, exc
            )
            raise


# ──────────────────────────────────────────────────────────
# CLI entry-point (python -m app.db.indexes)
# ──────────────────────────────────────────────────────────

async def _main() -> None:
    from app.db.client import connect_db, disconnect_db, get_database

    await connect_db()
    db = get_database()
    await create_all_indexes(db)
    await disconnect_db()
    logger.info("All indexes created successfully.")


if __name__ == "__main__":
    asyncio.run(_main())
