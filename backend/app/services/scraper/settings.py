"""
Scrapy project settings for Geo News Scraper.
See: https://docs.scrapy.org/en/latest/topics/settings.html
"""

import os

BOT_NAME = "geo_news_scraper"

SPIDER_MODULES = ["app.services.scraper.spiders"]
NEWSPIDER_MODULE = "app.services.scraper.spiders"

# ── ScraperAPI Configuration ──────────────────────────────────────────────────
SCRAPERAPI_KEY = os.getenv("SCRAPERAPI_KEY")
if not SCRAPERAPI_KEY:
    import logging
    logging.warning("⚠️  SCRAPERAPI_KEY is not set in environment! ScraperAPI proxy will not work.")


# ── Politeness ──────────────────────────────────────────────────────────────
ROBOTSTXT_OBEY = False
DOWNLOAD_DELAY = 1.5
RANDOMIZE_DOWNLOAD_DELAY = True
CONCURRENT_REQUESTS = 16  # Back to normal without Playwright RAM overhead
CONCURRENT_REQUESTS_PER_DOMAIN = 4
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1
AUTOTHROTTLE_MAX_DELAY = 10
AUTOTHROTTLE_TARGET_CONCURRENCY = 2.0

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
HTTPERROR_ALLOWED_CODES = [404]  # Reverted 403 block allowance since ScraperAPI bypasses them natively

# ── Timeouts ────────────────────────────────────────────────────────────────
DOWNLOAD_DELAY = 1.0  # Optional: keep a small delay, ScraperAPI manages rate limits, but politeness helps
DOWNLOAD_TIMEOUT = 120

# ── Custom Handlers for TLS Impersonation ───────────────────────────────────
DOWNLOAD_HANDLERS = {
    "http": "app.services.scraper.handlers.CurlCffiDownloadHandler",
    "https": "app.services.scraper.handlers.CurlCffiDownloadHandler",
}

# ── Pipelines ───────────────────────────────────────────────────────────────
ITEM_PIPELINES = {
    "app.services.scraper.pipelines.ValidationPipeline": 100,
    "app.services.scraper.pipelines.DateFilterPipeline": 200,
    "app.services.scraper.pipelines.RawHtmlPipeline": 300,
    "app.services.scraper.pipelines.MongoNewsPipeline": 400,
}

# ── Middleware ───────────────────────────────────────────────────────────────
DOWNLOADER_MIDDLEWARES = {
    "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
    "app.services.scraper.middlewares.RandomUserAgentMiddleware": 400,
    "app.services.scraper.middlewares.AntiBotDetectionMiddleware": 200,
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
