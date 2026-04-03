"""
Location extractor for news articles – Hybrid NER + Dictionary approach.

Strategy (4 layers, applied in order):

  Layer 0 – "X Mahallesi/Mah." context regex (NEW):
    Scans text for the pattern "[Name] Mahallesi/Mah./Mh." and extracts the
    neighbourhood name verbatim. This is the most precise layer and gets
    absolute priority. No risk of false positives since "Mahalle" suffix is
    required. The neighbourhood name is passed to the geocoder separately.

  Layer 1 – Neighbourhood / place-level dictionary:
    Known Kocaeli neighbourhoods, campuses, streets etc. are mapped to their
    parent district. Only *distinctive* place names are included here — common
    Turkish words (emek, özgürlük…) are NOT added and must be caught via
    Layer 0 (with the "Mahalle" context).

  Layer 2 – spaCy multilingual NER (xx_ent_wiki_sm):
    LOC / GPE entities detected by the model are normalised and looked up in
    the combined district + neighbourhood dictionaries.

  Layer 3 – District alias regex fallback:
    A regex scan over the 12 canonical district names and their common
    alternative spellings. Runs when layers 0-2 find nothing.

Graceful degradation: if spaCy or its model is unavailable the module falls
back silently to layers 0, 1 and 3 only.

Returns:
  - district      : normalised district name (first / best match)
  - neighborhood  : most specific place found (from Layer 0), or None
  - locations     : deduplicated list of all matched districts
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
# NOTE: Only add *distinctive* place names here (≥8 chars, not common Turkish words).
# Ambiguous short names (emek, özgürlük, akse…) must be caught via Layer 0
# (the "[Name] Mahallesi" context pattern) to avoid false positives.

NEIGHBORHOOD_TO_DISTRICT: dict[str, str] = {
    # ── İzmit ──────────────────────────────────────────────────────────────
    "yahyakaptan": "İzmit",
    "yenidogan": "İzmit",
    "yenidoğan": "İzmit",
    "seka park": "İzmit",
    "plajyolu": "İzmit",
    "fethiye caddesi": "İzmit",
    "yuruyus yolu": "İzmit",
    "kurucesme": "İzmit",
    "kuruçeşme": "İzmit",
    "alikahya": "İzmit",
    "kozluk": "İzmit",
    "tepecik": "İzmit",
    "tavşantepe": "İzmit",
    "tavşantepe": "İzmit",
    "çukurbey": "İzmit",
    "cukurbey": "İzmit",
    "yeşilova": "İzmit",
    "yesilova": "İzmit",
    "gundogdu": "İzmit",
    "gündoğdu": "İzmit",
    "topçular": "İzmit",
    "topcular": "İzmit",
    "orhantepe": "İzmit",
    "bağçeşme": "İzmit",
    "bagcesme": "İzmit",
    # NOT: 'serdar' kaldırıldı — Türkçe'de yaygın kişi adı, false positive riski yüksek
    "kabaoğlu": "İzmit",
    "kabaoglu": "İzmit",
    "durhasan": "İzmit",
    "aziziye": "İzmit",
    "arızlı": "İzmit",
    "arizli": "İzmit",
    "malta": "İzmit",
    # ── Gebze ───────────────────────────────────────────────────────────────
    "mutlukent": "Gebze",
    # NOT: "tübitak" kaldırıldı — kurum adı olarak haberlerde çok sık geçer
    # (örn. "TÜBİTAK raporu", "TÜBİTAK ödülü") ve yanlış Gebze tespitine
    # neden olur. Sadece kampüs referansı "tübitak mam" bırakıldı.
    "tübitak mam": "Gebze",
    "tubitak mam": "Gebze",
    "guzeller osb": "Gebze",
    "güzeller osb": "Gebze",
    "plastikciler osb": "Gebze",
    "plastikçiler osb": "Gebze",
    "tatlikuyu": "Gebze",
    "tatlıkuyu": "Gebze",
    "arapcesme": "Gebze",
    "arapçeşme": "Gebze",
    "pelitli": "Gebze",
    "sultanorhan": "Gebze",
    "güzeller": "Gebze",
    "guzeller": "Gebze",
    "deri osb": "Gebze",
    "bağarası": "Gebze",
    "bagarasi": "Gebze",
    # ── Derince ─────────────────────────────────────────────────────────────
    "yenikent": "Derince",
    "cenedag": "Derince",
    "çenedağ": "Derince",
    "sirripasa": "Derince",
    "sırrıpaşa": "Derince",
    "harikalar sahili": "Derince",
    "60 evler": "Derince",
    "tavşanlı": "Derince",
    "tavsanli": "Derince",
    "esadiye": "Derince",
    # ── Körfez ──────────────────────────────────────────────────────────────
    "yarimca": "Körfez",
    "yarımca": "Körfez",
    "tutunciftlik": "Körfez",
    "tütünçiftlik": "Körfez",
    "hereke": "Körfez",
    "sirinyali": "Körfez",
    "şirinyalı": "Körfez",
    # NOT: "kullar" Başiskele'ye taşındı (aşağıda)
    "rahmiye": "Körfez",
    "subaşı": "Körfez",
    "subasi": "Körfez",
    # ── Kartepe ─────────────────────────────────────────────────────────────
    "masukiye": "Kartepe",
    "maşukiye": "Kartepe",
    "derbent": "Kartepe",
    "suadiye": "Kartepe",
    "arslanbey": "Kartepe",
    "uzunciftlik": "Kartepe",
    "uzunçiftlik": "Kartepe",
    "kosekoy": "Kartepe",
    "köseköy": "Kartepe",
    "yeniköy": "Kartepe",
    "yenikoy": "Kartepe",
    # NOT: İhsaniye Kartepe değil, Karamürsel ilçesine bağlıdır.
    # ── Başiskele ───────────────────────────────────────────────────────────
    "yuvacik": "Başiskele",
    "yuvacık": "Başiskele",
    "bahcecik": "Başiskele",
    "bahçecik": "Başiskele",
    "karsiyaka": "Başiskele",
    "karşıyaka": "Başiskele",
    "başiskele merkez": "Başiskele",
    "körkuyu": "Başiskele",
    "korkuyu": "Başiskele",
    "ovacık": "Başiskele",
    "ovacik": "Başiskele",
    "kullar": "Başiskele",
    # ── Gölcük ──────────────────────────────────────────────────────────────
    "degirmendere": "Gölcük",
    "değirmendere": "Gölcük",
    "halidere": "Gölcük",
    "ulasli": "Gölcük",
    "ulaşlı": "Gölcük",
    "kavakli": "Gölcük",
    "kavaklı": "Gölcük",
    "nenehatun": "Gölcük",
    "yazlık": "Gölcük",
    "yazlik": "Gölcük",
    # ── Karamürsel ──────────────────────────────────────────────────────────
    "herşik": "Karamürsel",
    "hersik": "Karamürsel",
    "altinkemer": "Karamürsel",
    "altınkemer": "Karamürsel",
    "tepekoy": "Karamürsel",
    "tepeköy": "Karamürsel",
    "karamürsel merkez": "Karamürsel",
    "ihsaniye": "Karamürsel",
    "İhsaniye": "Karamürsel",
    # ── Darıca ──────────────────────────────────────────────────────────────
    "bayramoglu": "Darıca",
    "bayramoğlu": "Darıca",
    "osmangazi": "Darıca",
    # ── Çayırova ────────────────────────────────────────────────────────────
    "sekerpinar": "Çayırova",
    "şekerpınar": "Çayırova",
    "çayırova merkez": "Çayırova",
    # ── Dilovası ────────────────────────────────────────────────────────────
    "mermerciler": "Dilovası",
    "komurculer": "Dilovası",
    "kömürcüler": "Dilovası",
    "tavsancil": "Dilovası",
    "tavşancıl": "Dilovası",
    "diliskelesi": "Dilovası",
    # ── Kandıra ─────────────────────────────────────────────────────────────
    # NOT: 'kandira' burada yok — Kandıra DISTRICT_ALIASES'da tanımlı (ilçe adı, mahalle değil)
    "kefken": "Kandıra",
    "kerpe": "Kandıra",
    "cebeci": "Kandıra",
    "babali": "Kandıra",
    "babalı": "Kandıra",
}


# ── POI (Points of Interest) → district/neighborhood mapping ──────────────────
# Bilindik kurumlar, yapılar ve mekanlar — TAM İSİM eşleşmesi yapılır,
# yanlış pozitif riskini minimize etmek için minimum ~10 karakter uzunluğunda
# ve Kocaeli'ye özgü isimler seçilmiştir.

POI_TO_LOCATION: dict[str, tuple[str, Optional[str]]] = {
    # Değer: (district, neighborhood_for_geocoder)
    # neighborhood=None → sadece ilçe hassasiyetinde koordinat

    # ── Üniversiteler ───────────────────────────────────────────────────────
    "kocaeli universitesi": ("İzmit", "Umuttepe"),
    "kocaeli üniversitesi": ("İzmit", "Umuttepe"),
    "kou kampus": ("İzmit", "Umuttepe"),
    "umuttepe kampus": ("İzmit", "Umuttepe"),
    "umuttepe kampüs": ("İzmit", "Umuttepe"),
    "gebze teknik universitesi": ("Gebze", "Gebze Teknik Üniversitesi"),
    "gebze teknik üniversitesi": ("Gebze", "Gebze Teknik Üniversitesi"),
    "gtu kampus": ("Gebze", "Gebze Teknik Üniversitesi"),
    "gtu muzesi": ("Gebze", "Gebze Teknik Üniversitesi"),
    "gtu muze": ("Gebze", "Gebze Teknik Üniversitesi"),
    "kou umuttepe": ("İzmit", "Umuttepe"),
    "kou kampusu": ("İzmit", "Umuttepe"),
    "izmit universitesi": ("İzmit", None),

    # ── Hastaneler ──────────────────────────────────────────────────────────
    "kocaeli devlet hastanesi": ("İzmit", None),
    "kocaeli egitim arastirma hastanesi": ("İzmit", None),
    "kocaeli eğitim araştırma hastanesi": ("İzmit", None),
    "izmit devlet hastanesi": ("İzmit", None),
    "gebze fatih devlet hastanesi": ("Gebze", None),
    "gebze devlet hastanesi": ("Gebze", None),
    "golcuk devlet hastanesi": ("Gölcük", None),
    "gölcük devlet hastanesi": ("Gölcük", None),
    "darıca farabi hastanesi": ("Darıca", None),
    "darica farabi hastanesi": ("Darıca", None),
    "kartepe devlet hastanesi": ("Kartepe", None),
    "kandıra devlet hastanesi": ("Kandıra", None),
    "kandira devlet hastanesi": ("Kandıra", None),
    "karamürsel devlet hastanesi": ("Karamürsel", None),
    "karamursel devlet hastanesi": ("Karamürsel", None),
    "derince egitim arastirma hastanesi": ("Derince", None),
    "derince eğitim araştırma hastanesi": ("Derince", None),
    "değirmendere devlet hastanesi": ("Gölcük", "Değirmendere"),
    "degirmendere devlet hastanesi": ("Gölcük", "Değirmendere"),
    "körfez devlet hastanesi": ("Körfez", None),
    "korfez devlet hastanesi": ("Körfez", None),
    "kocaeli sehir hastanesi": ("Başiskele", None),
    "kocaeli şehir hastanesi": ("Başiskele", None),

    # ── Stadlar & Spor Tesisleri ────────────────────────────────────────────
    "kocaeli stadyumu": ("İzmit", None),
    "izmit stadyumu": ("İzmit", None),
    "seka stadyumu": ("İzmit", None),
    "kocaelispor stadyumu": ("İzmit", None),
    "körfez spor merkezi": ("Körfez", None),
    "korfez spor merkezi": ("Körfez", None),
    "gebze spor tesisi": ("Gebze", None),
    "darıca spor merkezi": ("Darıca", None),
    "darica spor merkezi": ("Darıca", None),

    # ── Alışveriş Merkezleri ────────────────────────────────────────────────
    "izmit aqua": ("İzmit", None),
    "aqua kocaeli": ("İzmit", None),
    "izmit park avm": ("İzmit", None),
    "gebze center": ("Gebze", None),
    "gebze plaza": ("Gebze", None),
    "migros kocaeli": ("İzmit", None),
    "carrefour kocaeli": ("İzmit", None),

    # ── Camiler ─────────────────────────────────────────────────────────────
    "sabanci camii kocaeli": ("İzmit", None),
    "sabancı camii kocaeli": ("İzmit", None),
    "pertevniyal camii": ("İzmit", None),
    "hereke camii": ("Körfez", "Hereke"),
    "yahyakaptan camii": ("İzmit", "Yahyakaptan"),
    "maşukiye camii": ("Kartepe", "Maşukiye"),
    "masukiye camii": ("Kartepe", "Maşukiye"),
    "gebze merkez camii": ("Gebze", None),
    "golcuk camii": ("Gölcük", None),
    "gölcük camii": ("Gölcük", None),

    # ── Parklar & Sahiller ──────────────────────────────────────────────────
    "seka park": ("İzmit", "Seka Park"),
    "kocaeli millet bahcesi": ("İzmit", None),
    "kocaeli millet bahçesi": ("İzmit", None),
    "izmit kordon": ("İzmit", None),
    "korfez sahili": ("Körfez", None),
    "körfez sahili": ("Körfez", None),
    "golcuk sahili": ("Gölcük", None),
    "gölcük sahili": ("Gölcük", None),
    "harikalar sahili": ("Derince", None),
    "karamursel sahili": ("Karamürsel", None),
    "karamürsel sahili": ("Karamürsel", None),
    "hereke sahili": ("Körfez", "Hereke"),
    "masukiye tabiat parki": ("Kartepe", "Maşukiye"),
    "maşukiye tabiat parkı": ("Kartepe", "Maşukiye"),
    "korfez belediye parki": ("Körfez", None),

    # ── Organize Sanayi Bölgeleri ───────────────────────────────────────────
    "losb": ("Dilovası", None),
    "kosbi": ("Gebze", None),
    "gebze osb": ("Gebze", None),
    "izmit osb": ("İzmit", None),
    "tuzla osb": ("Gebze", None),
    "körfez osb": ("Körfez", None),
    "korfez osb": ("Körfez", None),
    "cayirova osb": ("Çayırova", None),
    "çayırova osb": ("Çayırova", None),

    # ── Okullar (bilindik ve özgün isimler) ────────────────────────────────
    "izmit anadolu lisesi": ("İzmit", None),
    "kocaeli anadolu lisesi": ("İzmit", None),
    "gebze anadolu lisesi": ("Gebze", None),
    "darıca anadolu lisesi": ("Darıca", None),
    "darica anadolu lisesi": ("Darıca", None),
    "gölcük anadolu lisesi": ("Gölcük", None),
    "golcuk anadolu lisesi": ("Gölcük", None),
    "kartepe anadolu lisesi": ("Kartepe", None),
    "karamursel anadolu lisesi": ("Karamürsel", None),
    "karamürsel anadolu lisesi": ("Karamürsel", None),
    "hereke anadolu lisesi": ("Körfez", "Hereke"),

    # ── Diğer Önemli Noktalar ───────────────────────────────────────────────
    "kocaeli buyuksehir belediyesi": ("İzmit", None),
    "kocaeli büyükşehir belediyesi": ("İzmit", None),
    "izmit belediyesi": ("İzmit", None),
    "gebze belediyesi": ("Gebze", None),
    "golcuk belediyesi": ("Gölcük", None),
    "gölcük belediyesi": ("Gölcük", None),
    "darıca belediyesi": ("Darıca", None),
    "darica belediyesi": ("Darıca", None),
    "kartepe belediyesi": ("Kartepe", None),
    "korfez belediyesi": ("Körfez", None),
    "körfez belediyesi": ("Körfez", None),
    "derince belediyesi": ("Derince", None),
    "basciskele belediyesi": ("Başiskele", None),
    "başiskele belediyesi": ("Başiskele", None),
    "cayirova belediyesi": ("Çayırova", None),
    "çayırova belediyesi": ("Çayırova", None),
    "kandira belediyesi": ("Kandıra", None),
    "kandıra belediyesi": ("Kandıra", None),
    "karamursel belediyesi": ("Karamürsel", None),
    "karamürsel belediyesi": ("Karamürsel", None),
    "dilovasi belediyesi": ("Dilovası", None),
    "dilovası belediyesi": ("Dilovası", None),
    "kocaeli emniyet mudurlugu": ("İzmit", None),
    "kocaeli emniyet müdürlüğü": ("İzmit", None),
    "kocaeli valiligi": ("İzmit", None),
    "kocaeli valiliği": ("İzmit", None),
    "izmit adliyesi": ("İzmit", None),
    "kocaeli adliyesi": ("İzmit", None),
    "gebze adliyesi": ("Gebze", None),
    "yuvacik baraji": ("Başiskele", "Yuvacık"),
    "yuvacık barajı": ("Başiskele", "Yuvacık"),
    "izmit korfezi": ("İzmit", None),
    "izmit körfezi": ("İzmit", None),
    "tübitak marmara arastirma merkezi": ("Gebze", None),
    "tübitak marmara araştırma merkezi": ("Gebze", None),
    "tubitak marmara arastirma merkezi": ("Gebze", None),

    # ── Karayolları – D100 (eski E5) ───────────────────────────────────────
    "d-100": ("İzmit", None),
    "d100": ("İzmit", None),
    "d 100": ("İzmit", None),
    "e-5": ("İzmit", None),
    "e5 yolu": ("İzmit", None),
    "eski e5": ("İzmit", None),
    "d100 karayolu": ("İzmit", None),
    "d-100 karayolu": ("İzmit", None),
    # İlçe bazlı D100
    "gebze d100": ("Gebze", None),
    "çayırova d100": ("Çayırova", None),
    "cayirova d100": ("Çayırova", None),
    "darıca d100": ("Darıca", None),
    "darica d100": ("Darıca", None),
    "körfez d100": ("Körfez", None),
    "korfez d100": ("Körfez", None),
    "derince d100": ("Derince", None),
    "izmit d100": ("İzmit", None),

    # ── TEM Otoyolu ─────────────────────────────────────────────────────────
    "tem otoyolu": ("İzmit", None),
    "tem yolu": ("İzmit", None),
    "tem": ("İzmit", None),          # TEM'de kaza / TEM geçişinde
    "gebze tem": ("Gebze", None),
    "çayırova tem": ("Çayırova", None),
    "cayirova tem": ("Çayırova", None),
    "izmit tem": ("İzmit", None),
    "körfez tem": ("Körfez", None),
    "korfez tem": ("Körfez", None),
    "o-2 otoyolu": ("İzmit", None),
    "o2 otoyolu": ("İzmit", None),

    # ── O-4 / Gebze-Orhangazi-İzmir Otoyolu ────────────────────────────────
    "o-4 otoyolu": ("Gebze", None),
    "o4 otoyolu": ("Gebze", None),
    "gebze orhangazi otoyol": ("Gebze", None),
    "osmangazi köprüsü": ("Gebze", None),
    "osmangazi koprusu": ("Gebze", None),

    # ── Kavşaklar & Özel Yol Noktaları ─────────────────────────────────────
    "gebze kavşağı": ("Gebze", None),
    "gebze kavsagi": ("Gebze", None),
    "çayırova kavşağı": ("Çayırova", None),
    "cayirova kavsagi": ("Çayırova", None),
    "körfez kavşağı": ("Körfez", None),
    "korfez kavsagi": ("Körfez", None),
    "derince kavşağı": ("Derince", None),
    "derince kavsagi": ("Derince", None),
    "yarımca kavşağı": ("Körfez", "Yarımca"),
    "yarimca kavsagi": ("Körfez", "Yarımca"),
    "hereke kavşağı": ("Körfez", "Hereke"),
    "hereke kavsagi": ("Körfez", "Hereke"),
    "gebze çıkışı": ("Gebze", None),
    "gebze cikisi": ("Gebze", None),
    "izmit çıkışı": ("İzmit", None),
    "izmit cikisi": ("İzmit", None),

    # ── Köprüler & Tüneller ─────────────────────────────────────────────────
    "değirmendere köprüsü": ("Gölcük", "Değirmendere"),
    "degirmendere koprusu": ("Gölcük", "Değirmendere"),
    "dilovası tüneli": ("Dilovası", None),
    "dilovasi tuneli": ("Dilovası", None),

    # ── Liman Yolu – Derince ────────────────────────────────────────────────
    "derince liman yolu": ("Derince", None),
    "liman yolu": ("Derince", None),
    "derince limanı": ("Derince", None),
    "derince limani": ("Derince", None),

    # ── D-130 / İzmit-Kandıra ───────────────────────────────────────────────
    "d-130": ("İzmit", None),
    "d130": ("İzmit", None),
    "kandıra yolu": ("Kandıra", None),
    "kandira yolu": ("Kandıra", None),

    # ── D-140 / İzmit-Karamürsel ────────────────────────────────────────────
    "d-140": ("Karamürsel", None),
    "d140": ("Karamürsel", None),
    "karamürsel yolu": ("Karamürsel", None),
    "karamursel yolu": ("Karamürsel", None),

    # ── Diğer bilindik yollar ───────────────────────────────────────────────
    "izmit ankara yolu": ("İzmit", None),
    "ankara yolu izmit": ("İzmit", None),
    "istanbul yolu kocaeli": ("Gebze", None),
}


# ── Layer 0: "X Mahallesi/Mah." pattern ──────────────────────────────────────
# Catches any mention of a neighbourhood when followed by "Mahalle" context.
# Rules: max 2 words, no punctuation/apostrophes → prevents greedy over-matching.

_TR_CHARS = r"A-Za-z\u00c7\u00e7\u011e\u011f\u0130\u0131\u00d6\u00f6\u015e\u015f\u00dc\u00fc"

_MAHALLE_PATTERN = re.compile(
    r"(?<!['\u2019\w])"                          # not preceded by apostrophe/word char
    r"([" + _TR_CHARS + r"]{3,}"                 # first word: ≥3 Turkish letters
    r"(?:\s+[" + _TR_CHARS + r"]{2,})?)"         # optional second word only
    r"\s+(?:mahallesi|mahalle|mah\.|mh\.)",
    re.IGNORECASE | re.UNICODE,
)


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
    district = NEIGHBORHOOD_TO_DISTRICT.get(norm)
    if district:
        return district
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


def _build_neighbourhood_patterns() -> list[tuple[re.Pattern[str], str, str]]:
    """Compile regex patterns for neighbourhood → district matching (longest first).
    
    Returns list of (pattern, district, canonical_neighbourhood_name).
    canonical_neighbourhood_name is the properly capitalised Turkish form.
    """
    # Map normalised_key → (district, best_raw_key)
    # "best" = the raw key with most Turkish characters (longest after normalise strip)
    entries: dict[str, tuple[str, str]] = {}
    for raw_key, district in NEIGHBORHOOD_TO_DISTRICT.items():
        norm = _normalise(raw_key)
        existing = entries.get(norm)
        # Prefer key with Turkish diacritics (it will be longer or equal in char count)
        if not existing or len(raw_key) >= len(existing[1]):
            entries[norm] = (district, raw_key)

    sorted_entries = sorted(entries.items(), key=lambda x: len(x[0]), reverse=True)
    return [
        (re.compile(r"\b" + re.escape(k) + r"\b", re.IGNORECASE), dist, raw.title())
        for k, (dist, raw) in sorted_entries
    ]


# Module-level compiled patterns (built once at import time)
_DISTRICT_PATTERNS = _build_district_patterns()
_NEIGHBOURHOOD_PATTERNS = _build_neighbourhood_patterns()

# POI patterns: sorted longest first to prefer most specific match
_POI_PATTERNS: list[tuple[re.Pattern[str], tuple[str, Optional[str]]]] = sorted(
    [
        (re.compile(r"\b" + re.escape(_normalise(k)) + r"\b", re.IGNORECASE), v)
        for k, v in POI_TO_LOCATION.items()
    ],
    key=lambda x: len(x[0].pattern),
    reverse=True,
)


# ── Layer implementations ─────────────────────────────────────────────────────

def _layer0_mahalle_context(title: str, content: str) -> tuple[Optional[str], Optional[str]]:
    """
    Layer 0: scan for '[Name] Mahallesi/Mah.' patterns.

    Searches title and content *separately* to prevent word bleeding across
    the boundary (e.g. last word of title + first word of content).

    Returns (neighbourhood_name, district) where district is looked up from
    our dict if known, otherwise None (name still returned for geocoder).
    """
    # Turkish suffixes that indicate the first word is NOT a proper noun
    # but a common word that leaked into the regex match.
    # e.g. "geçişi Malta Mahallesi" → "geçişi" is not a place name
    _NON_NAME_SUFFIXES = (
        "si", "sı", "ın", "in", "un", "ün",        # possessive/genitive
        "da", "de", "ta", "te",                       # locative
        "nda", "nde",                                  # locative with n-buffer
        "dan", "den",                                  # ablative
        "ya", "ye", "na", "ne",                        # dative
    )

    for text in (title, content):
        match = _MAHALLE_PATTERN.search(text)
        if match:
            neighbourhood = match.group(1).strip()

            words = neighbourhood.split()
            if len(words) >= 2:
                first_word = words[0]
                first_word_norm = _normalise(first_word)

                # Case 1: first word is a district name → strip it, use as district
                if first_word_norm in DISTRICT_ALIASES or any(
                    _normalise(d) == first_word_norm for d in KOCAELI_DISTRICTS
                ):
                    inferred_district = DISTRICT_ALIASES.get(first_word_norm) or next(
                        (d for d in KOCAELI_DISTRICTS if _normalise(d) == first_word_norm), None
                    )
                    neighbourhood = " ".join(words[1:])
                    district = inferred_district or _lookup_in_dictionaries(neighbourhood)
                    logger.debug(
                        f"[extractor] Layer 0 hit (district-prefix stripped): "
                        f"'{neighbourhood}' Mahallesi → district={district}"
                    )
                    return neighbourhood, district

                # Case 2: first word starts with lowercase OR ends with a
                # Turkish grammatical suffix → it's a leaked common word,
                # not a proper noun. Strip it and keep only the second word.
                # Examples: "geçişi Malta", "yılında Kayacık", "ilçesi Malta"
                is_lowercase_start = first_word[0].islower()
                has_suffix = any(first_word_norm.endswith(s) for s in _NON_NAME_SUFFIXES)

                if is_lowercase_start or has_suffix:
                    neighbourhood = " ".join(words[1:])
                    logger.debug(
                        f"[extractor] Layer 0: stripped non-name prefix "
                        f"'{first_word}' → neighbourhood='{neighbourhood}'"
                    )

            district = _lookup_in_dictionaries(neighbourhood)
            logger.debug(f"[extractor] Layer 0 hit: '{neighbourhood}' Mahallesi → district={district}")
            return neighbourhood, district
    return None, None



def _layer05_poi(combined_norm: str) -> tuple[Optional[str], Optional[str]]:
    """
    Layer 0.5: Scan for known Kocaeli POI names (hospitals, universities,
    mosques, parks, malls, stadiums, schools, municipal buildings...).

    Uses normalised (diacritic-free) text for matching.
    Patterns sorted longest-first to prefer most specific hit.

    Returns (district, neighborhood_hint) or (None, None).
    """
    for pattern, (district, neighborhood) in _POI_PATTERNS:
        if pattern.search(combined_norm):
            logger.debug(
                f"[extractor] Layer 0.5 POI hit: '{pattern.pattern}' "
                f"→ district={district}, neighborhood={neighborhood}"
            )
            return district, neighborhood
    return None, None


def _layer1_dictionary(combined_norm: str, combined_raw: str) -> tuple[list[str], Optional[str]]:
    """Neighbourhood + district regex scan over normalised + raw text.
    
    Returns (districts_list, first_neighbourhood_canonical_name).
    """
    matched: list[str] = []
    seen: set[str] = set()
    first_neighbourhood: Optional[str] = None

    for pattern, district, canonical in _NEIGHBOURHOOD_PATTERNS:
        m = pattern.search(combined_norm)
        if m:
            if district not in seen:
                matched.append(district)
                seen.add(district)
            # Use the pre-built canonical name (e.g. "Değirmendere", "Maşukiye")
            # Minimum 5 chars to avoid short person-name false positives
            if first_neighbourhood is None and len(canonical) >= 5:
                first_neighbourhood = canonical

    return matched, first_neighbourhood


def _layer2_spacy(combined_raw: str) -> list[str]:
    """Use spaCy NER to find LOC/GPE entities, map them to districts."""
    nlp = _get_nlp()
    if not nlp:
        return []

    matched: list[str] = []
    seen: set[str] = set()

    try:
        doc = nlp(combined_raw[:5000])
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
    Scan title and content for Kocaeli location names using a hybrid
    4-layer strategy: mahalle context → neighbourhood dict → spaCy NER → district regex.

    Returns:
        {
          "district"     : Optional[str]  – primary matched district,
          "neighborhood" : Optional[str]  – most specific place (mahalle name),
          "locations"    : list[str]      – all unique matched districts,
        }
    """
    combined_raw = f"{title} {content}"
    combined_norm = _normalise(combined_raw)

    neighbourhood: Optional[str] = None
    poi_neighborhood: Optional[str] = None

    # Layer 0: "[Name] Mahallesi" context – highest precision
    neighbourhood, l0_district = _layer0_mahalle_context(title, content)
    results: list[str] = [l0_district] if l0_district else []

    # Layer 0.5: POI dictionary (hospitals, universities, mosques etc.)
    if not results:
        poi_district, poi_neighborhood = _layer05_poi(combined_norm)
        if poi_district:
            results = [poi_district]
            # POI neighborhood hint (e.g. "Maşukiye" for Kartepe hospital)
            if poi_neighborhood and not neighbourhood:
                neighbourhood = poi_neighborhood

    # Layer 1: neighbourhood / place-level dictionary
    if not results:
        results, l1_neighbourhood = _layer1_dictionary(combined_norm, combined_raw)
        # Use Layer 1 neighbourhood hint if Layer 0 found nothing
        if l1_neighbourhood and not neighbourhood:
            neighbourhood = l1_neighbourhood

    # Layer 2: spaCy NER (adds entities not caught by sözlük)
    if not results:
        results = _layer2_spacy(combined_raw)

    # Layer 3: district alias regex fallback
    if not results:
        results = _layer3_district_regex(combined_norm)

    # Deduplicate while preserving order
    seen: set[str] = set()
    locations: list[str] = []
    for d in results:
        if d not in seen:
            locations.append(d)
            seen.add(d)

    district: Optional[str] = locations[0] if locations else None

    return {
        "district": district,
        "neighborhood": neighbourhood,
        "locations": locations,
    }


def build_geocode_query(
    district: Optional[str],
    neighborhood: Optional[str] = None,
    city: str = "Kocaeli",
) -> Optional[str]:
    """
    Compose the address string to send to the Google Geocoding API.

    If a neighbourhood is known, it is prepended for higher precision:
      "Yahyakaptan Mahallesi, İzmit, Kocaeli, Turkey"
    If district is unknown but neighbourhood is known:
      "Yahyakaptan Mahallesi, Kocaeli, Turkey"
    Otherwise falls back to district-level:
      "Gebze, Kocaeli, Turkey"
    """
    if neighborhood and district:
        return f"{neighborhood} Mahallesi, {district}, {city}, Turkey"
    elif neighborhood:
        return f"{neighborhood} Mahallesi, {city}, Turkey"
    elif district:
        return f"{district}, {city}, Turkey"
    return None
