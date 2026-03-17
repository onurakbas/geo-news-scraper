"""
Spider for SES Kocaeli – https://www.seskocaeli.com/
"""

from __future__ import annotations

from scrapy.http import Response

from app.services.scraper.items import NewsItem
from app.services.scraper.spiders.base_spider import BaseNewsSpider


class SesKocaeliSpider(BaseNewsSpider):
    name = "ses_kocaeli"
    source_label = "SES Kocaeli"
    allowed_domains = ["seskocaeli.com"]
    start_urls = [
        "https://www.seskocaeli.com/",
        "https://www.seskocaeli.com/gundem/",
        "https://www.seskocaeli.com/son-dakika/",
    ]

    list_css = [
        "div.listing h2 a",
        "div.listing h3 a",
        "article.post h2 a",
        "article.post h3 a",
        "h2.post-title a",
        "a[href*='/haber/']",
    ]
    next_page_css = "a.next-page, a.next"

    def parse_article(self, response: Response) -> NewsItem | None:  # type: ignore[override]
        title = self._extract_title(
            response,
            "h1.title::text",
            "h1.post-title::text",
            "h1::text",
        )
        if not title:
            return None

        content = self._extract_content(
            response,
            "div.content p::text",
            "div.article-body p::text",
            "div.entry-content p::text",
        )

        published_at = self._extract_date(
            response,
            "time[datetime]",
            "span.date",
            "span.post-date",
        )

        return self._build_item(response, title, content, published_at)
