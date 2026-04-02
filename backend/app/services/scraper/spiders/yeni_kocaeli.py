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
        # Homepage only – category archive pages cause 27-minute crawls
        "https://www.yenikocaeli.com/",
    ]

    # Relaxed date brake: homepage mixes old and new articles so we need a higher tolerance
    MAX_CONSECUTIVE_OLD: int = 20

    # Focused selectors: main-feed headline links, a[href*='/haber/'] safe because no pagination
    list_css = [
        "div.news-list h2 a",
        "ul.haberler li h2 a",
        "div.son-dakika h3 a",
        "div.manset h2 a",
        "div.haber-listesi h2 a",
        "div.icerik-alani h2 a",
        "a[href*='/haber/']",   # fallback – safe: pagination is disabled (next_page_css=None)
    ]
    next_page_css = None  # No pagination – homepage only

    def parse_article(self, response: Response) -> NewsItem | None:  # type: ignore[override]
        # Sadece gerçek haber URL'lerini işle: /haber/<sayisal-id>/<baslik> formatı
        # /haber/cedit%20mahallesi.html gibi tag/arama sayfalarını atla
        import re
        if not re.search(r'/haber/\d+/', response.url):
            return None

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
            "div.yazi-tarih",    # Primary on article pages
            "span.post-date",    # Fallback
            "span.tarih",
            "time",
            "span.date",
        )

        # Smart date-based stopping
        self._check_date_brake(published_at)

        return self._build_item(response, title, content, published_at)
