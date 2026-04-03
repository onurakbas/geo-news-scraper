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

IMPORTANT – Matching strategy:
  Each keyword is compiled as a regex with word-boundary markers (\b).
  This prevents substring false-positives such as "kazandı" matching "kaza".
"""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Optional

# ── Category constants ────────────────────────────────────────────────────────

CAT_YANGIN          = "Yangın"
CAT_TRAFIK          = "Trafik Kazası"
CAT_HIRSIZLIK       = "Hırsızlık"
CAT_ELEKTRIK        = "Elektrik Kesintisi"
CAT_KULTUR          = "Kültürel Etkinlikler"
CAT_DIGER           = "Diğer"

# Priority list – first match wins.
# Trafik Kazası is above Yangın because traffic accident news often mention
# "itfaiye" (fire department arrived) causing false Yangın hits.
PRIORITY: list[str] = [
    CAT_TRAFIK,
    CAT_YANGIN,
    CAT_HIRSIZLIK,
    CAT_ELEKTRIK,
    CAT_KULTUR,
]

# ── Keyword dictionary ────────────────────────────────────────────────────────
# Rules:
#   • Each keyword is matched as a WHOLE WORD (\b...\b regex).
#   • Prefer multi-word phrases over single words to reduce false-positives.
#   • Avoid overly generic words (arıza, trafo, kesinti, kısa devre, duman)
#     that appear in non-category contexts.

KEYWORDS: dict[str, list[str]] = {
    CAT_TRAFIK: [
        # Çok spesifik compound phrases
        "trafik kazası", "zincirleme kaza", "feci kaza",
        "kazada yaralı", "kazada hayatını",
        "kaza sonucu", "maddi hasarlı kaza",
        # Tek kelime "kaza" — regex \bkaza\b ile "kazandı" eşleşmez
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
        # Ana yangın kelimeleri (ASCII duplikatlar kaldırıldı)
        "yangın", "yangında", "yangını",
        "alev", "alevler", "alev topuna",
        "tutuştu", "yandı", "yanarak",
        "kundak", "kundaklama",
        # Compound phrases
        "orman yangın", "bina yandı", "ev yandı", "fabrika yangın",
        "depo yandı", "araç yandı", "arazi yangını",
        "büyük yangın", "yangına müdahale",
    ],
    CAT_HIRSIZLIK: [
        # Ana kelimeler (ASCII duplikatlar kaldırıldı)
        "hırsızlık", "hırsız",
        "çalındı", "çalıntı",
        "gasp", "soygun", "soygunu", "soydu",
        "kapkaç",
        # Compound phrases
        "kablo hırsız", "kablo çalındı", "metal hırsız",
        "evden hırsızlık", "iş yerinden çalındı",
        "banka soygunu", "market soygunu", "kasa kırdı",
    ],
    CAT_ELEKTRIK: [
        # Compound phrases (tek kelime "kesinti", "arıza", "trafo" kaldırıldı)
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
        "kültür", "sanat",
        "müzik", "sinema",
        "gösteri", "panayır", "şenlik",
        "fuar", "kermes",
        "açılış töreni", "ödül töreni",
        "söyleşi", "konferans", "sempozyum",
        "halk konseri", "dans gösterisi", "tiyatro oyunu",
        "bilim festivali", "kariyer günü",
        # NOT: "etkinlik" tek başına kaldırıldı — "verimlilik/etkinlik" anlamında
        # adliye/bürokratik haberlerde de geçiyor. "mezuniyet" de kaldırıldı — 
        # tören haberleri zaten "açılış töreni" veya "ödül töreni" ile yakalanır.
    ],
}



# ── Compile keyword patterns (word-boundary) ─────────────────────────────────
# Longest-first sort ensures multi-word phrases are tried before single words.

_COMPILED_PATTERNS: dict[str, list[re.Pattern[str]]] = {}

for _cat, _kw_list in KEYWORDS.items():
    # Sort keywords: longest first so "trafik kazası" is tested before "kaza"
    sorted_kws = sorted(_kw_list, key=len, reverse=True)
    _COMPILED_PATTERNS[_cat] = [
        re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE)
        for kw in sorted_kws
    ]


# ── Core classifier ───────────────────────────────────────────────────────────

def _count_category_hits(text: str, category: str) -> int:
    """Count distinct keyword matches in text, deduplicating overlapping spans.

    Keywords like 'orman yangın' and 'yangın' can overlap at the same text
    position. We collect all (start, end) match spans, then merge overlapping
    ones so that each real-world mention is counted only once.
    """
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
        if s <= prev_e:            # overlapping or adjacent
            merged[-1] = (prev_s, max(prev_e, e))
        else:
            merged.append((s, e))

    return len(merged)



def classify_news(title: str, content: str = "") -> str:
    """
    Classify a news article into one of the 5 mandatory categories.

    Strategy (two-pass):
      Pass 1 – TITLE ONLY: If any keyword from a category appears in the
               title, that category is a strong candidate (single hit enough).
      Pass 2 – CONTENT BODY: If no title match, scan the content. However,
               require at least 2 distinct keyword hits to reduce false
               positives from lengthy articles where incidental mentions of
               generic words (e.g. "yangın", "kaza") cause misclassification.

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

    # ── Pass 2: content body (lower confidence, need ≥2 hits) ──
    if content_lower:
        content_matched: set[str] = set()
        for category in PRIORITY:
            hits = _count_category_hits(content_lower, category)
            if hits >= 2:
                content_matched.add(category)

        for category in PRIORITY:
            if category in content_matched:
                return category

    return CAT_DIGER
