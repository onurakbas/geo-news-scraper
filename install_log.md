# Install Log

Bu dosya; bilgisayara ve projeye kurulan tüm araç, paket ve servislerin kaydını tutar.

## Kullanım Kuralları

- Her kurulumdan hemen sonra yeni kayıt ekle.
- Sürümü kesin yaz.
- Doğrulama komutunu ve çıktının özetini yaz.
- Hata aldıysan çözüm notunu ekle.

## Kayıt Şablonu

### [Tarih] - [Bileşen Adı]

- Tür: system | backend | frontend | dev-tool
- Sürüm:
- Kurulum komutu:
- Doğrulama komutu:
- Doğrulama sonucu:
- Not:

## Kayıtlar

### 2026-03-17 - Homebrew Update

- Tür: system
- Sürüm: N/A
- Kurulum komutu: brew update
- Doğrulama komutu: brew --version
- Doğrulama sonucu: başarılı
- Not: başlangıç güncellemesi

### 2026-03-17 - MongoDB Community

- Tür: system
- Sürüm: 8.0
- Kurulum komutu: brew install mongodb-community@8.0
- Doğrulama komutu: mongosh --eval "db.runCommand({ ping: 1 })"
- Doğrulama sonucu: { ok: 1 }
- Not: servis brew services ile başlatıldı

### 2026-03-17 - Xcode Command Line Tools Kontrol

- Tür: system
- Sürüm: mevcut (zaten kurulu)
- Kurulum komutu: xcode-select --install
- Doğrulama komutu: xcode-select --install
- Doğrulama sonucu: "Command line tools are already installed"
- Not: Yeni kurulum gerekmedi.

### 2026-03-17 - MongoDB Tap

- Tür: system
- Sürüm: mongodb/brew tap (13 formula)
- Kurulum komutu: brew tap mongodb/brew
- Doğrulama komutu: brew tap | grep mongodb/brew
- Doğrulama sonucu: tap eklendi
- Not: MongoDB formula kaynağı hazırlandı.

### 2026-03-17 - MongoDB Service Start

- Tür: system
- Sürüm: mongodb-community@8.0.20
- Kurulum komutu: brew services start mongodb-community@8.0
- Doğrulama komutu: mongosh --eval "db.runCommand({ ping: 1 })"
- Doğrulama sonucu: { ok: 1 }
- Not: Servis başarılı şekilde ayağa kalktı.

### 2026-03-17 - Mongosh

- Tür: system
- Sürüm: 2.7.0
- Kurulum komutu: brew install mongosh
- Doğrulama komutu: mongosh --version
- Doğrulama sonucu: 2.7.0
- Not: Zaten güncel kurulu olduğu doğrulandı.

### 2026-03-17 - Node.js (Homebrew)

- Tür: system
- Sürüm: node 25.8.1_1
- Kurulum komutu: brew install node
- Doğrulama komutu: node -v
- Doğrulama sonucu: v25.8.1
- Not: PATH içinde node@22 çakışması vardı; `brew uninstall node@22` ile giderildi.

### 2026-03-17 - npm (Node ile)

- Tür: system
- Sürüm: 11.11.0
- Kurulum komutu: brew install node
- Doğrulama komutu: npm -v
- Doğrulama sonucu: 11.11.0
- Not: Doğrulama PATH=/opt/homebrew/bin:/usr/bin:/bin ile yapıldı.

### 2026-03-17 - Python 3.13 ve venv

- Tür: system
- Sürüm: Python 3.13.9
- Kurulum komutu: /opt/homebrew/bin/python3.13 -m venv .venv
- Doğrulama komutu: /opt/homebrew/bin/python3.13 --version
- Doğrulama sonucu: Python 3.13.9
- Not: Sanal ortam ana dizinde oluşturuldu.

### 2026-03-17 - pip/setuptools/wheel upgrade

- Tür: backend
- Sürüm: pip 26.0.1, setuptools 82.0.1, wheel 0.46.3
- Kurulum komutu: .venv/bin/python -m pip install --upgrade pip setuptools wheel
- Doğrulama komutu: .venv/bin/pip --version
- Doğrulama sonucu: pip 26.0.1
- Not: venv içinde başarıyla güncellendi.

### 2026-03-17 - Backend API ve DB Paketleri

- Tür: backend
- Sürüm: fastapi 0.135.1, uvicorn 0.42.0, pymongo 4.16.0, motor 3.7.1, pydantic 2.12.5, pydantic-settings 2.13.1, python-dotenv 1.2.2
- Kurulum komutu: .venv/bin/pip install fastapi uvicorn pymongo motor pydantic pydantic-settings python-dotenv
- Doğrulama komutu: .venv/bin/pip show fastapi pymongo motor
- Doğrulama sonucu: paketler yüklü
- Not: API ve Mongo erişim katmanı hazır.

### 2026-03-17 - Scraping Paketleri

- Tür: backend
- Sürüm: scrapy 2.14.2, beautifulsoup4 4.14.3, lxml 6.0.2, newspaper3k 0.2.8, requests 2.32.5, httpx 0.28.1
- Kurulum komutu: .venv/bin/pip install scrapy beautifulsoup4 lxml newspaper3k requests httpx
- Doğrulama komutu: .venv/bin/pip show scrapy newspaper3k
- Doğrulama sonucu: paketler yüklü
- Not: Scraping ve HTTP katmanı kuruldu.

### 2026-03-17 - NLP/Embedding Paketleri

- Tür: backend
- Sürüm: sentence-transformers 5.3.0, scikit-learn 1.8.0, numpy 2.4.3, scipy 1.17.1, pandas 3.0.1, rapidfuzz 3.14.3, torch 2.10.0
- Kurulum komutu: .venv/bin/pip install sentence-transformers scikit-learn numpy scipy pandas rapidfuzz
- Doğrulama komutu: .venv/bin/pip show sentence-transformers scikit-learn
- Doğrulama sonucu: paketler yüklü
- Not: Büyük boyutlu NLP bağımlılıkları sorunsuz tamamlandı.

### 2026-03-17 - Geocoding Yardımcı Paketleri

- Tür: backend
- Sürüm: googlemaps 4.10.0, tenacity 9.1.4
- Kurulum komutu: .venv/bin/pip install googlemaps tenacity
- Doğrulama komutu: .venv/bin/pip show googlemaps tenacity
- Doğrulama sonucu: paketler yüklü
- Not: Google Geocoding istemcisi için hazır.

### 2026-03-17 - Yardımcı Kalite Paketleri

- Tür: backend
- Sürüm: loguru 0.7.3, python-dateutil 2.9.0.post0
- Kurulum komutu: .venv/bin/pip install loguru python-dateutil
- Doğrulama komutu: .venv/bin/pip show loguru python-dateutil
- Doğrulama sonucu: paketler yüklü
- Not: Loglama ve tarih yardımcıları hazır.

### 2026-03-17 - Test/Lint/Format Paketleri

- Tür: dev-tool
- Sürüm: pytest 9.0.2, pytest-asyncio 1.3.0, pytest-cov 7.0.0, black 26.3.1, ruff 0.15.6, mypy 1.19.1, pre-commit 4.5.1
- Kurulum komutu: .venv/bin/pip install pytest pytest-asyncio pytest-cov black ruff mypy pre-commit
- Doğrulama komutu: .venv/bin/pip show pytest black ruff mypy pre-commit
- Doğrulama sonucu: paketler yüklü
- Not: Kod kalitesi araçları tamamlandı.

### 2026-03-17 - Frontend NPM Başlatma

- Tür: frontend
- Sürüm: frontend package.json 1.0.0
- Kurulum komutu: cd frontend && npm init -y && npm install
- Doğrulama komutu: npm install
- Doğrulama sonucu: up to date, 0 vulnerability
- Not: Planlanan klasör ağacını bozmamak için mevcut `frontend` içinde başlatıldı.

### 2026-03-17 - Frontend Uygulama Paketleri

- Tür: frontend
- Sürüm: axios, @tanstack/react-query, @react-google-maps/api, zod, dayjs, react-router-dom
- Kurulum komutu: npm install axios @tanstack/react-query @react-google-maps/api zod dayjs react-router-dom
- Doğrulama komutu: npm ls --depth=0
- Doğrulama sonucu: paketler yüklü
- Not: API, state ve harita bağımlılıkları kuruldu.

### 2026-03-17 - Frontend Test/Kalite Paketleri

- Tür: frontend
- Sürüm: vitest, @testing-library/react, @testing-library/jest-dom, eslint, prettier, eslint-config-prettier
- Kurulum komutu: npm install -D vitest @testing-library/react @testing-library/jest-dom eslint prettier eslint-config-prettier
- Doğrulama komutu: npm ls --depth=0
- Doğrulama sonucu: paketler yüklü
- Not: Frontend kalite araçları eklendi.

### 2026-03-17 - Frontend Core (React + Vite + TypeScript)

- Tür: frontend
- Sürüm: react, react-dom, typescript, vite, @types/react, @types/react-dom, @vitejs/plugin-react
- Kurulum komutu: npm install react react-dom && npm install -D typescript vite @types/react @types/react-dom @vitejs/plugin-react
- Doğrulama komutu: npm ls --depth=0
- Doğrulama sonucu: paketler yüklü
- Not: React+Vite+TS çekirdeği tamamlandı.
