# News Radar — Kocaeli Coğrafi Haber Takip Sistemi

> **Yazılım Laboratuvarı 2 · Proje 1**  
> 5 yerel haber sitesinden otomatik veri toplayan, haberleri NLP ile sınıflandıran, coğrafi konumları tespit edip Google Maps üzerinde görselleştiren full-stack bir web uygulaması.

---

## İçindekiler

- [Proje Hakkında](#proje-hakkında)
- [Mimari](#mimari)
- [Teknoloji Yığını](#teknoloji-yığını)
- [Ön Koşullar](#ön-koşullar)
- [Kurulum](#kurulum)
  - [1 — MongoDB](#1--mongodb)
  - [2 — Backend (Python)](#2--backend-python)
  - [3 — Frontend (Node.js)](#3--frontend-nodejs)
  - [4 — Ortam Değişkenleri](#4--ortam-değişkenleri)
- [Uygulamayı Çalıştırma](#uygulamayı-çalıştırma)
- [Kullanım](#kullanım)
- [API Referansı](#api-referansı)
- [Proje Yapısı](#proje-yapısı)
- [Sistem Nasıl Çalışır](#sistem-nasıl-çalışır)
  - [Scraping Pipeline](#scraping-pipeline)
  - [NLP Sınıflandırma](#nlp-sınıflandırma)
  - [Coğrafi Konum Tespiti](#coğrafi-konum-tespiti)
  - [Embedding Tabanlı Tekilleştirme](#embedding-tabanlı-tekilleştirme)
- [Haber Kaynakları](#haber-kaynakları)
- [Yazarlar](#yazarlar)

---

## Proje Hakkında

**News Radar**, Kocaeli ilindeki 5 yerel haber sitesini düzenli olarak tarayan, haberleri otomatik olarak 5 kategoriye sınıflandıran ve her haberin geçtiği ilçeyi veya mahalleyi tespit ederek interaktif bir harita üzerinde pin olarak gösteren tam yığın (full-stack) bir haber takip sistemidir.

### Temel Özellikler

- **Otomatik Scraping** — 5 haber sitesi paralel Scrapy spider'larıyla son 72 saatin haberleri çekilir; her sunucu başlangıcında arka planda tetiklenir.
- **Anahtar Kelime Tabanlı Sınıflandırma** — Türkçe morfolo­jisine uygun prefix-eşleme desteğiyle haberler 5 zorunlu kategoriye atanır.
- **Hibrit Coğrafi Tespit (4 Katman)** — "X Mahallesi" bağlam regex → Mahalle/POI sözlüğü → spaCy NER → ilçe alias regex zinciriyle konumlar çıkarılır; ardından Google Geocoding API ile koordinata dönüştürülür.
- **Embedding Tabanlı Tekilleştirme** — `sentence-transformers` ile üretilen vektörlerin kosinus benzerliği ≥ 0.90 olan haberler tek grup altında birleştirilir; aynı haberi farklı sitelerden bağlayan kaynaklar birleşik gösterilir.
- **İnteraktif Harita** — Kategori rengine göre farklı ikonlu pin'ler; ilçe, zaman aralığı, tür filtreleri; marker tıklandığında detay paneli açılır, kaynak site(ler)e doğrudan yönlendirme yapılır.
- **Dark / Light Tema** — Tek tıkla tam tema değiştirme.

### Haber Kategorileri

| Kategori | Renk | İkon |
|---|---|---|
| Trafik Kazası | Amber (`#f59e0b`) | Araç |
| Yangın | Kırmızı (`#ef4444`) | Alev |
| Hırsızlık | Mor (`#a855f7`) | Kilit |
| Elektrik Kesintisi | Mavi-beyaz (`#b6c4ff`) | Şimşek |
| Kültürel Etkinlikler | Pembe (`#a43d77`) | Nota |

---

## Mimari

```
┌──────────────────────────────────────────────────────────────┐
│                       FRONTEND  (React + Vite)               │
│  ┌─────────────┐  ┌──────────────────┐  ┌────────────────┐  │
│  │  Sol Panel  │  │  Google Maps     │  │  Detay Sidebar │  │
│  │  (Filtreler │  │  OverlayView     │  │  (Haber Detay) │  │
│  │  + Liste)   │  │  Marker Pin'ler  │  │                │  │
│  └──────┬──────┘  └────────┬─────────┘  └───────┬────────┘  │
│         └─────────────────┴────────────────────┘           │
│                     Axios + TanStack Query                  │
└────────────────────────────┬─────────────────────────────────┘
                             │ HTTP  REST
┌────────────────────────────▼─────────────────────────────────┐
│                    BACKEND  (FastAPI + Uvicorn)               │
│  ┌──────────────┐  ┌───────────────┐  ┌────────────────────┐ │
│  │ /api/v1/news │  │ /api/v1/scrape│  │  /health           │ │
│  │ /map/markers │  │ /trigger      │  │                    │ │
│  │ /filters     │  │ /status       │  │                    │ │
│  └──────┬───────┘  └───────┬───────┘  └────────────────────┘ │
│         │                  │                                  │
│  ┌──────▼──────────────────▼──────────────────────────────┐  │
│  │                 Service Layer                          │  │
│  │  ┌────────────┐  ┌────────────┐  ┌──────────────────┐  │  │
│  │  │  Scrapy    │  │    NLP     │  │    Geocoding     │  │  │
│  │  │  Spiders   │  │  Pipeline  │  │    Pipeline      │  │  │
│  │  │  (×5 site) │  │  classify  │  │  4-layer hybrid  │  │  │
│  │  │            │  │  dedup     │  │  + Google API    │  │  │
│  │  └─────┬──────┘  └─────┬──────┘  └────────┬─────────┘  │  │
│  └────────┼───────────────┼──────────────────┼────────────┘  │
└───────────┼───────────────┼──────────────────┼───────────────┘
            │               │                  │
┌───────────▼───────────────▼──────────────────▼───────────────┐
│                    MongoDB  (geo_news)                        │
│   news  │  geocode_cache  │  ingest_logs  │  sources         │
└──────────────────────────────────────────────────────────────┘
```

---

## Teknoloji Yığını

### Backend

| Teknoloji | Versiyon | Kullanım |
|---|---|---|
| Python | 3.13 | Çalışma zamanı |
| FastAPI | ≥ 0.111 | REST API çerçevesi |
| Uvicorn | ≥ 0.29 | ASGI sunucu |
| Scrapy | ≥ 2.11 | Web scraping |
| Motor | ≥ 3.4 | Async MongoDB sürücüsü |
| PyMongo | ≥ 4.7 | Sync MongoDB (pipeline/dedup) |
| sentence-transformers | ≥ 3.0 | Haber embedding'i |
| scikit-learn / numpy | — | Kosinus benzerliği |
| googlemaps | ≥ 4.10 | Geocoding API istemcisi |
| spaCy (`xx_ent_wiki_sm`) | — | Varlık tanıma (NER) |
| Pydantic v2 | ≥ 2.7 | Veri doğrulama |
| loguru | ≥ 0.7 | Yapılandırılmış loglama |

### Frontend

| Teknoloji | Versiyon | Kullanım |
|---|---|---|
| React | 19 | UI çerçevesi |
| TypeScript | 5 | Tip güvenliği |
| Vite | 8 | Geliştirme sunucusu / bundler |
| @react-google-maps/api | ≥ 2.20 | Google Maps entegrasyonu |
| TanStack React Query | v5 | Sunucu durumu yönetimi |
| Axios | ≥ 1.13 | HTTP istemcisi |
| Tailwind CSS | v4 | Stil |
| lucide-react | — | İkonlar |
| Zod | v4 | Şema doğrulama |

### Altyapı

| Teknoloji | Kullanım |
|---|---|
| MongoDB Community 8.0 | Birincil veritabanı |
| Google Geocoding API | Adres → koordinat dönüşümü |
| Google Maps JS API | Harita görüntüleme |

---

## Ön Koşullar

Aşağıdakilerin kurulu ve çalışır olduğunu doğrulayın:

- **macOS** (Homebrew ile test edildi; Linux'ta da çalışır)
- **Python 3.11+** — `python3 --version`
- **Node.js 20 LTS+** — `node -v`
- **MongoDB Community 8.0** — `brew services list | grep mongo`
- **Google Cloud Console'da etkinleştirilmiş iki API anahtarı:**
  - Maps JavaScript API (frontend harita)
  - Geocoding API (backend koordinat)

---

## Kurulum

### 1 — MongoDB

```bash
# Homebrew tap (bir kez)
brew tap mongodb/brew
brew install mongodb-community@8.0

# Servisi başlat
brew services start mongodb-community@8.0

# Çalıştığını doğrula
mongosh --eval "db.runCommand({ ping: 1 })"
# Beklenen: { ok: 1 }
```

> **Linux kullanıcıları:** `apt` veya `dnf` ile [resmi MongoDB belgelerini](https://www.mongodb.com/docs/manual/installation/) izleyin.

---

### 2 — Backend (Python)

```bash
# Repoyu klonla ve proje dizinine gir
git clone <repo-url>
cd geo-news-scraper

# Sanal ortam oluştur ve aktive et
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# pip araçlarını güncelle
python -m pip install --upgrade pip setuptools wheel

# Tüm bağımlılıkları kur
pip install -r backend/requirements.txt

# spaCy çok dilli NER modelini indir (konum tespiti için)
python -m spacy download xx_ent_wiki_sm
```

---

### 3 — Frontend (Node.js)

```bash
cd frontend
npm install
```

---

### 4 — Ortam Değişkenleri

#### Backend `.env`

Proje kök dizininde (yani `geo-news-scraper/`) bir `.env` dosyası oluşturun:

```bash
cp .env.example .env
```

Ardından dosyayı kendi değerlerinizle doldurun:

```dotenv
# ─── MongoDB ───────────────────────────────────────────────────
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB_NAME=geo_news

# ─── Google APIs ───────────────────────────────────────────────
# Bu iki anahtar farklı API'lere ait olabilir veya aynı proje altında verilebilir.
GOOGLE_GEOCODING_API_KEY=AIza...        # Geocoding API
GOOGLE_MAPS_JS_API_KEY=AIza...          # Maps JavaScript API

# ─── Scraper ───────────────────────────────────────────────────
# Her saat başı otomatik scrape (isteğe bağlı, sunucu başlangıcında zaten çalışır)
SCRAPE_SCHEDULE_CRON=0 * * * *

# ─── CORS ──────────────────────────────────────────────────────
CORS_ORIGINS=http://localhost:5173
```

#### Frontend `.env`

`frontend/` dizininde bir `.env` dosyası oluşturun:

```dotenv
VITE_API_BASE_URL=http://localhost:8000
VITE_GOOGLE_MAPS_API_KEY=AIza...    # Maps JavaScript API anahtarı
```

> **Güvenlik notu:** `.env` dosyaları `.gitignore`'a eklidir; **asla commit etmeyin.**

---

## Uygulamayı Çalıştırma

İki ayrı terminal sekmesi açın.

### Terminal 1 — Backend

```bash
# Proje kök dizininde, sanal ortam aktifken:
source .venv/bin/activate
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Sunucu başladığında arka planda otomatik olarak bir scrape turu başlar. Logları izleyin:

```
INFO     🚀 Server started – launching background scrape...
INFO     🕷️  [cagdas_kocaeli] → başladı
INFO     🕷️  [ozgur_kocaeli]  → başladı
...
INFO     🗺️  Geocoding tamamlandı
INFO     🔗 Deduplication tamamlandı
```

API dokümantasyonuna erişin: [http://localhost:8000/docs](http://localhost:8000/docs)

### Terminal 2 — Frontend

```bash
cd frontend
npm run dev
```

Uygulama şu adreste açılır: [http://localhost:5173](http://localhost:5173)

---

## Kullanım

Uygulama açıldıktan sonra:

1. **Harita otomatik yüklenir** — Backend'deki son scrape sonuçları gösterilir. Her marker bir haber olayını temsil eder; rengi kategorisine göre değişir.

2. **Sol panel filtreler:**
   - **İlçe** — Kocaeli'nin 12 ilçesinden birini seçin.
   - **Zaman Aralığı** — Son 24 saat / Son 3 gün veya özel tarih aralığı.
   - **Olay Türü** — Kategorilere göre checkbox filtresi.
   - **Arama kutusu** (üstteki header) — Başlık veya ilçe adına göre anlık filtreleme.

3. **Marker'a tıklayın** — Sağdan açılan detay panelinde başlık, tarih, ilçe/mahalle, kaynak site(ler) ve orijinal habere giden bağlantı gösterilir.

4. **Veri Çek butonu** — Sol panelin alt kısmındaki buton yeni bir scrape başlatır; dönen ok animasyonu işlemin devam ettiğini gösterir. Tamamlandığında harita otomatik güncellenir.

5. **Tema butonu** (sağ üst) — Dark/Light mod geçişi.

---

## API Referansı

Tüm endpoint'ler `http://localhost:8000/api/v1` altındadır.  
Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)

### Haberler

#### `GET /news`

Sayfalanmış haber listesi döner. Tekilleştirilmiş haberler grup temsilcisiyle gösterilir.

| Parametre | Tip | Açıklama |
|---|---|---|
| `date_from` | string (ISO 8601) | Başlangıç tarihi — örn. `2024-03-01` |
| `date_to` | string (ISO 8601) | Bitiş tarihi |
| `type` | string | Kategori filtresi — örn. `Yangın` |
| `district` | string | İlçe filtresi — örn. `İzmit` |
| `page` | int (≥1) | Sayfa numarası (varsayılan: 1) |
| `page_size` | int (1–100) | Sayfa başı kayıt (varsayılan: 20) |

```bash
curl "http://localhost:8000/api/v1/news?type=Yangın&district=Gebze&page=1"
```

#### `GET /news/filters`

Mevcut kategori ve ilçe listelerini döner (dropdown menü için).

```bash
curl "http://localhost:8000/api/v1/news/filters"
```

#### `GET /news/map/markers`

Koordinatlı tüm haberleri harita pin formatında döner (sayfalama yok; client-side cluster uygulanır).

```bash
curl "http://localhost:8000/api/v1/news/map/markers?type=Trafik+Kazası"
```

**Yanıt örneği:**
```json
{
  "markers": [
    {
      "_id": "665abc...",
      "title": "D-100'de zincirleme kaza: 3 yaralı",
      "type": "Trafik Kazası",
      "district": "Gebze",
      "neighborhood": "Şekerpınar",
      "lat": 40.7821,
      "lon": 29.4432,
      "sources": ["Bizim Yaka", "Çağdaş Kocaeli"],
      "urls": ["https://...", "https://..."],
      "published_at": "2024-03-15T10:30:00"
    }
  ],
  "total": 1
}
```

#### `GET /news/{news_id}`

Tekil haber detayını döner.

```bash
curl "http://localhost:8000/api/v1/news/665abc123def456"
```

### Scrape Kontrol

#### `POST /scrape/trigger`

Tüm spider'ları arka planda başlatır. Zaten çalışıyorsa `409 Conflict` döner.

```bash
curl -X POST "http://localhost:8000/api/v1/scrape/trigger"
```

#### `GET /scrape/status`

Mevcut scrape durumunu döner.

```bash
curl "http://localhost:8000/api/v1/scrape/status"
```

**Yanıt örneği:**
```json
{
  "status": "idle",
  "last_run": "2024-03-15T12:00:00+00:00",
  "last_error": null,
  "inserted": 0,
  "dropped": 0
}
```

#### `GET /health`

Sunucu sağlık kontrolü.

```bash
curl "http://localhost:8000/health"
# {"status": "ok"}
```

---

## Proje Yapısı

```
geo-news-scraper/
│
├── .env.example                   # Ortam değişkenleri şablonu
├── .env                           # Kendi değerleriniz (git'e eklenmez)
│
├── backend/
│   ├── requirements.txt
│   └── app/
│       ├── main.py                # FastAPI uygulama girişi, lifespan, CORS
│       ├── core/
│       │   └── config.py          # Pydantic-Settings ile .env okuma
│       ├── api/
│       │   └── v1/
│       │       ├── router.py      # Ana router (news + scrape)
│       │       ├── schemas.py     # Response Pydantic şemaları
│       │       └── endpoints/
│       │           ├── news.py    # GET /news, /filters, /map/markers, /{id}
│       │           └── scrape.py  # POST /trigger, GET /status
│       ├── db/
│       │   ├── client.py          # Motor bağlantısı (connect/disconnect/get)
│       │   ├── indexes.py         # MongoDB indeks tanımları
│       │   └── repositories/
│       │       ├── news_repository.py    # Tüm news sorguları
│       │       └── geocode_cache.py      # Geocode cache CRUD
│       ├── models/
│       │   ├── news.py            # NewsBase / NewsInDB / NewsOut
│       │   ├── geocode_cache.py
│       │   ├── ingest_log.py
│       │   └── source.py
│       └── services/
│           ├── scraper/
│           │   ├── runner.py      # Paralel subprocess yönetimi
│           │   ├── pipelines.py   # Validation → DateFilter → RawHtml → Mongo
│           │   ├── settings.py    # Scrapy ayarları
│           │   ├── items.py       # NewsItem tanımı
│           │   ├── middlewares.py # TLS impersonation download handler
│           │   ├── handlers.py
│           │   ├── parsers/
│           │   │   ├── date_parser.py   # Türkçe tarih parse
│           │   │   └── text_cleaner.py  # HTML → temiz metin
│           │   └── spiders/
│           │       ├── base_spider.py   # Ortak spider mantığı
│           │       ├── bizim_yaka.py
│           │       ├── cagdas_kocaeli.py
│           │       ├── ozgur_kocaeli.py
│           │       ├── ses_kocaeli.py
│           │       └── yeni_kocaeli.py
│           ├── nlp/
│           │   ├── classifier.py  # Anahtar kelime tabanlı 5-kategori sınıflandırma
│           │   ├── deduplicator.py # Embedding + Union-Find tekilleştirme
│           │   └── embedder.py    # sentence-transformers batch embed
│           └── geocoding/
│               ├── extractor.py   # 4-katman konum çıkarımı
│               ├── maps.py        # Google Geocoding API istemcisi + cache
│               └── pipeline.py    # Toplu geocoding orchestrator
│
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
│       ├── main.tsx
│       ├── app/App.tsx
│       ├── pages/
│       │   └── MapPage.tsx        # Ana sayfa: harita + filtre paneli + liste
│       ├── components/
│       │   └── map/
│       │       └── MapContainer.tsx  # Google Maps + özel OverlayView pin'ler
│       ├── api/
│       │   ├── client.ts          # Axios instance
│       │   └── newsService.ts     # API çağrı fonksiyonları
│       ├── types/
│       │   └── news.ts            # TypeScript arayüz tanımları
│       └── styles/
│           └── index.css          # CSS değişkenleri, dark/light tema
│
├── scripts/
│   ├── run_spiders.py             # Scrapy CrawlerProcess başlatıcı
│   └── run_geocode.py             # Toplu geocoding scripti
│
├── data/
│   └── raw/                       # Spider'ların kaydettiği ham HTML'ler
│       ├── bizim_yaka/
│       ├── cagdas_kocaeli/
│       └── ...
│
└── docs/
    └── scraping-sources.md        # Spider selector stratejileri
```

---

## Sistem Nasıl Çalışır

### Scraping Pipeline

Sunucu başlatıldığında `lifespan` hook'u `run_spiders_background()` görevini başlatır. Manuel tetikleme için `POST /api/v1/scrape/trigger` da kullanılabilir.

**Adımlar:**

```
1. MongoDB news koleksiyonu temizlenir (taze veri için)
2. 5 spider asyncio.gather() ile paralel subprocess'te çalışır
   → Toplam süre en yavaş spider kadardır (seri değil)
3. Her spider BaseNewsSpider'dan miras alır:
   - 72 saatten eski haberlerde DateFilterPipeline öğeyi atar
   - URL unique index ile duplikasyon önlenir (MongoDB tarafı)
   - Scrapy DupeFilter ile aynı URL çalıştırma içinde iki kez ziyaret edilmez
   - Ham HTML data/raw/<spider>/<slug>.html olarak kaydedilir
4. Geocoding pipeline çalışır (aşağıya bakın)
5. Deduplication pipeline çalışır (aşağıya bakın)
6. Terminal'e özet tablo yazdırılır: kaynak bazlı sayılar, kategori bazlı sayılar
```

### NLP Sınıflandırma

`classifier.py` her haber için **iki aşamalı** kural tabanlı sınıflandırma uygular:

- **Geçiş 1 (Başlık)** — Başlıkta bir anahtar kelime bulunursa o kategori hemen döner (1 eşleşme yeterli, yüksek güven).
- **Geçiş 2 (İçerik)** — Başlıkta eşleşme yoksa içerikte ≥ 3 farklı kelime eşleşmesi aranır; uzun haberlerde yanlış pozitifi önler.

Türkçe çekimlerine uyum için iki eşleşme modu:
- **Tam kelime:** `\bkaza\b` — "kazandı" veya "kazanma" eşleşmez.
- **Prefix:** `^dolandır` → `dolandırıcı`, `dolandırıldığını`, `dolandırılma` gibi tüm çekimleri yakalar.

Öncelik sırası: `Trafik Kazası > Yangın > Hırsızlık > Elektrik Kesintisi > Kültürel Etkinlikler > Diğer`

### Coğrafi Konum Tespiti

`extractor.py` haber başlığı ve içeriğini 4 katmanlı bir stratejiyle tarar:

```
Katman 0 — "[İsim] Mahallesi/Mah." bağlam regex
           En yüksek hassasiyet; mahalle adını verbatim yakalar.
           Örn: "Yahyakaptan Mahallesi'nde yangın" → mahalle=Yahyakaptan, ilçe=İzmit

Katman 0.5 — POI (Point of Interest) sözlüğü
             600+ bilindik yer adı: hastaneler, üniversiteler, camiler, AVM'ler,
             yollar (D-100, TEM, O-4), OSB'ler, köprüler...
             Örn: "Kocaeli Şehir Hastanesi" → ilçe=Başiskele

Katman 1 — Mahalle sözlüğü (400+ mahalle → ilçe eşleşmesi)
           Yalnızca ayırt edici yer adları; kısa/yaygın sözcükler dahil değil.

Katman 2 — spaCy xx_ent_wiki_sm NER (LOC/GPE varlıklar)
           Model yüklü değilse sessizce atlanır.

Katman 3 — İlçe alias regex (fallback)
           12 ilçe adı + yaygın yazım varyantları (ğ→g, ı→i vb.)
```

Konum bulunursa `build_geocode_query()` bir adres string'i oluşturur ve `maps.py` Google Geocoding API'ye gönderir. Aynı adres tekrar sorgulanmadan önce `geocode_cache` koleksiyonundan kontrol edilir.

### Embedding Tabanlı Tekilleştirme

`deduplicator.py` `sentence-transformers` modeliyle her haber için yoğun vektör üretir:

1. **Embedding üretimi** — `embed_batch()` ile 256'lı gruplar halinde işlenir; vektörler MongoDB'ye kaydedilir (sonraki çalıştırmalarda yeniden hesaplanmaz).
2. **Tarih penceresi** — Aralarında 3 günden fazla fark olan haberler karşılaştırılmaz.
3. **Kosinus benzerliği** — L2-normalize edilmiş vektörler için `vᵢ · vⱼ` = cosine(i, j). Eşik: **0.90**.
4. **Union-Find (path compression)** — Transitif gruplamayı verimli şekilde çözer; A≈B ve B≈C ise üçü aynı grupta olur.
5. **`similarity_group_id` yazımı** — Grup temsilcisinin `_id`'si tüm grup üyelerine yazılır. API, grup üyelerinin `sources` ve `urls` dizilerini birleştirerek tek yanıt döner.

---

## Haber Kaynakları

| # | Site | URL | Spider |
|---|---|---|---|
| 1 | Çağdaş Kocaeli | https://www.cagdaskocaeli.com.tr/ | `cagdas_kocaeli.py` |
| 2 | Özgür Kocaeli | https://www.ozgurkocaeli.com.tr/ | `ozgur_kocaeli.py` |
| 3 | SES Kocaeli | https://www.seskocaeli.com/ | `ses_kocaeli.py` |
| 4 | Yeni Kocaeli | https://www.yenikocaeli.com/ | `yeni_kocaeli.py` |
| 5 | Bizim Yaka | https://www.bizimyaka.com/ | `bizim_yaka.py` |

Her spider `BaseNewsSpider`'dan miras alır. Yeni kaynak eklemek için:
1. `spiders/` altına yeni `<site_adi>.py` dosyası oluşturun.
2. `source_label`, `start_urls`, `list_css`, `next_page_css` ve `parse_article()` tanımlayın.
3. `runner.py` içindeki `spider_names` listesine ekleyin.

---

## Yazarlar

**Yazılım Laboratuvarı 2 — Proje 1**

| Öğrenci No | Ad |
|---|---|
| 230201090 | Onur Akbaş |
| 240201120 | Dilay Dikbıyık |

---

<sub>Bu proje yalnızca eğitim amaçlıdır. Scraping işlemleri ilgili sitelerin `robots.txt` kurallarına uygun biçimde, makul istek gecikmeleriyle gerçekleştirilmektedir.</sub>
