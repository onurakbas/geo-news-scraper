"""
Deduplication runner – generates embeddings and groups near-duplicate news.

Usage:
    # Process only un-embedded / un-grouped articles (default, incremental)
    python scripts/run_dedup.py

    # Force a full re-run (re-groups ALL articles)
    python scripts/run_dedup.py --full-rerun

    # Custom MongoDB settings
    MONGODB_URI=mongodb://localhost:27017 MONGODB_DB_NAME=geo_news python scripts/run_dedup.py

Run from the project root with the virtual-env active:
    source .venv/bin/activate
    python scripts/run_dedup.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Make the backend package importable when running from project root
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from loguru import logger

# Load .env so MONGODB_URI / MONGODB_DB_NAME are available without exporting
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except ImportError:
    pass  # python-dotenv not installed; rely on shell environment

from app.services.nlp.deduplicator import run_deduplication


def main() -> None:
    parser = argparse.ArgumentParser(description="Run NLP deduplication pipeline.")
    parser.add_argument(
        "--full-rerun",
        action="store_true",
        default=False,
        help="Re-process ALL documents, even those already grouped.",
    )
    args = parser.parse_args()

    logger.info("Starting deduplication pipeline…")
    summary = run_deduplication(full_rerun=args.full_rerun)

    print("\n── Deduplication Summary ───────────────────────")
    print(f"  Documents found      : {summary['total']}")
    print(f"  Embeddings generated : {summary['embedded']}")
    print(f"  Duplicate pairs found: {summary['grouped']}")
    print(f"  Documents updated    : {summary['updated']}")
    print("────────────────────────────────────────────────\n")


if __name__ == "__main__":
    main()
