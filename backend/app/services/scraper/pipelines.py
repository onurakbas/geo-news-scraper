"""
Scrapy Item Pipelines for Geo News Scraper.

Pipeline execution order (defined in settings.py):
  1. ValidationPipeline  (priority 100) – drop items missing required fields.
  2. DateFilterPipeline  (priority 150) – drop articles older than 72 hours.
  3. RawHtmlPipeline     (priority 200) – save raw HTML bytes to data/raw/.
  4. MongoNewsPipeline   (priority 300) – classify, then insert into MongoDB.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING

import pymongo
from pymongo import errors as pymongo_errors
from loguru import logger
from scrapy import signals
from scrapy import Spider
from scrapy.exceptions import DropItem

from app.services.scraper.items import NewsItem
from app.services.nlp.classifier import classify_news

if TYPE_CHECKING:
    pass


# ── 1. Validation ────────────────────────────────────────────────────────────

class ValidationPipeline:
    """Drop any item that is missing url, title, or source."""

    REQUIRED_FIELDS = ("url", "title", "source")

    def process_item(self, item: NewsItem) -> NewsItem:
        for field in self.REQUIRED_FIELDS:
            value = item.get(field)
            if not value or not str(value).strip():
                raise DropItem(
                    f"Missing required field '{field}' – url={item.get('url')}"
                )
        return item


# ── 2. Date Filter ───────────────────────────────────────────────────────────

class DateFilterPipeline:
    """
    Drop articles published more than 72 hours ago.

    Articles with no published_at date are allowed through so we don't
    silently discard content whose timestamp could not be parsed.
    """

    MAX_AGE: timedelta = timedelta(hours=72)

    def process_item(self, item: NewsItem) -> NewsItem:
        published_at: datetime | None = item.get("published_at")
        if published_at is None:
            return item

        if published_at.tzinfo is None:
            published_at = published_at.replace(tzinfo=timezone.utc)

        age = datetime.now(tz=timezone.utc) - published_at
        if age > self.MAX_AGE:
            raise DropItem(
                f"Article too old ({age.days}d {age.seconds//3600}h) – "
                f"url={item.get('url')}"
            )
        return item


# ── 2. Raw HTML saver ────────────────────────────────────────────────────────

class RawHtmlPipeline:
    """
    Persist raw HTML bytes to data/raw/<spider_name>/<url_slug>.html.
    Never blocks the scrape – exceptions are logged and swallowed.
    """

    def __init__(self, crawler) -> None:
        self._crawler = crawler
        self.base_dir: Path = Path("data/raw")
        self._spider_name: str = "unknown"

    @classmethod
    def from_crawler(cls, crawler):
        inst = cls(crawler)
        crawler.signals.connect(inst._on_spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(inst._on_spider_closed, signal=signals.spider_closed)
        return inst

    def _on_spider_opened(self, spider) -> None:
        self._spider_name = spider.name
        raw_dir = spider.settings.get("RAW_HTML_DIR", "data/raw")
        self.base_dir = Path(raw_dir) / spider.name
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _on_spider_closed(self, spider) -> None:
        pass  # nothing to close for file I/O

    def process_item(self, item: NewsItem) -> NewsItem:
        raw_html: bytes | None = item.get("raw_html")
        if not raw_html:
            return item

        try:
            url: str = item.get("url", "unknown")
            slug = (
                url.split("://", 1)[-1]
                .replace("/", "_")
                .replace("?", "_")
                .replace("&", "_")
                .replace("=", "_")
                [:180]
            )
            dest = self.base_dir / f"{slug}.html"
            dest.write_bytes(raw_html)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[{self._spider_name}] RawHtmlPipeline could not save HTML: {exc}")

        return item


# ── 3. MongoDB ───────────────────────────────────────────────────────────────

class MongoNewsPipeline:
    """
    Insert scraped news items into MongoDB.

    Duplicate handling (two layers):
      a) Scrapy DupeFilter – prevents re-visiting the same URL in one run.
      b) MongoDB unique index on `url` – duplicate key errors are
         caught and logged, not re-raised.

    Connection is synchronous (pymongo) because Scrapy's reactor is
    synchronous by default in the pipeline layer.
    """

    def __init__(self, crawler) -> None:
        self._crawler = crawler
        self._spider_name: str = "unknown"
        self.client = None
        self.collection = None

    @classmethod
    def from_crawler(cls, crawler):
        inst = cls(crawler)
        crawler.signals.connect(inst._on_spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(inst._on_spider_closed, signal=signals.spider_closed)
        return inst

    def _on_spider_opened(self, spider) -> None:
        self._spider_name = spider.name
        mongo_uri: str = spider.settings.get(
            "MONGODB_URI", os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        )
        db_name: str = spider.settings.get(
            "MONGODB_DB_NAME", os.getenv("MONGODB_DB_NAME", "geo_news")
        )
        self.client = pymongo.MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        db = self.client[db_name]
        self.collection = db["news"]
        try:
            self.collection.create_index("url", unique=True, background=True)
        except pymongo_errors.OperationFailure:
            # Index might already exist with a different name, ignore.
            pass
        logger.info(
            f"[{spider.name}] MongoNewsPipeline connected → "
            f"{mongo_uri} / db={db_name}"
        )

    def _on_spider_closed(self, spider) -> None:
        if self.client:
            self.client.close()
        logger.info(f"[{spider.name}] MongoNewsPipeline connection closed.")

    def process_item(self, item: NewsItem) -> NewsItem:
        now = datetime.now(tz=timezone.utc)

        news_type = classify_news(
            title=item.get("title", ""),
            content=item.get("content", ""),
        )

        doc: dict = {
            "source": item.get("source"),
            "url": item.get("url"),
            "title": item.get("title"),
            "content": item.get("content", ""),
            "published_at": item.get("published_at"),
            "type": news_type,
            "district": item.get("district"),
            "city": item.get("city", "Kocaeli"),
            "locations": [],
            "coordinates": None,
            "embedding": None,
            "similarity_group_id": None,
            "created_at": now,
            "updated_at": now,
        }

        try:
            result = self.collection.update_one(
                filter={"url": doc["url"]},
                update={"$setOnInsert": doc},
                upsert=True,
            )
            if result.upserted_id is not None:
                logger.debug(f"[{self._spider_name}] Inserted: {doc['url']}")
            else:
                logger.debug(f"[{self._spider_name}] Skipped duplicate: {doc['url']}")
        except pymongo_errors.PyMongoError as exc:
            logger.error(f"[{self._spider_name}] MongoDB error for {doc['url']}: {exc}")

        return item
