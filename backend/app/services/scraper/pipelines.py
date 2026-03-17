"""
Scrapy Item Pipelines for Geo News Scraper.

Pipeline execution order (defined in settings.py):
  1. ValidationPipeline  (priority 100) – drop items missing required fields.
  2. RawHtmlPipeline     (priority 200) – save raw HTML bytes to data/raw/.
  3. MongoNewsPipeline   (priority 300) – insert into MongoDB; skip URL duplicates.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

import pymongo
from loguru import logger
from scrapy import Spider
from scrapy.exceptions import DropItem

from app.services.scraper.items import NewsItem

if TYPE_CHECKING:
    pass


# ── 1. Validation ────────────────────────────────────────────────────────────

class ValidationPipeline:
    """Drop any item that is missing url, title, or source."""

    REQUIRED_FIELDS = ("url", "title", "source")

    def process_item(self, item: NewsItem, spider: Spider) -> NewsItem:
        for field in self.REQUIRED_FIELDS:
            value = item.get(field)
            if not value or not str(value).strip():
                raise DropItem(
                    f"[{spider.name}] Missing required field '{field}' – url={item.get('url')}"
                )
        return item


# ── 2. Raw HTML saver ────────────────────────────────────────────────────────

class RawHtmlPipeline:
    """
    Persist raw HTML bytes to data/raw/<spider_name>/<url_slug>.html.
    Never blocks the scrape – exceptions are logged and swallowed.
    """

    def open_spider(self, spider: Spider) -> None:
        raw_dir = spider.settings.get("RAW_HTML_DIR", "data/raw")
        self.base_dir = Path(raw_dir) / spider.name
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def process_item(self, item: NewsItem, spider: Spider) -> NewsItem:
        raw_html: bytes | None = item.get("raw_html")
        if not raw_html:
            return item

        try:
            url: str = item.get("url", "unknown")
            # Build a filesystem-safe filename from the URL
            slug = (
                url.split("://", 1)[-1]
                .replace("/", "_")
                .replace("?", "_")
                .replace("&", "_")
                .replace("=", "_")
                [:180]  # cap length
            )
            dest = self.base_dir / f"{slug}.html"
            dest.write_bytes(raw_html)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[{spider.name}] RawHtmlPipeline could not save HTML: {exc}")

        return item


# ── 3. MongoDB ───────────────────────────────────────────────────────────────

class MongoNewsPipeline:
    """
    Insert scraped news items into MongoDB.

    Duplicate handling (two layers):
      a) Scrapy DupeFilter – prevents re-visiting the same URL in one run.
      b) MongoDB unique index on `url` – insert_one is wrapped with
         UpdateOne + upsert=False equivalent; duplicate key errors are
         caught and logged, not re-raised.

    Connection is synchronous (pymongo) because Scrapy's reactor is
    synchronous by default in the pipeline layer.
    """

    def open_spider(self, spider: Spider) -> None:
        mongo_uri: str = spider.settings.get(
            "MONGODB_URI", os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        )
        db_name: str = spider.settings.get(
            "MONGODB_DB_NAME", os.getenv("MONGODB_DB_NAME", "geo_news")
        )
        self.client = pymongo.MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        self.db = self.client[db_name]
        self.collection = self.db["news"]

        # Ensure the unique URL index exists (idempotent)
        self.collection.create_index("url", unique=True, background=True)
        logger.info(
            f"[{spider.name}] MongoNewsPipeline connected → "
            f"{mongo_uri} / db={db_name}"
        )

    def close_spider(self, spider: Spider) -> None:
        self.client.close()
        logger.info(f"[{spider.name}] MongoNewsPipeline connection closed.")

    def process_item(self, item: NewsItem, spider: Spider) -> NewsItem:
        now = datetime.now(tz=timezone.utc)

        doc: dict = {
            "source": item.get("source"),
            "url": item.get("url"),
            "title": item.get("title"),
            "content": item.get("content", ""),
            "published_at": item.get("published_at"),
            "type": item.get("type", "genel"),
            "district": item.get("district"),
            "city": item.get("city", "Kocaeli"),
            # Enrichment fields – populated by later pipeline stages (NLP, geocoding)
            "locations": [],
            "coordinates": None,
            "embedding": None,
            "similarity_group_id": None,
            "created_at": now,
            "updated_at": now,
        }

        try:
            # Use update_one with upsert=True so the document is created only
            # when the URL is new; existing docs are NOT overwritten.
            result = self.collection.update_one(
                filter={"url": doc["url"]},
                update={"$setOnInsert": doc},
                upsert=True,
            )
            if result.upserted_id is not None:
                logger.debug(
                    f"[{spider.name}] Inserted: {doc['url']}"
                )
            else:
                logger.debug(
                    f"[{spider.name}] Skipped duplicate: {doc['url']}"
                )
        except pymongo.errors.PyMongoError as exc:
            logger.error(
                f"[{spider.name}] MongoDB error for {doc['url']}: {exc}"
            )

        return item
