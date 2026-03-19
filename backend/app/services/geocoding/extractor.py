"""
Location extractor for news articles – Hybrid NER + Dictionary approach.

Strategy (3 layers, applied in order):

  Layer 1 – Neighbourhood / place-level dictionary:
    Known Kocaeli neighbourhoods, campuses, streets etc. are mapped to their
    parent district.  This is the most precise layer and gets first priority.

  Layer 2 – spaCy multilingual NER (xx_ent_wiki_sm):
    LOC / GPE entities detected by the model are normalised and looked up in
    the combined district + neighbourhood dictionaries.

  Layer 3 – District alias regex fallback:
    A regex scan over the 12 canonical district names and their common
    alternative spellings.  Runs when layers 1+2 find nothing.

Graceful degradation: if spaCy or its model is unavailable the module falls
back silently to layers 1 and 3 only.

Returns:
  - district  : normalised district name (first / best match)
  - locations : deduplicated list of all matched place strings
"""

from __future__ import annotations

import re
import unicodedata
from typing import Optional

from loguru import logger

# ── spaCy – optional, graceful degradation ────────────────────────────────────

_nlp = None  # lazy-loaded on first call

def _get_nlp():
    global _nlp
    if _nlp is not None:
        return _nlp
    try:
        import spacy  # noqa: PLC0415
        _nlp = spacy.load("xx_ent_wiki_sm")
        logger.info("[extractor] spaCy model 'xx_ent_wiki_sm' loaded.")
    except Exception as exc:
        logger.warning(f"[extractor] spaCy unavailable – NER layer disabled. ({exc})")
        _nlp = False  # sentinel: don't retry
    return _nlp


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

# ── District aliases (normalised → canonical) ─────────────────────────────────

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
    # colloquials
    "kocaeli merkez": "İzmit",
    "merkez": "İzmit",
}

# ── Neighbourhood / place → district mapping ──────────────────────────────────

NEIGHBORHOOD_TO_DISTRICT: dict[str, str] = {
    # İzmit
    "yahyakaptan": "İzmit",
    "yenidogan": "İzmit",
    "seka park": "İzmit",
    "plajyolu": "İzmit",
    "fethiye caddesi": "İzmit",
    "yuruyus yolu": "İzmit",
    "kurucesme": "İzmit",
    "alikahya": "İzmit",
    "kozluk": "İzmit",
    # Gebze
    "mutlukent": "Gebze",
    "tubitak": "Gebze",
    "tübitak": "Gebze",
    "guzeller osb": "Gebze",
    "güzeller osb": "Gebze",
    "plastikciler osb": "Gebze",
    "plastikçiler osb": "Gebze",
    "tatlikuyu": "Gebze",
    "tatlıkuyu": "Gebze",
    "arapcesme": "Gebze",
    "arapçeşme": "Gebze",
    # Derince
    "yenikent": "Derince",
    "cenedag": "Derince",
    "çenedağ": "Derince",
    "sirripasa": "Derince",
    "sırrıpaşa": "Derince",
    "harikalar sahili": "Derince",
    "60 evler": "Derince",
    "yavuz sultan": "Derince",
    # Körfez
    "yarimca": "Körfez",
    "yarımca": "Körfez",
    "tutunciftlik": "Körfez",
    "tütünçiftlik": "Körfez",
    "hereke": "Körfez",
    "sirinyali": "Körfez",
    "şirinyalı": "Körfez",
    # Kartepe
    "masukiye": "Kartepe",
    "maşukiye": "Kartepe",
    "derbent": "Kartepe",
    "suadiye": "Kartepe",
    "arslanbey": "Kartepe",
    "uzunciftlik": "Kartepe",
    "uzunçiftlik": "Kartepe",
    "kosekoy": "Kartepe",
    "köseköy": "Kartepe",
    # Başiskele
    "yuvacik": "Başiskele",
    "yuvacık": "Başiskele",
    "bahcecik": "Başiskele",
    "bahçecik": "Başiskele",
    "kullar": "Başiskele",
    "karsiyaka": "Başiskele",
    "karşıyaka": "Başiskele",
    "yenikoy": "Başiskele",
    "yeniköy": "Başiskele",
    # Gölcük
    "degirmendere": "Gölcük",
    "değirmendere": "Gölcük",
    "halidere": "Gölcük",
    "ulasli": "Gölcük",
    "ulaşlı": "Gölcük",
    "kavakli": "Gölcük",
    "kavaklı": "Gölcük",
    "ihsaniye": "Gölcük",
    "ihsaniye": "Gölcük",
    # Karamürsel
    "eregli": "Karamürsel",
    "ereğli": "Karamürsel",
    "altinkemer": "Karamürsel",
    "altınkemer": "Karamürsel",
    "tepekoy": "Karamürsel",
    "tepeköy": "Karamürsel",
    # Darıca
    "bayramoglu": "Darıca",
    "bayramoğlu": "Darıca",
    "emek": "Darıca",
    "osmangazi": "Darıca",
    "nenehatun": "Darıca",
    # Çayırova
    "sekerpinar": "Çayırova",
    "şekerpınar": "Çayırova",
    "akse": "Çayırova",
    "ozgurluk": "Çayırova",
    "özgürlük": "Çayırova",
    # Dilovası
    "mermerciler": "Dilovası",
    "komurculer": "Dilovası",
    "kömürcüler": "Dilovası",
    "tavsancil": "Dilovası",
    "tavşancıl": "Dilovası",
    "diliskelesi": "Dilovası",
    # Kandıra
    "kefken": "Kandıra",
    "kerpe": "Kandıra",
    "cebeci": "Kandıra",
    "babali": "Kandıra",
    "babalı": "Kandıra",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _normalise(text: str) -> str:
    """Lowercase + strip Turkish diacritics for fuzzy matching."""
    text = text.lower()
    replacements = {
        "ç": "c", "ğ": "g", "ı": "i", "ö": "o",
        "ş": "s", "ü": "u", "â": "a", "î": "i", "û": "u",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return text


def _lookup_in_dictionaries(token: str) -> Optional[str]:
    """
    Look up a raw token in neighbourhood dict first, then district aliases.
    Returns canonical district name or None.
    """
    norm = _normalise(token)
    # 1. Neighbourhood → district
    district = NEIGHBORHOOD_TO_DISTRICT.get(norm)
    if district:
        return district
    # 2. District alias
    district = DISTRICT_ALIASES.get(norm)
    return district


def _build_district_patterns() -> list[tuple[re.Pattern[str], str]]:
    """Compile regex patterns for district + alias matching (longest first)."""
    entries: dict[str, str] = {}
    for canonical in KOCAELI_DISTRICTS:
        entries[_normalise(canonical)] = canonical
    for alias, canonical in DISTRICT_ALIASES.items():
        entries[_normalise(alias)] = canonical

    sorted_entries = sorted(entries.items(), key=lambda x: len(x[0]), reverse=True)
    return [
        (re.compile(r"\b" + re.escape(k) + r"\b", re.IGNORECASE), v)
        for k, v in sorted_entries
    ]


def _build_neighbourhood_patterns() -> list[tuple[re.Pattern[str], str]]:
    """Compile regex patterns for neighbourhood → district matching (longest first)."""
    # Use Turkish + normalised keys for robustness
    entries: dict[str, str] = {}
    for raw_key, district in NEIGHBORHOOD_TO_DISTRICT.items():
        entries[_normalise(raw_key)] = district
        entries[raw_key.lower()] = district   # keep original Turkish too

    sorted_entries = sorted(entries.items(), key=lambda x: len(x[0]), reverse=True)
    return [
        (re.compile(r"\b" + re.escape(k) + r"\b", re.IGNORECASE), v)
        for k, v in sorted_entries
    ]


# Module-level compiled patterns (built once at import time)
_DISTRICT_PATTERNS = _build_district_patterns()
_NEIGHBOURHOOD_PATTERNS = _build_neighbourhood_patterns()


# ── Layer implementations ─────────────────────────────────────────────────────

def _layer1_dictionary(combined_norm: str, combined_raw: str) -> list[str]:
    """Neighbourhood + district regex scan over normalised + raw text."""
    matched: list[str] = []
    seen: set[str] = set()

    for pattern, district in _NEIGHBOURHOOD_PATTERNS:
        if pattern.search(combined_raw) or pattern.search(combined_norm):
            if district not in seen:
                matched.append(district)
                seen.add(district)

    return matched


def _layer2_spacy(combined_raw: str) -> list[str]:
    """Use spaCy NER to find LOC/GPE entities, map them to districts."""
    nlp = _get_nlp()
    if not nlp:
        return []

    matched: list[str] = []
    seen: set[str] = set()

    try:
        doc = nlp(combined_raw[:5000])  # cap text length for performance
        for ent in doc.ents:
            if ent.label_ not in ("LOC", "GPE"):
                continue
            entity_text = ent.text.strip()
            district = _lookup_in_dictionaries(entity_text)
            if district and district not in seen:
                matched.append(district)
                seen.add(district)
                logger.debug(f"[extractor] NER hit: '{entity_text}' → {district}")
    except Exception as exc:
        logger.warning(f"[extractor] spaCy inference error: {exc}")

    return matched


def _layer3_district_regex(combined_norm: str) -> list[str]:
    """Fallback: raw district name / alias regex scan."""
    matched: list[str] = []
    seen: set[str] = set()

    for pattern, canonical in _DISTRICT_PATTERNS:
        if pattern.search(combined_norm) and canonical not in seen:
            matched.append(canonical)
            seen.add(canonical)

    return matched


# ── Public API ────────────────────────────────────────────────────────────────

def extract_locations(title: str, content: str) -> dict[str, object]:
    """
    Scan title and content for Kocaeli district names using a hybrid
    3-layer strategy: neighbourhood dictionary → spaCy NER → district regex.

    Returns:
        {
          "district"  : Optional[str]  – primary matched district,
          "locations" : list[str]      – all unique matched districts,
        }
    """
    combined_raw = f"{title} {content}"
    combined_norm = _normalise(combined_raw)

    # Layer 1: neighbourhood / place-level dictionary
    results = _layer1_dictionary(combined_norm, combined_raw)

    # Layer 2: spaCy NER (adds entities not caught by sözlük)
    if not results:
        results = _layer2_spacy(combined_raw)

    # Layer 3: district alias regex fallback
    if not results:
        results = _layer3_district_regex(combined_norm)

    # Merge all layers and deduplicate while preserving order
    seen: set[str] = set()
    locations: list[str] = []
    for d in results:
        if d not in seen:
            locations.append(d)
            seen.add(d)

    district: Optional[str] = locations[0] if locations else None

    return {
        "district": district,
        "locations": locations,
    }


def build_geocode_query(district: Optional[str], city: str = "Kocaeli") -> Optional[str]:
    """
    Compose the address string to send to the Google Geocoding API.

    Returns "Gebze, Kocaeli, Turkey" style string, or None if no district.
    """
    if not district:
        return None
    return f"{district}, {city}, Turkey"
