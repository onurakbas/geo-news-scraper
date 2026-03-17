"""
Geocoding runner – extracts locations from news articles and populates
the coordinates field with GeoJSON Point data from Google Geocoding API.

Usage:
    # Process only docs without coordinates (default, incremental)
    python scripts/run_geocode.py

    # Force a full re-run (re-geocode ALL articles)
    python scripts/run_geocode.py --full-rerun

    # Custom MongoDB settings via environment
    MONGODB_URI=mongodb://localhost:27017 MONGODB_DB_NAME=geo_news python scripts/run_geocode.py

Run from the project root with the virtual-env active:
    source .venv/bin/activate
    python scripts/run_geocode.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Make the backend package importable when running from project root
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from loguru import logger

# Load .env so API keys and MongoDB settings are available without exporting
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except ImportError:
    pass  # python-dotenv not installed; rely on shell environment

import pymongo
from app.core.config import settings
from app.services.geocoding.pipeline import run_geocoding


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run geocoding pipeline: extract locations from news and store coordinates."
    )
    parser.add_argument(
        "--full-rerun",
        action="store_true",
        default=False,
        help="Re-geocode ALL documents, even those that already have coordinates.",
    )
    args = parser.parse_args()

    # ── Validate API key ───────────────────────────────────────────────────
    if not settings.GOOGLE_GEOCODING_API_KEY:
        logger.error(
            "GOOGLE_GEOCODING_API_KEY is not set. "
            "Add it to your .env file and try again."
        )
        sys.exit(1)

    # ── Connect to MongoDB (sync) ─────────────────────────────────────────
    logger.info(f"Connecting to MongoDB at {settings.MONGODB_URI} …")
    client: pymongo.MongoClient = pymongo.MongoClient(settings.MONGODB_URI)  # type: ignore[type-arg]
    try:
        client.admin.command("ping")
    except Exception as exc:
        logger.error(f"Cannot reach MongoDB: {exc}")
        sys.exit(1)

    db = client[settings.MONGODB_DB_NAME]

    # ── Run pipeline ───────────────────────────────────────────────────────
    logger.info("Starting geocoding pipeline…")
    summary = run_geocoding(db, full_rerun=args.full_rerun)

    # ── Report ─────────────────────────────────────────────────────────────
    print("\n── Geocoding Summary ──────────────────────────────")
    print(f"  Documents processed  : {summary['total']}")
    print(f"  Successfully geocoded: {summary['geocoded']}")
    print(f"  Skipped (no district): {summary['skipped']}")
    print(f"  Failed (API/no result): {summary['failed']}")
    print(f"  Documents updated    : {summary['updated']}")
    print("───────────────────────────────────────────────────\n")

    client.close()


if __name__ == "__main__":
    main()
