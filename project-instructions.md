# ProjectInstructions - Geo News Scraper

## 1) Proje Amacı

Bu proje, belirli haber sitelerinden şehir/kent odaklı haberleri toplar, embedding tabanlı benzerlik analiziyle tekilleştirir, konumları geocode eder ve sonuçları harita üzerinde dinamik filtrelerle gösterir.

## 2) Zorunlu Gereksinimler

- Veritabanı MongoDB olmalıdır.
- Web scraping uygulanmalıdır.
- Embedding tabanlı benzerlik analizi yapılmalıdır.
- Benzerlik oranı 0.90 ve üzeri haberler tekilleştirilmelidir.
- Konumlar Google Geocoding API ile koordinata çevrilmelidir.
- Frontend tarafında sayfa yenilenmeden filtreleme yapılmalıdır (tarih, tür, ilçe).

## 3) Teknoloji Kararları

- Backend: Python + FastAPI
- Scraping: Scrapy
- NLP: sentence-transformers + cosine similarity
- Veritabanı: MongoDB
- Frontend: React + Vite + TypeScript
- Harita: Google Maps JavaScript API

## 4) Kodlama Standartları

- Python:
  - PEP8 uyumlu yaz.
  - Tip ipuçları ekle.
  - Fonksiyonları tek sorumluluk prensibiyle küçük tut.
- TypeScript/React:
  - strict mode kullan.
  - Bileşenleri sorumluluklarına göre ayır.
  - API çağrılarını merkezi client katmanında topla.
- Her kritik modülde kısa ama anlamlı açıklama notları kullan.

## 5) Mimari Kurallar

- Scraping, NLP, geocoding ve API katmanlarını ayrı servis modüllerinde tut.
- Business logic endpoint dosyalarında değil service katmanında olmalı.
- Mongo erişimi repository katmanı ile yönetilmeli.
- Geocoding sonuçları cache koleksiyonuna yazılmalı.
- URL bazlı duplicate kontrolü ve içerik bazlı dedup birlikte uygulanmalı.

## 6) Veri ve Model Kuralları

- news dokümanında minimum alanlar:
  - source, url, title, content, published_at, type, district, locations, coordinates, embedding, similarity_group_id
- URL unique olmalı.
- coordinates için 2dsphere index kullanılmalı.
- similarity_group_id tekilleşen haberleri gruplayacak şekilde tutulmalı.

## 7) NLP ve Tekilleştirme Kuralları

- Metin temizleme adımı zorunlu.
- Embedding hesaplamasında model sabitlenmeli.
- Benzerlik metodu cosine similarity olmalı.
- Eşik: similarity >= 0.90 => aynı haber kümesi.
- Eşik/karar adımları loglanmalı.

## 8) API Kuralları

- Tüm endpointler /api/v1 altında olmalı.
- Filtre endpointleri:
  - date_from
  - date_to
  - type
  - district
- Liste endpointleri sayfalama desteklemeli.
- Hatalar standart JSON formatında dönmeli.

## 9) Frontend Kuralları

- Filtre değiştiğinde tam sayfa yenilenmesi yapılmamalı.
- Harita ve liste aynı veri kaynağından beslenmeli.
- Query param ile filtre state senkron tutulmalı.
- Büyük marker setlerinde cluster kullanılmalı.
- Loading, error, empty state ekranları zorunlu.

## 10) Güvenlik ve Konfigürasyon

- API anahtarlarını kod içine gömme.
- Sadece .env üzerinden yönet.
- .env.example güncel tutulmalı.
- Üretim ve geliştirme ayarları ayrılmalı.

## 11) Test ve Kalite

- Parser, dedup, geocode cache için birim test yaz.
- API ve Mongo entegrasyon testleri ekle.
- Frontend filtre akışı test edilmeli.
- Lint ve format kontrolleri CI benzeri şekilde çalıştırılmalı.

## 12) Copilot Çalışma Biçimi

- Yeni kod yazmadan önce mevcut yapıyı tarayıp uyumlu kal.
- Dosya yapısını bozmadan mevcut modüle ekleme yap.
- Gereksiz bağımlılık ekleme.
- Büyük değişikliklerde önce kısa plan çıkar, sonra uygula.
- Her önemli değişiklikte hangi gereksinimi karşıladığını belirt.

## 13) Git Workflow ve Otomasyon

- Her önemli TODO maddesi tamamlandığında veya mantıksal bir iş paketi bittiğinde, doğrudan bir sonraki işe geçme. Önce dur ve kullanıcıya commit onayı sor.
- Commit mesajları daima bir başlık ve altında neler yapıldığını madde madde anlatan detaylı bir body içermelidir. **Commit mesajının TAMAMI (başlık ve tüm body maddeleri) KESİNLİKLE İNGİLİZCE olmalıdır. Türkçe veya başka bir dil kesinlikle kabul edilemez.** Format:

  ```
  type(scope): Short title in English (max 72 chars)

  - Change description 1 (in English)
  - Change description 2 (in English)
  - Change description 3 (in English)
  ```

  Kullanıcı onay verirse terminalde `git add .`, `git commit -m "title" -m "body"` ve `git push` komutlarını çalıştır.

- ÖNEMLİ: Yeni bir dosya, klasör, log veya veri tipi (cache, raw data vb.) oluşturduğunda, commit aşamasına geçmeden önce daima `.gitignore` dosyasını kontrol et ve bu gereksiz/büyük dosyaların Git tarafından takip edilmediğinden emin olacak şekilde `.gitignore` dosyasını güncelle.
