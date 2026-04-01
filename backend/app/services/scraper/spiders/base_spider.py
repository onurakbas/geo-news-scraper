"""
BaseNewsSpider – shared logic for all Kocaeli news spiders.

Subclasses must define:
  - name          : unique spider identifier
  - source_label  : human-readable site name stored in MongoDB
  - start_urls    : list of entry-point URLs
  - list_css      : CSS selector(s) for article links on list pages
  - next_page_css : CSS selector for the "next page" link (or None)
  - parse_article : method that extracts fields from an article response
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Generator, Iterable

import scrapy
from scrapy.exceptions import CloseSpider
from scrapy.http import Response

from app.services.scraper.items import NewsItem
from app.services.scraper.parsers.date_parser import parse_date
from app.services.scraper.parsers.text_cleaner import clean_text

class BaseNewsSpider(scrapy.Spider):
    # Subclasses override these
    source_label: str = ""
    list_css: str | list[str] = "a"
    next_page_css: str | None = None
    max_pages: int = 20  # guard against infinite pagination

    # Smart date-based stopping: close spider after this many consecutive stale articles
    MAX_CONSECUTIVE_OLD: int = 10
    _cutoff: datetime = datetime.now(tz=timezone.utc) - timedelta(hours=72)
    _consecutive_old: int = 0

    def start_requests(self) -> Generator:
        """Yield initial requests routed through ScraperAPI Middleware."""
        for url in self.start_urls:
            yield scrapy.Request(
                url=url,
                callback=self.parse,
                dont_filter=True,
            )

    def parse(self, response: Response) -> Generator:
        """Parse a listing/category page and follow article links."""
        selectors = (
            [self.list_css] if isinstance(self.list_css, str) else self.list_css
        )
        seen_urls: set[str] = set()

        for css in selectors:
            for href in response.css(f"{css}::attr(href)").getall():
                url = response.urljoin(href)
                if url not in seen_urls:
                    seen_urls.add(url)
                    yield scrapy.Request(
                        url,
                        callback=self.parse_article,
                    )

        # Pagination – follow "next page" link up to max_pages
        if self.next_page_css:
            page_num = int(response.meta.get("page_num", 1))
            if page_num < self.max_pages:
                next_href = response.css(
                    f"{self.next_page_css}::attr(href)"
                ).get()
                if next_href:
                    yield response.follow(
                        next_href,
                        callback=self.parse,
                        meta={"page_num": page_num + 1},
                    )

    def parse_article(self, response: Response) -> NewsItem | None:  # type: ignore[override]
        """Default article parser – subclasses override or call super()."""
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement parse_article()"
        )

    def _check_date_brake(self, published_at: datetime | None) -> None:
        """
        Smart stopping: raise CloseSpider if MAX_CONSECUTIVE_OLD stale articles
        are seen in a row. Resets the counter when a fresh article is found.
        """
        if published_at is None:
            # Unknown date – treat as fresh to avoid false positives
            self._consecutive_old = 0
            return

        dt = published_at
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        if dt < self._cutoff:
            self._consecutive_old += 1
            if self._consecutive_old >= self.MAX_CONSECUTIVE_OLD:
                raise CloseSpider(
                    f"Date brake: {self._consecutive_old} consecutive stale articles – stopping."
                )
        else:
            self._consecutive_old = 0

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _extract_title(self, response: Response, *selectors: str) -> str:
        for sel in selectors:
            title = response.css(sel).get("").strip()
            if title:
                return clean_text(title)
        # Fallback to <title>
        return clean_text(response.css("title::text").get(""))

    def _extract_content(self, response: Response, *selectors: str) -> str:
        for sel in selectors:
            paragraphs = response.css(sel).getall()
            if paragraphs:
                return clean_text(" ".join(paragraphs))
        return ""

    def _extract_date(self, response: Response, *selectors: str) -> datetime | None:
        # 1. Try meta og / article tags first (most reliable)
        for prop in (
            "article:published_time",
            "article:modified_time",
            "og:updated_time",
        ):
            val = response.css(f'meta[property="{prop}"]::attr(content)').get()
            if val:
                return parse_date(val)

        # 2. Try provided CSS selectors
        for sel in selectors:
            raw = (
                response.css(f"{sel}::attr(datetime)").get()
                or response.css(f"{sel}::text").get()
            )
            if raw:
                parsed = parse_date(raw.strip())
                if parsed:
                    return parsed

        return None

    def _build_item(
        self,
        response: Response,
        title: str,
        content: str,
        published_at: datetime | None,
        news_type: str = "genel",
    ) -> NewsItem:
        item = NewsItem()
        item["source"] = self.source_label
        item["url"] = response.url
        item["title"] = title
        item["content"] = content
        item["published_at"] = published_at
        item["type"] = news_type
        item["city"] = "Kocaeli"
        item["district"] = None
        item["raw_html"] = response.body
        item["spider_name"] = self.name
        return item
