"""
Spider runner – runs all (or a selected) Kocaeli news spiders sequentially.

Usage:
    # Run all spiders
    python scripts/run_spiders.py

    # Run a single spider by name
    python scripts/run_spiders.py cagdas_kocaeli

Run from the project root with the virtual-env active:
    source .venv/bin/activate
    python scripts/run_spiders.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the backend package is importable when running from the project root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

SPIDER_NAMES = [
    "cagdas_kocaeli",
    "ozgur_kocaeli",
    "ses_kocaeli",
    "yeni_kocaeli",
    "bizim_yaka",
]


def main() -> None:
    # Scrapy resolves settings via SCRAPY_SETTINGS_MODULE env var or scrapy.cfg
    settings = get_project_settings()

    process = CrawlerProcess(settings)

    requested = sys.argv[1:] if len(sys.argv) > 1 else SPIDER_NAMES
    unknown = [s for s in requested if s not in SPIDER_NAMES]
    if unknown:
        print(f"Unknown spider(s): {unknown}")
        print(f"Available: {SPIDER_NAMES}")
        sys.exit(1)

    for spider_name in requested:
        process.crawl(spider_name)

    process.start()  # blocks until all crawls finish


if __name__ == "__main__":
    main()
