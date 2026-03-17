"""
Spider for Yeni Kocaeli – https://www.yenikocaeli.com/
"""

from __future__ import annotations

from scrapy.http import Response

from app.services.scraper.items import NewsItem
from app.services.scraper.spiders.base_spider import BaseNewsSpider


class YeniKocaeliSpider(BaseNewsSpider):
    name = "yeni_kocaeli"
    source_label = "Yeni Kocaeli"
    allowed_domains = ["yenikocaeli.com"]
    start_urls = [
        "https://www.yenikocaeli.com/",
        "https://www.yenikocaeli.com/gundem/",
        "https://www.yenikocaeli.com/son-dakika/",
    ]

    list_css = [
        "div.news-list h2 a",
        "ul.haberler li h2 a",
        "article h2 a",
        "h3.entry-title a",
        "a[href*='/haber/']",
    ]
    next_page_css = "a.next-page, a.next"

    def parse_article(self, response: Response) -> NewsItem | None:  # type: ignore[override]
        title = self._extract_title(
            response,
            "h1.haber-baslik::text",
            "h1.entry-title::text",
            "h1::text",
        )
        if not title:
            return None

        content = self._extract_content(
            response,
            "div.haber-detay p::text",
            "div.icerik p::text",
            "div.entry-content p::text",
        )

        published_at = self._extract_date(
            response,
            "span.tarih",
            "time",
            "span.date",
        )

        return self._build_item(response, title, content, published_at)
