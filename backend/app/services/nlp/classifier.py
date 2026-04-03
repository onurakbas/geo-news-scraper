"""
Keyword-based news classifier for Kocaeli news articles.

Classifies articles into one of 5 mandatory categories using keyword matching.
Priority order (highest → lowest):
  1. Trafik Kazası       (Traffic Accident)
  2. Yangın              (Fire)
  3. Hırsızlık          (Theft / Burglary)
  4. Elektrik Kesintisi  (Power Outage)
  5. Kültürel Etkinlikler (Cultural Events)
  6. Diğer              (Other – fallback)

When multiple categories match, the highest-priority one wins.

Matching strategy:
  • Normal keywords  → compiled as \\b<word>\\b  (whole-word match)
  • Prefix keywords (start with ^) → compiled as \\b<stem>  (prefix match)
    This handles Turkish agglutinative suffixes:
      ^dolandır  matches  dolandırıcı, dolandırıldığını, dolandırılma …
"""

from __future__ import annotations

import re
from typing import Optional

# ── Category constants ────────────────────────────────────────────────────────

CAT_YANGIN          = "Yangın"
CAT_TRAFIK          = "Trafik Kazası"
CAT_HIRSIZLIK       = "Hırsızlık"
CAT_ELEKTRIK        = "Elektrik Kesintisi"
CAT_KULTUR          = "Kültürel Etkinlikler"
CAT_DIGER           = "Diğer"

# Priority list – first match wins.
PRIORITY: list[str] = [
    CAT_TRAFIK,
    CAT_YANGIN,
    CAT_HIRSIZLIK,
    CAT_ELEKTRIK,
    CAT_KULTUR,
]

# ── Keyword dictionary ────────────────────────────────────────────────────────
# Rules:
#   • Normal keyword:  matched as WHOLE WORD (\b...\b)
#   • ^prefix keyword: matched as PREFIX only (\b...) — no trailing boundary
#     so Turkish suffixes (-ıcı, -dığını, -arak, etc.) are captured.
#   • Prefer multi-word phrases over single words to reduce false-positives.

KEYWORDS: dict[str, list[str]] = {
    CAT_TRAFIK: [
        # Compound phrases
        "trafik kazası", "zincirleme kaza", "feci kaza",
        "kazada yaralı", "kazada hayatını",
        "kaza sonucu", "maddi hasarlı kaza",
        # Single word — \bkaza\b won't match "kazandı"
        "kaza",
        # Araç hareketleri
        "devrildi", "takla attı", "şarampole", "bariyere çarptı",
        "çarpıştı", "çarpışma", "çarptı",
        "yayaya çarptı", "kafa kafaya",
        "kamyon devrildi", "tır devrildi", "otobüs kazası",
        "motosiklet kazası", "servis kazası",
        "araç takla", "köprüde kaza", "tünelde kaza",
        "kavşakta kaza", "yol kapandı",
        # Sürücü davranışları
        "alkollü sürücü", "makas attı", "kırmızı ışık ihlali",
        "sürücü hayatını kaybetti",
    ],
    CAT_YANGIN: [
        "yangın", "yangında", "yangını",
        "alev", "alevler", "alev topuna",
        "tutuştu", "yandı", "yanarak",
        "kundak", "kundaklama",
        "orman yangın", "bina yandı", "ev yandı", "fabrika yangın",
        "depo yandı", "araç yandı", "arazi yangını",
        "büyük yangın", "yangına müdahale",
    ],
    CAT_HIRSIZLIK: [
        "hırsızlık", "hırsız",
        "çalındı", "çalıntı",
        "gasp", "soygun", "soygunu", "soydu",
        "kapkaç",
        # Compound phrases
        "kablo hırsız", "kablo çalındı", "metal hırsız",
        "evden hırsızlık", "iş yerinden çalındı",
        "banka soygunu", "market soygunu", "kasa kırdı",
        # Dolandırıcılık — prefix match ile tüm Türkçe çekimlerini yakala
        # ^dolandır → dolandırıcı, dolandırıcılık, dolandırıldı,
        #             dolandırıldığını, dolandırılma, dolandırma …
        "^dolandır",
        "vurgun", "vurgunu",
    ],
    CAT_ELEKTRIK: [
        "elektrik kesintisi", "elektrik kesildi", "elektrik yok",
        "enerji kesintisi", "planlı kesinti",
        "elektrik arızası", "şebeke arızası",
        # Elektrik çarpması
        "elektrik akımına", "akıma kapıldı",
        "elektrik çarptı", "elektrik çarpması",
        "yüksek gerilim",
    ],
    CAT_KULTUR: [
        "konser", "sergi", "tiyatro", "festival",
        "müzik", "sinema",
        "gösteri", "panayır", "şenlik",
        "fuar", "kermes",
        "açılış töreni", "ödül töreni",
        "^ödül",              # ödül, ödüllerini, ödülleri …
        "söyleşi", "konferans", "sempozyum",
        "halk konseri", "dans gösterisi", "tiyatro oyunu",
        "bilim festivali", "kariyer günü",
        # Spor / Turnuvalar
        "turnuva", "derbi",
        "^şampiyon",         # şampiyon, şampiyonluk, şampiyona …
        "play-off", "playoff",
        "milli takım",
        # NOT: "kültür", "sanat" kaldırıldı — belediye haberlerinde
        #      "kültür merkezi", "sanat galerisi" olarak çok sık geçiyor
        #      ve yanlış pozitif veriyor.
        # NOT: "lig", "maç" kaldırıldı — çok genel, içerikte her yerde
        #      geçebilir ("süper lig" başlıkta zaten şampiyon/playoff
        #      ile birlikte gelir).
    ],
}


# ── Compile keyword patterns ─────────────────────────────────────────────────
# • Normal:  \b<word>\b     (whole word)
# • Prefix:  \b<stem>       (^prefix convention)
# Longest-first sort ensures multi-word phrases are tried before single words.

_COMPILED_PATTERNS: dict[str, list[re.Pattern[str]]] = {}

for _cat, _kw_list in KEYWORDS.items():
    sorted_kws = sorted(_kw_list, key=len, reverse=True)
    patterns = []
    for kw in sorted_kws:
        if kw.startswith("^"):
            # Prefix match — no trailing \b
            stem = kw[1:]
            patterns.append(re.compile(r"\b" + re.escape(stem), re.IGNORECASE))
        else:
            # Full word match
            patterns.append(re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE))
    _COMPILED_PATTERNS[_cat] = patterns


# ── Core classifier ───────────────────────────────────────────────────────────

CONTENT_HIT_THRESHOLD: int = 3
"""Minimum distinct keyword hits required in the article BODY (not title)
to classify the article. Title needs only 1 hit (high-confidence signal).
Set to 3 to prevent false positives from long articles that incidentally
mention category keywords (e.g. a metro article mentioning 'kültür merkezi').
"""


def _count_category_hits(text: str, category: str) -> int:
    """Count distinct keyword matches in text, deduplicating overlapping spans."""
    spans: list[tuple[int, int]] = []
    for pat in _COMPILED_PATTERNS.get(category, []):
        for m in pat.finditer(text):
            spans.append((m.start(), m.end()))

    if not spans:
        return 0

    # Merge overlapping spans
    spans.sort()
    merged: list[tuple[int, int]] = [spans[0]]
    for s, e in spans[1:]:
        prev_s, prev_e = merged[-1]
        if s <= prev_e:
            merged[-1] = (prev_s, max(prev_e, e))
        else:
            merged.append((s, e))

    return len(merged)


def classify_news(title: str, content: str = "") -> str:
    """
    Classify a news article into one of the 5 mandatory categories.

    Strategy (two-pass):
      Pass 1 – TITLE ONLY: If any keyword from a category appears in the
               title, that category is classified immediately (1 hit enough).
      Pass 2 – CONTENT BODY: If no title match, scan the content body.
               Require ≥CONTENT_HIT_THRESHOLD (3) distinct keyword hits to
               reduce false positives from lengthy articles mentioning
               category words incidentally.

    Args:
        title:   Article headline.
        content: Article body (optional, improves accuracy).

    Returns:
        One of the 6 category constants (CAT_* or CAT_DIGER).
    """
    title_lower = title.lower()
    content_lower = (content or "").lower()

    # ── Pass 1: title-only (high confidence, 1 hit is enough) ──
    title_matched: set[str] = set()
    for category, patterns in _COMPILED_PATTERNS.items():
        for pat in patterns:
            if pat.search(title_lower):
                title_matched.add(category)
                break

    for category in PRIORITY:
        if category in title_matched:
            return category

    # ── Pass 2: content body (lower confidence, need ≥3 hits) ──
    if content_lower:
        content_matched: set[str] = set()
        for category in PRIORITY:
            hits = _count_category_hits(content_lower, category)
            if hits >= CONTENT_HIT_THRESHOLD:
                content_matched.add(category)

        for category in PRIORITY:
            if category in content_matched:
                return category

    return CAT_DIGER
