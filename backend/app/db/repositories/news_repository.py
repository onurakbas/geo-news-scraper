"""
News repository – all MongoDB queries for the news collection.

Architecture rule: business logic and DB queries stay in the repository layer,
not in endpoint handlers.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.services.nlp.classifier import (
    CAT_YANGIN, CAT_TRAFIK, CAT_HIRSIZLIK, CAT_ELEKTRIK, CAT_KULTUR,
)

# Only these 5 categories are exposed through the API
VALID_CATEGORIES: list[str] = [
    CAT_YANGIN,
    CAT_TRAFIK,
    CAT_HIRSIZLIK,
    CAT_ELEKTRIK,
    CAT_KULTUR,
]


def _build_match_stage(
    date_from: Optional[str],
    date_to: Optional[str],
    type_filter: Optional[str],
    district: Optional[str],
    require_coordinates: bool = False,
    only_valid_categories: bool = True,
) -> dict[str, Any]:
    """Build the $match stage dict for aggregation or find queries."""
    match: dict[str, Any] = {}

    # Only expose the 5 mandatory categories (exclude "Diğer")
    if only_valid_categories:
        if type_filter and type_filter in VALID_CATEGORIES:
            match["type"] = type_filter
        else:
            match["type"] = {"$in": VALID_CATEGORIES}

    if district:
        match["district"] = district

    if date_from or date_to:
        date_filter: dict[str, Any] = {}
        if date_from:
            try:
                date_filter["$gte"] = datetime.fromisoformat(date_from).replace(
                    tzinfo=timezone.utc
                )
            except ValueError:
                pass
        if date_to:
            try:
                date_filter["$lte"] = datetime.fromisoformat(date_to).replace(
                    tzinfo=timezone.utc
                )
            except ValueError:
                pass
        if date_filter:
            match["published_at"] = date_filter

    if require_coordinates:
        match["coordinates"] = {"$ne": None, "$exists": True}

    return match


# ── Aggregation pipeline helpers ──────────────────────────────────────────────

def _group_by_similarity_pipeline(match: dict[str, Any]) -> list[dict]:
    """
    MongoDB aggregation that groups deduplicated articles.

    For each similarity_group_id, the representative document (lowest
    published_at) is returned along with a merged `sources` and `urls` array
    from all documents in the group.
    """
    return [
        {"$match": match},
        {"$sort": {"published_at": -1}},
        {
            "$group": {
                "_id": {
                    "$ifNull": [
                        "$similarity_group_id",
                        {"$toString": "$_id"},
                    ]
                },
                # Pick representative document fields from first (latest) doc
                "doc_id":       {"$first": {"$toString": "$_id"}},
                "title":        {"$first": "$title"},
                "published_at": {"$first": "$published_at"},
                "type":         {"$first": "$type"},
                "district":     {"$first": "$district"},
                "city":         {"$first": "$city"},
                "coordinates":  {"$first": "$coordinates"},
                "similarity_group_id": {"$first": "$similarity_group_id"},
                # Merge all sources and urls across the group
                "sources": {"$addToSet": "$source"},
                "urls":    {"$addToSet": {"$toString": "$url"}},
            }
        },
        {
            "$project": {
                "_id":               "$doc_id",
                "title":             1,
                "published_at":      1,
                "type":              1,
                "district":          1,
                "city":              1,
                "coordinates":       1,
                "similarity_group_id": 1,
                "sources":           1,
                "urls":              1,
            }
        },
    ]


# ── Public repository functions ───────────────────────────────────────────────

async def get_news_list(
    db: AsyncIOMotorDatabase,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    type_filter: Optional[str] = None,
    district: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict], int]:
    """
    Return paginated, deduplicated news grouped by similarity_group_id.
    Returns (items, total_count).
    """
    match = _build_match_stage(date_from, date_to, type_filter, district)
    pipeline = _group_by_similarity_pipeline(match)

    # Run aggregation
    cursor = db["news"].aggregate(pipeline)
    all_items = await cursor.to_list(length=None)

    # Sort by published_at descending after grouping
    all_items.sort(key=lambda x: x.get("published_at") or datetime.min, reverse=True)

    total = len(all_items)
    start = (page - 1) * page_size
    page_items = all_items[start: start + page_size]

    return page_items, total


async def get_map_markers(
    db: AsyncIOMotorDatabase,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    type_filter: Optional[str] = None,
    district: Optional[str] = None,
) -> list[dict]:
    """
    Return all geocoded news as lightweight marker objects.
    GeoJSON coordinates are unpacked to flat lat/lon fields.
    No pagination – the frontend handles clustering.
    """
    match = _build_match_stage(
        date_from, date_to, type_filter, district,
        require_coordinates=True,
        only_valid_categories=False,  # Show ALL categories on map, not only the 5 mandatory
    )
    pipeline = _group_by_similarity_pipeline(match)

    # Unpack GeoJSON: coordinates.coordinates = [lon, lat]
    pipeline.append({
        "$addFields": {
            "lon": {"$arrayElemAt": ["$coordinates.coordinates", 0]},
            "lat": {"$arrayElemAt": ["$coordinates.coordinates", 1]},
        }
    })
    # Drop raw coordinates object – frontend only needs lat/lon
    pipeline.append({
        "$project": {
            "coordinates": 0,
            "city": 0,
            "similarity_group_id": 0,
        }
    })
    pipeline.append({"$sort": {"published_at": -1}})

    cursor = db["news"].aggregate(pipeline)
    return await cursor.to_list(length=None)


async def get_filter_options(
    db: AsyncIOMotorDatabase,
) -> dict[str, list[str]]:
    """Return distinct types and districts available in the collection."""
    types_raw = await db["news"].distinct("type", {"type": {"$in": VALID_CATEGORIES}})
    districts_raw = await db["news"].distinct(
        "district", {"district": {"$ne": None}, "type": {"$in": VALID_CATEGORIES}}
    )

    # Sort for deterministic UI ordering
    types = sorted(t for t in types_raw if t)
    districts = sorted(d for d in districts_raw if d)

    return {"types": types, "districts": districts}


async def get_news_by_id(
    db: AsyncIOMotorDatabase,
    news_id: str,
) -> Optional[dict]:
    """Return a single news document by its string _id."""
    from bson import ObjectId  # noqa: PLC0415

    try:
        oid = ObjectId(news_id)
    except Exception:
        return None

    doc = await db["news"].find_one({"_id": oid})
    if doc:
        doc["_id"] = str(doc["_id"])
    return doc
