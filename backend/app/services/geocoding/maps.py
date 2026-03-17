"""
Google Geocoding API client with MongoDB-backed cache.

Flow for each geocode request:
  1. Normalise the address query.
  2. Check geocode_cache collection – return cached result immediately.
  3. On cache miss: call Google Geocoding API (with retry + rate-limit guard).
  4. Persist result to geocode_cache.
  5. Return (lat, lng, formatted_address).

Uses pymongo (sync) to match the sync scraping/dedup pipeline style.
Rate limiting: maximum REQUESTS_PER_SECOND calls/second via a simple token
approach with time.sleep().
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Optional

import pymongo
from loguru import logger
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings

# ── Constants ─────────────────────────────────────────────────────────────────

REQUESTS_PER_SECOND: float = 0.5
"""Max calls per second to the Geocoding API (conservative: 0.5 = 1 per 2 s)."""

_last_call_time: float = 0.0
"""Module-level timestamp of the most recent API call (for rate limiting)."""


# ── Geocoding API call (with retry) ──────────────────────────────────────────


class GeocodingError(Exception):
    """Raised when the Geocoding API returns an unrecoverable error."""


@retry(
    retry=retry_if_exception_type(GeocodingError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
def _call_geocoding_api(address: str, api_key: str) -> dict:
    """
    Make a single geocoding request to the Google Maps Geocoding REST endpoint.

    Returns the first result dict from the API response, or raises
    GeocodingError on API-level failures.
    """
    import httpx  # deferred import – keeps module loadable without httpx

    global _last_call_time

    # ── Rate limiting ──────────────────────────────────────────────────────
    elapsed = time.monotonic() - _last_call_time
    min_interval = 1.0 / REQUESTS_PER_SECOND
    if elapsed < min_interval:
        time.sleep(min_interval - elapsed)
    _last_call_time = time.monotonic()

    # ── HTTP request ───────────────────────────────────────────────────────
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": address, "key": api_key, "language": "tr"}

    try:
        response = httpx.get(url, params=params, timeout=10.0)
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise GeocodingError(f"HTTP {exc.response.status_code} for address '{address}'") from exc
    except httpx.RequestError as exc:
        raise GeocodingError(f"Network error for address '{address}': {exc}") from exc

    data = response.json()
    status = data.get("status")

    if status == "OK":
        results = data.get("results", [])
        if results:
            return results[0]
        raise GeocodingError(f"No results in OK response for '{address}'")

    if status in ("ZERO_RESULTS",):
        # Not an error per se – just no match.  Don't retry.
        return {}

    if status in ("OVER_DAILY_LIMIT", "OVER_QUERY_LIMIT", "REQUEST_DENIED"):
        raise GeocodingError(f"API quota/auth error ({status}) for '{address}'")

    raise GeocodingError(f"Geocoding API returned status={status} for '{address}'")


# ── Cache helpers ─────────────────────────────────────────────────────────────


def _get_cache_collection(db: pymongo.database.Database):  # type: ignore[return]
    """Return the geocode_cache collection from the given sync pymongo database."""
    return db["geocode_cache"]


def _lookup_cache(col, address: str) -> Optional[dict]:
    """Return cached geocode doc for *address*, or None on cache miss."""
    return col.find_one({"address": address})


def _store_cache(col, address: str, lat: float, lng: float, formatted_address: str) -> None:
    """Upsert a geocode result into the cache collection."""
    doc = {
        "address": address,
        "lat": lat,
        "lng": lng,
        "formatted_address": formatted_address,
        "cached_at": datetime.now(timezone.utc),
    }
    col.update_one({"address": address}, {"$set": doc}, upsert=True)


# ── Public API ────────────────────────────────────────────────────────────────


def geocode_address(
    address: str,
    db: pymongo.database.Database,  # type: ignore[type-arg]
    api_key: Optional[str] = None,
) -> Optional[dict[str, object]]:
    """
    Geocode *address* with cache-first strategy.

    Args:
        address: Normalised query string, e.g. "Gebze, Kocaeli, Turkey".
        db:      Synchronous pymongo Database instance.
        api_key: Google Geocoding API key.  Falls back to settings if None.

    Returns:
        Dict with keys "lat", "lng", "formatted_address", or None on failure.
    """
    if not address:
        return None

    key = api_key or settings.GOOGLE_GEOCODING_API_KEY
    if not key:
        logger.warning("GOOGLE_GEOCODING_API_KEY is not set; skipping geocoding.")
        return None

    col = _get_cache_collection(db)

    # ── Cache hit ──────────────────────────────────────────────────────────
    cached = _lookup_cache(col, address)
    if cached:
        logger.debug(f"[geocode] Cache hit for '{address}'")
        return {
            "lat": cached["lat"],
            "lng": cached["lng"],
            "formatted_address": cached["formatted_address"],
        }

    # ── Cache miss: call Google ────────────────────────────────────────────
    logger.info(f"[geocode] Cache miss – calling Google API for '{address}'")
    try:
        result = _call_geocoding_api(address, key)
    except GeocodingError as exc:
        logger.error(f"[geocode] API error: {exc}")
        return None

    if not result:
        logger.warning(f"[geocode] No result returned for '{address}'")
        return None

    geometry = result.get("geometry", {}).get("location", {})
    lat: Optional[float] = geometry.get("lat")
    lng: Optional[float] = geometry.get("lng")
    formatted_address: str = result.get("formatted_address", address)

    if lat is None or lng is None:
        logger.warning(f"[geocode] Missing lat/lng in API response for '{address}'")
        return None

    # ── Persist to cache ───────────────────────────────────────────────────
    _store_cache(col, address, lat, lng, formatted_address)
    logger.debug(f"[geocode] Cached ({lat}, {lng}) for '{address}'")

    return {"lat": lat, "lng": lng, "formatted_address": formatted_address}
