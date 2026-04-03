"""
Spider for Çağdaş Kocaeli – https://www.cagdaskocaeli.com.tr/
"""

from __future__ import annotations

from scrapy.http import Response

from app.services.scraper.items import NewsItem
from app.services.scraper.spiders.base_spider import BaseNewsSpider


class CagdasKocaeliSpider(BaseNewsSpider):
    name = "cagdas_kocaeli"
    source_label = "Çağdaş Kocaeli"
    allowed_domains = ["cagdaskocaeli.com.tr"]
    start_urls = [
        "https://www.cagdaskocaeli.com.tr/",
        "https://www.cagdaskocaeli.com.tr/kategori/gundem",
        "https://www.cagdaskocaeli.com.tr/kategori/son-dakika",
    ]

    # Article links on listing pages
    list_css = [
        "h2.entry-title a",
        "h3.entry-title a",
        "div.post-content a",
        "a.news-link",
        "div.category-news h2 a",
        "a[href*='/haber/']",
        "a[href*='/gundem/']",
    ]
    next_page_css = "a.next.page-numbers"

    def parse_article(self, response: Response) -> NewsItem | None:  # type: ignore[override]
        # Skip non-article pages
        if not any(k in response.url for k in ["/haber/", "/gundem/", "/?p=", "com.tr/"]):
            return None

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
            "div.post-text p::text",       # PRIMARY: Site'nin gerçek içerik container'ı
            "div.detay p::text",           # Alternatif
            "div.entry-content p::text",
            "div.post-content p::text",
            "div.news-content p::text",
            "div.content p::text",
        )

        published_at = self._extract_date(
            response,
            "span.post-date",    # Primary: '31 Mart 202610:28'
            "time.entry-date",
            "span.date",
        )

        self._check_date_brake(published_at)
        return self._build_item(response, title, content, published_at)
