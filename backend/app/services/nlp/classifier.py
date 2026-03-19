"""
Keyword-based news classifier for Kocaeli news articles.

Classifies articles into one of 5 mandatory categories using keyword matching.
Priority order (highest → lowest):
  1. Yangın              (Fire)
  2. Trafik Kazası       (Traffic Accident)
  3. Hırsızlık          (Theft / Burglary)
  4. Elektrik Kesintisi  (Power Outage)
  5. Kültürel Etkinlikler (Cultural Events)
  6. Diğer              (Other – fallback)

When multiple categories match, the highest-priority one wins.
"""

from __future__ import annotations

# ── Category constants ────────────────────────────────────────────────────────

CAT_YANGIN          = "Yangın"
CAT_TRAFIK          = "Trafik Kazası"
CAT_HIRSIZLIK       = "Hırsızlık"
CAT_ELEKTRIK        = "Elektrik Kesintisi"
CAT_KULTUR          = "Kültürel Etkinlikler"
CAT_DIGER           = "Diğer"

# Priority list – first match wins
PRIORITY: list[str] = [
    CAT_YANGIN,
    CAT_TRAFIK,
    CAT_HIRSIZLIK,
    CAT_ELEKTRIK,
    CAT_KULTUR,
]

# ── Keyword dictionary ────────────────────────────────────────────────────────

KEYWORDS: dict[str, list[str]] = {
    CAT_YANGIN: [
        "yangın", "yangin", "itfaiye", "alev", "alevler", "tutuştu",
        "yandı", "yaldi", "yanarak", "kundak", "kundaklama",
        "dumana", "duman", "köy yaktı", "orman yangın", "bina yandı",
        "çıktı alev", "büyük yangın", "söndürme", "yangına müdahale",
        "arazi yangını", "ev yandı", "fabrika yangın", "depo yandı",
    ],
    CAT_TRAFIK: [
        "kaza", "trafik kazası", "trafik kazasi", "çarpıştı", "carpisma",
        "çarpışma", "devrildi", "takla attı", "şarampol", "bariyere çarptı",
        "zincirleme kaza", "kazada yaralı", "kazada hayatını", "feci kaza",
        "araç çarptı", "motosiklet kazası", "tır devrildi", "otobüs kazası",
        "minibüs", "alkollü sürücü", "hız", "makas attı",
        "yayaya çarptı", "kırmızı ışık", "kafa kafaya",
    ],
    CAT_HIRSIZLIK: [
        "hırsız", "hirsiz", "hırsızlık", "hirsizlik", "çalındı",
        "gasp", "soygun", "soygunu", "dolandırıcı", "dolandırıcılık",
        "kapkaç", "kapkac", "evden hırsızlık", "iş yerinden çalındı",
        "motosiklet çalındı", "araç çalındı", "güvenlik kamerası",
        "soydu", "yakalandı hırsız", "banka soygunu", "kasa kırdı",
        "market soygunu", "zimmet", "sahte para",
    ],
    CAT_ELEKTRIK: [
        "elektrik kesintisi", "elektrik kesintis", "elektrik yok",
        "elektrik arızası", "arıza", "elektrik kesildi", "kesinti",
        "aydınlatma sorunu", "trafo", "enerji kesintisi", "tedaş",
        "akım kesintisi", "şebeke arızası", "elektrik şebekesi",
        "planlı kesinti", "bakım çalışması", "elektrik bağlantı",
    ],
    CAT_KULTUR: [
        "konser", "sergi", "tiyatro", "festival", "etkinlik",
        "kültür", "kultur", "sanat", "müzik", "muzik",
        "sinema", "gösteri", "gosteri", "panayır", "panayir",
        "şenlik", "senligi", "fuar", "açılış töreni", "kermes",
        "yarışma", "turnuva", "ödül töreni", "kitap fuarı",
        "söyleşi", "konferans", "sempozyum", "sergi açılış",
        "halk konseri", "dans gösterisi", "tiyatro oyunu",
    ],
}

# ── Core classifier ───────────────────────────────────────────────────────────

def classify_news(title: str, content: str = "") -> str:
    """
    Classify a news article into one of the 5 mandatory categories.

    Args:
        title:   Article headline.
        content: Article body (optional, improves accuracy).

    Returns:
        One of the 6 category constants (CAT_* or CAT_DIGER).
    """
    combined = f"{title} {content}".lower()

    matched: set[str] = set()
    for category, keywords in KEYWORDS.items():
        for kw in keywords:
            if kw in combined:
                matched.add(category)
                break  # one hit per category is enough

    # Apply priority order – return the highest-priority match
    for category in PRIORITY:
        if category in matched:
            return category

    return CAT_DIGER
