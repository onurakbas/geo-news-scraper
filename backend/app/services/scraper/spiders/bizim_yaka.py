"""
Spider for Bizim Yaka – https://www.bizimyaka.com/
"""

from __future__ import annotations

from scrapy.http import Response

from app.services.scraper.items import NewsItem
from app.services.scraper.spiders.base_spider import BaseNewsSpider


class BizimYakaSpider(BaseNewsSpider):
    name = "bizim_yaka"
    source_label = "Bizim Yaka"
    allowed_domains = ["bizimyaka.com"]
    start_urls = [
        "https://www.bizimyaka.com/",
        "https://www.bizimyaka.com/gundem/",
        "https://www.bizimyaka.com/son-dakika/",
    ]

    list_css = [
        "div.haber-kutu h2 a",
        "article.post h2 a",
        "h2.entry-title a",
        "h3.entry-title a",
        "a[href*='/haber/']",
    ]
    next_page_css = "a.next.page-numbers, a.next"

    def parse_article(self, response: Response) -> NewsItem | None:  # type: ignore[override]
        title = self._extract_title(
            response,
            "h1.entry-title::text",
            "h1.post-title::text",
            "h1::text",
        )
        if not title:
            return None

        content = self._extract_content(
            response,
            "div.entry-content p::text",
            "div.post-content p::text",
            "div.article-body p::text",
        )

        published_at = self._extract_date(
            response,
            ".tarih",           # Primary: '02 Nis 2026 - 17:02'
            "span.post-date",
            "div.yazi-tarih",
            "time.entry-date",
            "span.date",
        )

        self._check_date_brake(published_at)
        return self._build_item(response, title, content, published_at)
