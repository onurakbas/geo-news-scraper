"""
Location extractor for news articles.

Strategy: dictionary-based NER approach using known Kocaeli province
districts and common neighbourhood/place names.  Falls back to a simple
keyword scan of title + content when no district is matched.

Returns:
  - district  : normalised district name (first match wins)
  - locations : deduplicated list of all matched place strings found in text
"""

from __future__ import annotations

import re
import unicodedata
from typing import Optional

# ── Kocaeli districts (canonical Turkish spelling) ────────────────────────────

KOCAELI_DISTRICTS: list[str] = [
    "Başiskele",
    "Çayırova",
    "Darıca",
    "Derince",
    "Dilovası",
    "Gebze",
    "Gölcük",
    "İzmit",
    "Kandıra",
    "Karamürsel",
    "Kartepe",
    "Körfez",
]

# Common alternative spellings / abbreviations mapped to canonical names
DISTRICT_ALIASES: dict[str, str] = {
    "basiskele": "Başiskele",
    "cayirova": "Çayırova",
    "cayrova": "Çayırova",
    "darica": "Darıca",
    "derince": "Derince",
    "dilovasi": "Dilovası",
    "gebze": "Gebze",
    "golcuk": "Gölcük",
    "izmit": "İzmit",
    "izmit merkez": "İzmit",
    "kandira": "Kandıra",
    "karamursel": "Karamürsel",
    "kartepe": "Kartepe",
    "korfez": "Körfez",
    # common colloquials
    "kocaeli merkez": "İzmit",
    "merkez": "İzmit",
}

# ── Helpers ───────────────────────────────────────────────────────────────────


def _normalise(text: str) -> str:
    """Lowercase + strip Turkish diacritics for fuzzy matching."""
    text = text.lower()
    # Map Turkish chars to ASCII equivalents for comparison
    replacements = {
        "ç": "c",
        "ğ": "g",
        "ı": "i",
        "ö": "o",
        "ş": "s",
        "ü": "u",
        "â": "a",
        "î": "i",
        "û": "u",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    # Remove any remaining combining characters
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return text


def _build_patterns() -> list[tuple[re.Pattern[str], str]]:
    """
    Build compiled (pattern, canonical_name) pairs for all known districts and
    aliases, ordered longest-first to prefer more specific matches.
    """
    entries: dict[str, str] = {}

    for canonical in KOCAELI_DISTRICTS:
        key = _normalise(canonical)
        entries[key] = canonical

    for alias, canonical in DISTRICT_ALIASES.items():
        entries[_normalise(alias)] = canonical

    # Sort by length descending so "izmit merkez" matches before "izmit"
    sorted_entries = sorted(entries.items(), key=lambda x: len(x[0]), reverse=True)

    patterns: list[tuple[re.Pattern[str], str]] = []
    for norm_key, canonical in sorted_entries:
        # Word-boundary aware pattern on the normalised key
        pattern = re.compile(r"\b" + re.escape(norm_key) + r"\b", re.IGNORECASE)
        patterns.append((pattern, canonical))

    return patterns


# Module-level compiled patterns (built once)
_PATTERNS: list[tuple[re.Pattern[str], str]] = _build_patterns()


# ── Public API ────────────────────────────────────────────────────────────────


def extract_locations(title: str, content: str) -> dict[str, object]:
    """
    Scan title and content for known Kocaeli district names.

    Args:
        title:   Article headline.
        content: Article body text.

    Returns:
        A dict with keys:
          - "district"  (Optional[str]): first/primary matched district
          - "locations" (list[str])    : all unique matched district names
    """
    # Normalise the combined text for matching
    combined_raw = f"{title} {content}"
    combined_norm = _normalise(combined_raw)

    matched: list[str] = []
    seen: set[str] = set()

    for pattern, canonical in _PATTERNS:
        if pattern.search(combined_norm) and canonical not in seen:
            matched.append(canonical)
            seen.add(canonical)

    district: Optional[str] = matched[0] if matched else None

    return {
        "district": district,
        "locations": matched,
    }


def build_geocode_query(district: Optional[str], city: str = "Kocaeli") -> Optional[str]:
    """
    Compose the address string to send to the Google Geocoding API.

    Args:
        district: Normalised district name, or None.
        city:     Province/city name (default: Kocaeli).

    Returns:
        A query string like "Gebze, Kocaeli, Turkey", or None when no district
        was extracted and therefore geocoding cannot be narrowed down.
    """
    if not district:
        return None
    return f"{district}, {city}, Turkey"
