"""
Custom Scrapy downloader middlewares.
"""

from __future__ import annotations

import random
import re

from scrapy import signals
from scrapy.http import Request, Response


# ── Cloudflare / anti-bot fingerprints ───────────────────────────────────────

# HTML patterns that indicate bot-blocking pages
_BLOCK_PATTERNS: list[tuple[str, str]] = [
    # Cloudflare JS challenge
    ("just a moment", "Cloudflare JS challenge"),
    ("cf-browser-verification", "Cloudflare browser verification"),
    ("ray id", "Cloudflare Ray ID detected"),
    ("attention required! | cloudflare", "Cloudflare protection page"),
    # Generic CAPTCHA
    ("recaptcha", "reCAPTCHA challenge"),
    ("hcaptcha", "hCaptcha challenge"),
    ("captcha", "CAPTCHA wall"),
    # Other common blocks
    ("access denied", "Access Denied page"),
    ("403 forbidden", "403 Forbidden page"),
    ("too many requests", "Rate-limit / 429 page"),
    ("ddos-guard", "DDoS-Guard protection"),
    ("please enable javascript", "Bot-gating JS requirement"),
]

# HTTP status codes that signal blocking (beyond standard Scrapy errors)
_BLOCK_STATUS_CODES: set[int] = {403, 429, 503, 520, 521, 522, 523, 524, 525, 526}

# Cloudflare-specific response headers
_CF_HEADERS: set[str] = {"cf-ray", "cf-cache-status", "cf-request-id"}


def _check_response_for_blocks(request, response: Response, spider) -> None:  # noqa: C901
    """
    Inspect a response for anti-bot signals and emit clear log messages.
    Does NOT raise or drop items – purely observational.
    """
    source = getattr(spider, "source_label", spider.name)
    url = response.url

    # ── 1. Check HTTP status blocks ──────────────────────────────────────────
    if response.status in (403, 401, 429, 503):
        # If Playwright is active, a 403 might just be the initial JS Challenge status
        # but the DOM might be solved. Downgrade to WARNING instead of ERROR.
        is_playwright = False
        if request is not None:
            is_playwright = request.meta.get("playwright", False)
            
        if response.status == 403 and is_playwright:
            spider.logger.debug(
                "🛡️  [POTENTIAL BLOCK – 403] %s → %s (Playwright might solve this)",
                source,
                url,
            )
        else:
            spider.logger.error(
                "🚫 [BLOCKED – HTTP %d] %s → %s",
                response.status,
                source,
                url,
            )

    elif response.status != 200:
        spider.logger.warning(
            "⚠️  [UNEXPECTED HTTP %s] %s → %s",
            response.status,
            source,
            url,
        )

    # ── 2. Cloudflare header fingerprint ─────────────────────────────────────
    cf_headers_present = [h for h in _CF_HEADERS if h in response.headers]
    if cf_headers_present:
        # cf-ray only appears when a real CF edge handled the request –
        # may or may not be a block, but always worth knowing.
        if b"cf-ray" in response.headers:
            spider.logger.warning(
                "☁️  [CLOUDFLARE EDGE] %s responded via Cloudflare (cf-ray: %s) → %s",
                source,
                response.headers.get(b"cf-ray", b"").decode(),
                url,
            )

    # ── 3. HTML body content check ───────────────────────────────────────────
    try:
        body_lower = response.text.lower()
    except Exception:
        return  # binary / non-text response, skip

    for marker, label in _BLOCK_PATTERNS:
        if marker in body_lower:
            spider.logger.error(
                "🛑 [ANTI-BOT DETECTED – %s] %s → %s",
                label,
                source,
                url,
            )
            break  # one alert per page is enough

    # ── 4. Warn when the body is suspiciously short (<500 chars) ─────────────
    content_length = len(response.text)
    if content_length < 500 and response.status == 200:
        spider.logger.warning(
            "❓ [TINY BODY %d chars] %s → %s  (empty page or early block?)",
            content_length,
            source,
            url,
        )


# ── Middleware implementations ────────────────────────────────────────────────


class RandomUserAgentMiddleware:
    """Rotate User-Agent header from the list defined in settings."""

    def __init__(self, user_agent_list: list[str]) -> None:
        self.user_agent_list = user_agent_list

    @classmethod
    def from_crawler(cls, crawler):
        ua_list = crawler.settings.getlist("USER_AGENT_LIST")
        if not ua_list:
            ua_list = [crawler.settings.get("USER_AGENT")]
        return cls(ua_list)

    def process_request(self, request: Request) -> None:
        request.headers["User-Agent"] = random.choice(self.user_agent_list)


class AntiBotDetectionMiddleware:
    """
    Detect and log Cloudflare, CAPTCHA, 403/429, and other bot-blocking
    responses without interrupting the normal scraping pipeline.

    Enabled via DOWNLOADER_MIDDLEWARES in settings.py.
    """

    def __init__(self) -> None:
        self._spider = None  # set via signal so we don't need it as arg

    @classmethod
    def from_crawler(cls, crawler):
        inst = cls()
        crawler.signals.connect(inst._spider_opened, signal=signals.spider_opened)
        return inst

    def _spider_opened(self, spider) -> None:
        self._spider = spider
        spider.logger.info(
            "\U0001f6e1\ufe0f  AntiBotDetectionMiddleware active for spider: %s", spider.name
        )

    def process_response(self, request, response: Response, spider):
        """Check every response for anti-bot signals, then pass it through."""
        if self._spider is not None:
            _check_response_for_blocks(request, response, self._spider)
        return response  # always return – never drop here

    def process_exception(self, request: Request, exception) -> None:
        """Log network-level errors (timeouts, DNS failures, etc.)."""
        if self._spider is None:
            return
        source = getattr(self._spider, "source_label", self._spider.name)
        self._spider.logger.error(
            "\U0001f4a5 [NETWORK ERROR] %s \u2192 %s  (%s: %s)",
            source,
            request.url,
            type(exception).__name__,
            exception,
        )


