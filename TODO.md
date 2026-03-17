# TODO - Geo News Scraper

## 1. Ortam ve Kurulumlar (Mac + Homebrew)

- [ ] Xcode Command Line Tools kur:
  - Komut: xcode-select --install
- [ ] Homebrew güncelle:
  - Komut: brew update

### 1.1 MongoDB Kurulumu ve Çalıştırma

- [ ] MongoDB tap ekle:
  - Komut: brew tap mongodb/brew
- [ ] MongoDB Community sürümünü kur:
  - Komut: brew install mongodb-community@8.0
- [ ] MongoDB servisini başlat:
  - Komut: brew services start mongodb-community@8.0
- [ ] MongoDB durumunu kontrol et:
  - Komut: brew services list
- [ ] Mongosh kur (gerekliyse):
  - Komut: brew install mongosh
- [ ] Ping testi yap:
  - Komut: mongosh --eval "db.runCommand({ ping: 1 })"
- [ ] Gerekirse durdur/yeniden başlat:
  - Komut: brew services stop mongodb-community@8.0
  - Komut: brew services restart mongodb-community@8.0

### 1.2 Node.js Kurulumu

- [ ] Node.js LTS kur:
  - Komut: brew install node
- [ ] Sürümleri doğrula:
  - Komut: node -v
  - Komut: npm -v

### 1.3 Python ve venv Kurulumu

- [ ] Python sürümünü doğrula:
  - Komut: python3 --version
- [ ] Ana dizinde sanal ortam oluştur:
  - Komut: python3 -m venv .venv
- [ ] Sanal ortamı aktive et:
  - Komut: source .venv/bin/activate
- [ ] Pip araçlarını güncelle:
  - Komut: python -m pip install --upgrade pip setuptools wheel

### 1.4 Backend Kütüphaneleri Kurulumu

- [ ] API ve DB paketlerini kur:
  - Komut: pip install fastapi uvicorn pymongo motor pydantic pydantic-settings python-dotenv
- [ ] Scraping paketlerini kur:
  - Komut: pip install scrapy beautifulsoup4 lxml newspaper3k requests httpx
- [ ] NLP/Embedding paketlerini kur:
  - Komut: pip install sentence-transformers scikit-learn numpy scipy pandas rapidfuzz
- [ ] Konum/geocoding yardımcı paketlerini kur:
  - Komut: pip install googlemaps tenacity
- [ ] Yardımcı kalite paketlerini kur:
  - Komut: pip install loguru python-dateutil
- [ ] Test/lint/format paketlerini kur:
  - Komut: pip install pytest pytest-asyncio pytest-cov black ruff mypy pre-commit

### 1.5 Frontend Kurulumu

- [ ] Vite + React + TypeScript projesi oluştur:
  - Komut: npm create vite@latest frontend -- --template react-ts
- [ ] Frontend bağımlılıklarını kur:
  - Komut: cd frontend && npm install
- [ ] API/State/Map paketlerini kur:
  - Komut: npm install axios @tanstack/react-query @react-google-maps/api zod dayjs react-router-dom
- [ ] Test ve kalite paketlerini kur:
  - Komut: npm install -D vitest @testing-library/react @testing-library/jest-dom eslint prettier eslint-config-prettier

### 1.6 Kurulum Kayıt Disiplini

- [ ] Ana dizinde install_log.md dosyasını oluştur.
- [ ] Her kurulumdan sonra şu bilgileri işle:
  - Tarih
  - Kurulan paket/uygulama
  - Sürüm
  - Kurulum komutu
  - Doğrulama komutu ve sonucu
  - Notlar

## 2. Proje İskeleti ve Konfigürasyon

- [x] Dizin yapısını planlanan ağaçla oluştur.
- [x] .gitignore dosyasını doldur (.venv, node_modules, .env, data/raw vb. hariç tut).
- [x] .env.example dosyasını hazırla:
  - MONGODB_URI
  - MONGODB_DB_NAME
  - GOOGLE_GEOCODING_API_KEY
  - GOOGLE_MAPS_JS_API_KEY
  - SCRAPE_SCHEDULE_CRON
- [x] Backend için temel FastAPI uygulamasını ayağa kaldır.
- [x] Frontend için temel Vite uygulamasını ayağa kaldır.
- [x] Health endpoint hazırla (/health).

## 3. MongoDB Tasarımı ve İndeksler

- [x] Koleksiyonları tanımla:
  - news
  - sources
  - geocode_cache
  - ingest_logs
- [x] news doküman şemasını netleştir:
  - source, url, title, content, published_at, type, district, city, locations, coordinates, embedding, similarity_group_id, created_at, updated_at
- [x] Temel indeksleri oluştur:
  - url unique index
  - published_at index
  - type index
  - district index
  - coordinates 2dsphere index
- [x] Geocode cache için unique address index ekle.

## 4. Web Scraping Katmanı

- [ ] Hedef haber sitelerini ve selector stratejilerini dokümante et.
- [ ] Scrapy spider dosyalarını oluştur.
- [ ] Her kaynak için parser yaz (başlık, tarih, içerik, tür, URL).
- [ ] Retry, timeout ve user-agent rotasyonu ekle.
- [ ] Duplicate URL kontrolü ekle.
- [ ] Scrape çıktısını ham ve işlenmiş olarak logla.
- [ ] İlk örnek veri setini MongoDB news koleksiyonuna yaz.

## 5. NLP ve Embedding Tabanlı Tekilleştirme

- [ ] Metin temizleme pipeline’ı oluştur (HTML temizleme, normalizasyon).
- [ ] Embedding modeli seç ve sabitle.
- [ ] Her haber için embedding üret.
- [ ] Aday eşleşmeleri filtrele:
  - aynı gün aralığı
  - benzer başlık ipuçları
- [ ] Cosine similarity hesapla.
- [ ] Eşik kuralını uygula:
  - similarity >= 0.90 ise tekilleştir
- [ ] Tekilleştirme kararını veri modelinde sakla (similarity_group_id).
- [ ] Eşiği doğrulamak için manuel örnekleme raporu hazırla.

## 6. Konum Çıkarımı ve Geocoding

- [ ] Haber metninden konum çıkarımı stratejisini belirle (NER + sözlük yaklaşımı).
- [ ] Çıkarılan konumları normalize et (il/ilçe adları).
- [ ] Google Geocoding API istemcisini yaz.
- [ ] Rate limit ve retry mekanizması ekle.
- [ ] Geocode cache kullan (aynı adresi tekrar çağırma).
- [ ] Başarılı koordinatları news dokümanına yaz.

## 7. Backend API Endpoint’leri

- [ ] GET /api/v1/news endpoint:
  - filtre: date_from, date_to, type, district, page, page_size
- [ ] GET /api/v1/filters endpoint:
  - mevcut türler ve ilçeler
- [ ] GET /api/v1/news/{id} detay endpoint
- [ ] GET /api/v1/map/markers endpoint (harita için optimize veri)
- [ ] Pydantic doğrulama ve hata mesajları ekle.
- [ ] OpenAPI dokümantasyonunu gözden geçir.
- [ ] Endpoint performansını test et.

## 8. React Harita ve Dinamik Filtreleme

- [ ] Harita sayfasını kur.
- [ ] Google Maps JS entegrasyonunu tamamla.
- [ ] Marker ve popup bileşenlerini hazırla.
- [ ] Filtre paneli oluştur:
  - tarih
  - tür
  - ilçe
- [ ] Sayfa yenilemeden veri çekme (React Query).
- [ ] URL query param senkronizasyonu ekle.
- [ ] Filtre değişimlerinde liste + haritayı eşzamanlı güncelle.
- [ ] Marker cluster ekleyerek yoğun veri performansını iyileştir.

## 9. Test ve Kalite

- [ ] Backend birim testleri (parser, dedup, geocode cache).
- [ ] Backend entegrasyon testleri (Mongo + API).
- [ ] Frontend bileşen testleri (filtreler, harita etkileşimi).
- [ ] API sözleşme testleri.
- [ ] Lint/format kuralları:
  - Python: ruff, black, mypy
  - Frontend: eslint, prettier
- [ ] Pre-commit hook’ları aktive et.

## 10. Güvenlik, Hata Yönetimi ve Gözlemlenebilirlik

- [ ] API anahtarlarını yalnızca .env içinde tut.
- [ ] İstek loglama ve hata loglama ekle.
- [ ] Kritik akışlar için structured logging kullan.
- [ ] Scraper ve geocoding hataları için fallback planı yaz.
- [ ] Basit rate limiting düşün.

## 11. Dokümantasyon ve Teslim Hazırlığı

- [ ] README’yi proje kurulum + çalıştırma + mimari ile tamamla.
- [ ] docs/architecture.md dosyasını doldur.
- [ ] docs/api-contract.md dosyasını endpoint örnekleriyle doldur.
- [ ] Son demo senaryosu hazırla:
  - scrape çalıştır
  - dedup sonucu göster
  - haritada filtrelerle gösterim yap
- [ ] Teslim öncesi son kontrol listesi:
  - tüm gereksinimler karşılandı mı
  - tekrar üretilebilir kurulum var mı
  - install_log.md güncel mi
