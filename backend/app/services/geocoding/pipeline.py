"""
Geocoding pipeline – orchestrates extraction, API calls, and DB writes.

Algorithm:
  1. Fetch news documents that still have no coordinates (or all, on full
     re-run).
  2. For each document, extract district / location names from title + content.
  3. Build a geocode query string and call the Google Geocoding API (cache
     checked first).
  4. Write the GeoJSON coordinates back to the news document.
  5. Also update the district and locations fields when they were empty.

Designed to run synchronously so it can be called from a plain script.
"""

from __future__ import annotations

from typing import Any

import pymongo
from loguru import logger

from app.services.geocoding.extractor import extract_locations, build_geocode_query
from app.services.geocoding.maps import geocode_address

# ── Constants ─────────────────────────────────────────────────────────────────

BATCH_SIZE = 200
"""Documents fetched per MongoDB cursor iteration."""


# ── Pipeline ─────────────────────────────────────────────────────────────────


def run_geocoding(
    db: pymongo.database.Database,  # type: ignore[type-arg]
    full_rerun: bool = False,
) -> dict[str, int]:
    """
    Process news documents and populate their coordinates field.

    Args:
        db:          Synchronous pymongo Database instance.
        full_rerun:  When True, re-geocode ALL documents even those that
                     already have coordinates.

    Returns:
        Summary dict with counts for total, skipped, geocoded, failed, updated.
    """
    news_col = db["news"]

    # ── Query ──────────────────────────────────────────────────────────────
    if full_rerun:
        query: dict[str, Any] = {}
        logger.info("[geocode-pipeline] Full re-run: processing ALL documents.")
    else:
        query = {"$or": [{"coordinates": {"$exists": False}}, {"coordinates": None}]}
        logger.info("[geocode-pipeline] Incremental run: processing docs without coordinates.")

    total = news_col.count_documents(query)
    logger.info(f"[geocode-pipeline] Documents to process: {total}")

    counts = {"total": total, "skipped": 0, "geocoded": 0, "failed": 0, "updated": 0, "neighborhood_hits": 0}

    if total == 0:
        return counts

    cursor = news_col.find(query, {"_id": 1, "title": 1, "content": 1, "district": 1, "locations": 1})

    for doc in cursor:
        doc_id = doc["_id"]
        title = doc.get("title", "")
        content = doc.get("content", "")

        # ── Extract locations ──────────────────────────────────────────────
        extracted = extract_locations(title, content)
        district: str | None = extracted["district"]  # type: ignore[assignment]
        neighborhood: str | None = extracted.get("neighborhood")  # type: ignore[assignment]
        locations: list[str] = extracted["locations"]  # type: ignore[assignment]

        if not district and not neighborhood:
            logger.debug(f"[geocode-pipeline] No district or neighborhood found for doc {doc_id} – skipping.")
            counts["skipped"] += 1
            continue
        query_str = build_geocode_query(district, neighborhood)
        if not query_str:
            counts["skipped"] += 1
            continue

        result = geocode_address(query_str, db)
        if not result:
            # Fallback: try district-only query if neighborhood query failed
            if neighborhood:
                fallback_query = build_geocode_query(district)
                result = geocode_address(fallback_query, db) if fallback_query else None
            if not result:
                logger.warning(f"[geocode-pipeline] Geocoding failed for '{query_str}' (doc {doc_id}).")
                counts["failed"] += 1
                continue

        lat: float = result["lat"]  # type: ignore[assignment]
        lng: float = result["lng"]  # type: ignore[assignment]

        # GeoJSON Point format required for 2dsphere index
        coordinates_doc = {
            "type": "Point",
            "coordinates": [lng, lat],  # GeoJSON order: [longitude, latitude]
        }

        # Build update – always set coordinates; fill district/locations/neighborhood if absent
        update_fields: dict[str, Any] = {"coordinates": coordinates_doc}
        if not doc.get("district"):
            update_fields["district"] = district
        if not doc.get("locations"):
            update_fields["locations"] = locations
        if neighborhood and not doc.get("neighborhood"):
            update_fields["neighborhood"] = neighborhood

        news_col.update_one({"_id": doc_id}, {"$set": update_fields})

        counts["geocoded"] += 1
        counts["updated"] += 1
        if neighborhood:
            counts["neighborhood_hits"] += 1
            logger.info(
                f"[geocode-pipeline] 📍 MAHALLE TESPİTİ: doc {doc_id} → "
                f"mahalle={neighborhood}, ilçe={district}, coords=({lat:.4f}, {lng:.4f})"
            )
        else:
            logger.debug(
                f"[geocode-pipeline] Updated doc {doc_id}: district={district}, coords=({lat:.4f}, {lng:.4f})"
            )

    neighborhood_count = counts.get("neighborhood_hits", 0)
    logger.info(
        f"[geocode-pipeline] Done. "
        f"total={counts['total']}, geocoded={counts['geocoded']}, "
        f"mahalle_tespiti={neighborhood_count}, "
        f"skipped={counts['skipped']}, failed={counts['failed']}"
    )
    return counts
