"""
Spider for Özgür Kocaeli – https://www.ozgurkocaeli.com.tr/
"""

from __future__ import annotations

from scrapy.http import Response

from app.services.scraper.items import NewsItem
from app.services.scraper.spiders.base_spider import BaseNewsSpider


class OzgurKocaeliSpider(BaseNewsSpider):
    name = "ozgur_kocaeli"
    source_label = "Özgür Kocaeli"
    allowed_domains = ["ozgurkocaeli.com.tr"]
    start_urls = [
        "https://www.ozgurkocaeli.com.tr/",
        "https://www.ozgurkocaeli.com.tr/gundem/",
        "https://www.ozgurkocaeli.com.tr/son-dakika/",
    ]

    list_css = [
        "h2.title a",
        "h3.title a",
        "div.haber-listesi h2 a",
        "div.news-list h3 a",
        "article.post h2 a",
        "a[href*='/haber/']",
    ]
    next_page_css = "a.next"

    def parse_article(self, response: Response) -> NewsItem | None:  # type: ignore[override]
        title = self._extract_title(
            response,
            "h1.baslik::text",
            "h1.entry-title::text",
            "h1::text",
        )
        if not title:
            return None

        content = self._extract_content(
            response,
            "div.haber-icerik p::text",
            "div.news-detail p::text",
            "div.entry-content p::text",
            "div.post-body p::text",
        )

        published_at = self._extract_date(
            response,
            "span.tarih",
            "time",
            "span.date",
        )

        self._check_date_brake(published_at)
        return self._build_item(response, title, content, published_at)
