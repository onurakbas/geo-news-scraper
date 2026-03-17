# TODO - Geo News Scraper

## 1. Ortam ve Kurulumlar (Mac + Homebrew)

- [x] Xcode Command Line Tools kur:
  - Komut: xcode-select --install
- [x] Homebrew güncelle:
  - Komut: brew update

### 1.1 MongoDB Kurulumu ve Çalıştırma

- [x] MongoDB tap ekle:
  - Komut: brew tap mongodb/brew
- [x] MongoDB Community sürümünü kur:
  - Komut: brew install mongodb-community@8.0
- [x] MongoDB servisini başlat:
  - Komut: brew services start mongodb-community@8.0
- [x] MongoDB durumunu kontrol et:
  - Komut: brew services list
- [x] Mongosh kur (gerekliyse):
  - Komut: brew install mongosh
- [x] Ping testi yap:
  - Komut: mongosh --eval "db.runCommand({ ping: 1 })"
- [x] Gerekirse durdur/yeniden başlat:
  - Komut: brew services stop mongodb-community@8.0
  - Komut: brew services restart mongodb-community@8.0

### 1.2 Node.js Kurulumu

- [x] Node.js LTS kur:
  - Komut: brew install node
- [x] Sürümleri doğrula:
  - Komut: node -v
  - Komut: npm -v

### 1.3 Python ve venv Kurulumu

- [x] Python sürümünü doğrula:
  - Komut: python3 --version
- [x] Ana dizinde sanal ortam oluştur:
  - Komut: python3 -m venv .venv
- [x] Sanal ortamı aktive et:
  - Komut: source .venv/bin/activate
- [x] Pip araçlarını güncelle:
  - Komut: python -m pip install --upgrade pip setuptools wheel

### 1.4 Backend Kütüphaneleri Kurulumu

- [x] API ve DB paketlerini kur:
  - Komut: pip install fastapi uvicorn pymongo motor pydantic pydantic-settings python-dotenv
- [x] Scraping paketlerini kur:
  - Komut: pip install scrapy beautifulsoup4 lxml newspaper3k requests httpx
- [x] NLP/Embedding paketlerini kur:
  - Komut: pip install sentence-transformers scikit-learn numpy scipy pandas rapidfuzz
- [x] Konum/geocoding yardımcı paketlerini kur:
  - Komut: pip install googlemaps tenacity
- [x] Yardımcı kalite paketlerini kur:
  - Komut: pip install loguru python-dateutil
- [x] Test/lint/format paketlerini kur:
  - Komut: pip install pytest pytest-asyncio pytest-cov black ruff mypy pre-commit

### 1.5 Frontend Kurulumu

- [x] Vite + React + TypeScript projesi oluştur:
  - Komut: npm create vite@latest frontend -- --template react-ts
- [x] Frontend bağımlılıklarını kur:
  - Komut: cd frontend && npm install
- [x] API/State/Map paketlerini kur:
  - Komut: npm install axios @tanstack/react-query @react-google-maps/api zod dayjs react-router-dom
- [x] Test ve kalite paketlerini kur:
  - Komut: npm install -D vitest @testing-library/react @testing-library/jest-dom eslint prettier eslint-config-prettier

### 1.6 Kurulum Kayıt Disiplini

- [x] Ana dizinde install_log.md dosyasını oluştur.
- [x] Her kurulumdan sonra şu bilgileri işle:
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

- [x] Hedef haber sitelerini ve selector stratejilerini dokümante et.
- [x] Scrapy spider dosyalarını oluştur.
- [x] Her kaynak için parser yaz (başlık, tarih, içerik, tür, URL).
- [x] Retry, timeout ve user-agent rotasyonu ekle.
- [x] Duplicate URL kontrolü ekle.
- [x] Scrape çıktısını ham ve işlenmiş olarak logla.
- [x] İlk örnek veri setini MongoDB news koleksiyonuna yaz.

## 5. NLP ve Embedding Tabanlı Tekilleştirme

- [x] Metin temizleme pipeline'ı oluştur (HTML temizleme, normalizasyon).
- [x] Embedding modeli seç ve sabitle.
- [x] Her haber için embedding üret.
- [x] Aday eşleşmeleri filtrele:
  - aynı gün aralığı
  - benzer başlık ipuçları
- [x] Cosine similarity hesapla.
- [x] Eşik kuralını uygula:
  - similarity >= 0.90 ise tekilleştir
- [x] Tekilleştirme kararını veri modelinde sakla (similarity_group_id).
- [x] Eşiği doğrulamak için manuel örnekleme raporu hazırla.

## 6. Konum Çıkarımı ve Geocoding

- [x] Haber metninden konum çıkarımı stratejisini belirle (NER + sözlük yaklaşımı).
- [x] Çıkarılan konumları normalize et (il/ilçe adları).
- [x] Google Geocoding API istemcisini yaz.
- [x] Rate limit ve retry mekanizması ekle.
- [x] Geocode cache kullan (aynı adresi tekrar çağırma).
- [x] Başarılı koordinatları news dokümanına yaz.

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
