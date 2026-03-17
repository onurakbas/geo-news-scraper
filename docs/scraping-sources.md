# Scraping Sources – Kocaeli Yerel Haber Siteleri

Bu proje **yalnızca** aşağıdaki 5 Kocaeli yerel haber sitesinden veri toplar.
Yeni kaynak eklenmeden önce bu belge güncellenmeli ve ilgili spider yazılmalıdır.

---

## Kaynak Listesi

| #   | Site Adı       | URL                               | Spider Dosyası      |
| --- | -------------- | --------------------------------- | ------------------- |
| 1   | Çağdaş Kocaeli | https://www.cagdaskocaeli.com.tr/ | `cagdas_kocaeli.py` |
| 2   | Özgür Kocaeli  | https://www.ozgurkocaeli.com.tr/  | `ozgur_kocaeli.py`  |
| 3   | SES Kocaeli    | https://www.seskocaeli.com/       | `ses_kocaeli.py`    |
| 4   | Yeni Kocaeli   | https://www.yenikocaeli.com/      | `yeni_kocaeli.py`   |
| 5   | Bizim Yaka     | https://www.bizimyaka.com/        | `bizim_yaka.py`     |

---

## Genel Strateji

### Sayfa Gezinme

Her sitenin ana sayfa ve kategori/haber-listesi sayfaları taranır. Sayfalama
`?page=N` veya `?p=N` gibi query parametreleriyle ya da "Daha Fazla" / "Sonraki"
butonlarıyla ilerlenir. Spider, yeni URL bulamadığında durur.

### Duplicate Kontrolü

İki katmanlı duplicate önleme uygulanır:

1. **Scrapy DupeFilter** – aynı URL aynı çalıştırmada iki kez ziyaret edilmez.
2. **MongoDB URL unique index** – pipeline, `url` alanı zaten mevcut olan
   dokümanı insert etmez (`update_one` ile `upsert=False`).

### Çekilen Alanlar

Her haber öğesi için aşağıdaki alanlar hedeflenir:

| Alan           | Açıklama                                       |
| -------------- | ---------------------------------------------- |
| `source`       | Kaynak site adı (sabit string)                 |
| `url`          | Haberin tam URL'si (canonical)                 |
| `title`        | Haber başlığı (`<h1>` veya `<title>`)          |
| `content`      | Temizlenmiş haber metni                        |
| `published_at` | Yayın tarihi (ISO 8601 / UTC)                  |
| `type`         | Otomatik etiket (örn. `genel`, `yerel`, vb.)   |
| `raw_html`     | Ham HTML (debug; `data/raw/` dizinine yazılır) |

### Selector Stratejisi (Site Bazında)

#### 1. Çağdaş Kocaeli (`cagdaskocaeli.com.tr`)

- Liste sayfası: `a.news-item` veya `div.category-news a`
- Başlık: `h1.news-title` veya `h1`
- İçerik: `div.news-content p`
- Tarih: `span.news-date` veya `time[datetime]`

#### 2. Özgür Kocaeli (`ozgurkocaeli.com.tr`)

- Liste sayfası: `div.haber-listesi a`, `div.news-list a`
- Başlık: `h1.baslik` veya `h1`
- İçerik: `div.haber-icerik p`, `div.news-detail p`
- Tarih: `span.tarih`, `time`, `meta[property="article:published_time"]`

#### 3. SES Kocaeli (`seskocaeli.com`)

- Liste sayfası: `div.listing a`, `article a`
- Başlık: `h1`, `h1.title`
- İçerik: `div.content p`, `div.article-body p`
- Tarih: `time[datetime]`, `span.date`, `meta[property="article:published_time"]`

#### 4. Yeni Kocaeli (`yenikocaeli.com`)

- Liste sayfası: `div.news-list a`, `ul.haberler li a`
- Başlık: `h1.haber-baslik`, `h1`
- İçerik: `div.haber-detay p`, `div.icerik p`
- Tarih: `span.tarih`, `time`, `meta[property="article:published_time"]`

#### 5. Bizim Yaka (`bizimyaka.com`)

- Liste sayfası: `div.haber-kutu a`, `article.post a`
- Başlık: `h1.entry-title`, `h1`
- İçerik: `div.entry-content p`
- Tarih: `time.entry-date`, `meta[property="article:published_time"]`

### Fallback Zinciri

Her alan için birincil CSS selector denenir; bulunamazsa `meta` og/article tag'leri,
bulunamazsa `<title>` veya boş string döner. Tarih parse hatalarında
`published_at = None` set edilir ve ilgili haber loglanır.

### Teknik Ayarlar

- `DOWNLOAD_DELAY`: 1–2 saniye (siteye nazik yükleme)
- `RANDOMIZE_DOWNLOAD_DELAY`: True
- `CONCURRENT_REQUESTS_PER_DOMAIN`: 2
- `USER_AGENT`: rotasyon listesinden seçilir (bkz. `settings.py`)
- `ROBOTSTXT_OBEY`: True
- `RETRY_TIMES`: 3
- `HTTPERROR_ALLOWED_CODES`: [404] (404'ler hata sayılmaz, loglanır)

---

## Veri Akışı

```
Spider → Item → NewsItemPipeline → MongoDB (news koleksiyonu)
                                 → data/raw/<site>/<date>/<url_hash>.html
```

---

## Notlar

- Sitelerin yapısı değişirse ilgili spider'daki selector'lar güncellenmeli.
- Her başarılı spider çalıştırması `ingest_logs` koleksiyonuna kaydedilir.
- Herhangi bir siteye erişim sorunu yaşanırsa önce `robots.txt` kontrol edilmeli.
