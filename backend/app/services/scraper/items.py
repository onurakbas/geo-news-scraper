"""
Scrapy Item definitions.
Fields mirror the news document schema defined in copilot-instructions.md §6.
"""

import scrapy


class NewsItem(scrapy.Item):
    # Required fields
    source = scrapy.Field()        # str  – spider name / site label
    url = scrapy.Field()           # str  – canonical article URL
    title = scrapy.Field()         # str
    content = scrapy.Field()       # str  – cleaned plain text
    published_at = scrapy.Field()  # datetime | None

    # Optional / enriched later
    type = scrapy.Field()          # str  – auto-detected category
    district = scrapy.Field()      # str  – filled by NLP step
    city = scrapy.Field()          # str  – default "Kocaeli"

    # Internal pipeline use
    raw_html = scrapy.Field()      # bytes – saved to data/raw/
    spider_name = scrapy.Field()   # str
