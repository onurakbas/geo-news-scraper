"""
Scrapy project settings for Geo News Scraper.
See: https://docs.scrapy.org/en/latest/topics/settings.html
"""

import os

BOT_NAME = "geo_news_scraper"

SPIDER_MODULES = ["app.services.scraper.spiders"]
NEWSPIDER_MODULE = "app.services.scraper.spiders"

# ── Politeness ──────────────────────────────────────────────────────────────
ROBOTSTXT_OBEY = True
DOWNLOAD_DELAY = 1.5
RANDOMIZE_DOWNLOAD_DELAY = True
CONCURRENT_REQUESTS = 8
CONCURRENT_REQUESTS_PER_DOMAIN = 2
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1
AUTOTHROTTLE_MAX_DELAY = 10
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.5

# ── User-Agent rotation ─────────────────────────────────────────────────────
USER_AGENT_LIST = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
]
# Default – overridden per-request by the RandomUserAgentMiddleware
USER_AGENT = USER_AGENT_LIST[0]

# ── Retries ─────────────────────────────────────────────────────────────────
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]
HTTPERROR_ALLOWED_CODES = [404]  # 404s are logged, not treated as errors

# ── Timeouts ────────────────────────────────────────────────────────────────
DOWNLOAD_TIMEOUT = 20

# ── Pipelines ───────────────────────────────────────────────────────────────
ITEM_PIPELINES = {
    "app.services.scraper.pipelines.ValidationPipeline": 100,
    "app.services.scraper.pipelines.DateFilterPipeline": 150,
    "app.services.scraper.pipelines.RawHtmlPipeline": 200,
    "app.services.scraper.pipelines.MongoNewsPipeline": 300,
}

# ── Middleware ───────────────────────────────────────────────────────────────
DOWNLOADER_MIDDLEWARES = {
    "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
    "app.services.scraper.middlewares.RandomUserAgentMiddleware": 400,
    "scrapy.downloadermiddlewares.retry.RetryMiddleware": 550,
}

# ── Feed / logging ───────────────────────────────────────────────────────────
LOG_LEVEL = "INFO"
FEED_EXPORT_ENCODING = "utf-8"

# ── MongoDB (read from env so settings.py stays secret-free) ─────────────────
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "geo_news")

# ── Raw HTML output directory ────────────────────────────────────────────────
RAW_HTML_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "..", "..", "data", "raw"
)

# ── Duplicate filter ─────────────────────────────────────────────────────────
DUPEFILTER_CLASS = "scrapy.dupefilters.RFPDupeFilter"
