"""
Utility: parse a raw date string into a UTC-aware datetime.

Tries dateutil first (handles most ISO / RFC formats), then a set of
Turkish locale patterns common on Kocaeli news sites.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from dateutil import parser as dateutil_parser
from loguru import logger

# Turkish month name → number mapping
_TR_MONTHS: dict[str, int] = {
    "ocak": 1, "şubat": 2, "mart": 3, "nisan": 4,
    "mayıs": 5, "haziran": 6, "temmuz": 7, "ağustos": 8,
    "eylül": 9, "ekim": 10, "kasım": 11, "aralık": 12,
}

# e.g. "17 Mart 2026 15:30" or "17 Mart 2026" or "17 Mart 202615:30" (no space before time)
_TR_PATTERN = re.compile(
    r"(\d{1,2})\s+([A-Za-z\u00c7\u00e7\u011e\u011f\u0130\u0131\u00d6\u00f6\u015e\u015f\u00dc\u00fc]+)\s+(\d{4})"
    r"(?:[\s:]*(\d{1,2}):(\d{2})(?::(\d{2}))?)?",
    re.IGNORECASE,
)


def parse_date(raw: str) -> datetime | None:
    """Return a UTC-aware datetime or None if parsing fails."""
    if not raw:
        return None

    raw = raw.strip()

    # 1. dateutil handles ISO 8601, RFC 2822, and many other formats
    try:
        dt = dateutil_parser.parse(raw, dayfirst=True)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        pass

    # 2. Turkish date pattern fallback
    m = _TR_PATTERN.search(raw)
    if m:
        day = int(m.group(1))
        month_name = m.group(2).lower()
        year = int(m.group(3))
        hour = int(m.group(4)) if m.group(4) else 0
        minute = int(m.group(5)) if m.group(5) else 0
        second = int(m.group(6)) if m.group(6) else 0
        month = _TR_MONTHS.get(month_name)
        if month:
            try:
                return datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)
            except ValueError:
                pass

    logger.warning("Could not parse date string: {!r}", raw)
    return None
