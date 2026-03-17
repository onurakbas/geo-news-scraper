# Windows Setup Guide - Geo News Scraper

Bu dokuman, Windows kullanan ekip arkadaslari icin MongoDB, Node.js ve Python kurulumunu adim adim anlatir.

## 1) On Kosullar

1. Windows 10/11 guncel olsun.
2. PowerShell'i Yonetici olarak acabildiginden emin ol.
3. Kurulumlar bittikten sonra terminali kapatip yeniden ac.

## 2) MongoDB Kurulumu (Resmi Kaynaklar)

1. MongoDB Community Server indir:
   https://www.mongodb.com/try/download/community
2. Platform olarak Windows, package olarak MSI sec.
3. MSI kurulumunda asagidakileri sec:
   - Complete kurulum
   - Install MongoDB as a Service (onerilir)
   - Install MongoDB Compass (opsiyonel ama faydali)
4. Kurulumdan sonra yeni PowerShell ac ve kontrol et:
   - Komut: mongod --version
   - Komut: mongosh --version
5. Servis durumunu kontrol et:
   - Komut: Get-Service | findstr MongoDB
6. Gerekirse servisi baslat:
   - Komut: net start MongoDB
7. Ping testi yap:
   - Komut: mongosh --eval "db.runCommand({ ping: 1 })"

Ek resmi dokuman:
https://www.mongodb.com/docs/manual/tutorial/install-mongodb-on-windows/

## 3) Node.js Kurulumu (Resmi Kaynak)

1. Node.js LTS indir:
   https://nodejs.org/en/download
2. Windows Installer (.msi) ile kurulumu tamamla.
3. Yeni PowerShell ac ve surumleri kontrol et:
   - Komut: node -v
   - Komut: npm -v

## 4) Python Kurulumu (Resmi Kaynak)

1. Python indir:
   https://www.python.org/downloads/windows/
2. Kurulum ekraninda mutlaka su secenegi isaretle:
   - Add python.exe to PATH
3. Kurulumdan sonra yeni PowerShell ac ve kontrol et:
   - Komut: python --version
   - Komut: py --version

## 5) Proje Dizinine Gecis

1. PowerShell'de proje klasorune git:
   - Komut: cd C:\\path\\to\\geo-news-scraper

## 6) Python Sanal Ortam (venv) Olusturma ve Aktivasyon

1. Sanal ortam olustur:
   - Komut: python -m venv .venv
2. PowerShell aktivasyon:
   - Komut: .\\.venv\\Scripts\\Activate.ps1
3. Komut Istemi (cmd) aktivasyon:
   - Komut: .venv\\Scripts\\activate.bat
4. Git Bash aktivasyon:
   - Komut: source .venv/Scripts/activate

Not: PowerShell script execution policy hatasi alirsan (gecici cozum):

- Komut: Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
- Sonra tekrar: .\\.venv\\Scripts\\Activate.ps1

## 7) Python Paketlerini Kurma

Sanal ortam aktifken:

1. Pip araclarini guncelle:
   - Komut: python -m pip install --upgrade pip setuptools wheel
2. Backend temel paketleri:
   - Komut: pip install fastapi uvicorn pymongo motor pydantic pydantic-settings python-dotenv
3. Scraping paketleri:
   - Komut: pip install scrapy beautifulsoup4 lxml newspaper3k requests httpx
4. NLP paketleri:
   - Komut: pip install sentence-transformers scikit-learn numpy scipy pandas rapidfuzz
5. Geocoding ve yardimci paketler:
   - Komut: pip install googlemaps tenacity loguru python-dateutil
6. Test ve kalite paketleri:
   - Komut: pip install pytest pytest-asyncio pytest-cov black ruff mypy pre-commit

## 8) Frontend Kurulumu

1. Frontend iskeletini olustur:
   - Komut: npm create vite@latest frontend -- --template react-ts
2. Frontend bagimliliklarini kur:
   - Komut: cd frontend
   - Komut: npm install
3. API ve harita paketleri:
   - Komut: npm install axios @tanstack/react-query @react-google-maps/api zod dayjs react-router-dom
4. Test ve kalite paketleri:
   - Komut: npm install -D vitest @testing-library/react @testing-library/jest-dom eslint prettier eslint-config-prettier

## 9) Hizli Dogrulama

1. Backend dogrulama:
   - Komut: python -c "import fastapi, pymongo, scrapy; print('backend ok')"
2. Frontend dogrulama:
   - Komut: cd frontend
   - Komut: npm run dev
3. MongoDB dogrulama:
   - Komut: mongosh --eval "db.runCommand({ ping: 1 })"

## 10) Kurulum Kaydi

Her kurulum adimindan sonra ana dizindeki install_log.md dosyasina su bilgileri yaz:

- Tarih
- Kurulan paket/uygulama
- Surum
- Kurulum komutu
- Dogrulama komutu ve sonucu
- Notlar
