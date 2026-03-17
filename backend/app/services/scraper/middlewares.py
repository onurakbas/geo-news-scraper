"""
Custom Scrapy downloader middlewares.
"""

import random

from scrapy import signals
from scrapy.http import Request


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

    def process_request(self, request: Request, spider) -> None:
        request.headers["User-Agent"] = random.choice(self.user_agent_list)
