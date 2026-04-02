import { useEffect, useState, useCallback } from 'react';
import MapContainer from '../components/map/MapContainer';
import { newsService } from '../api/newsService';
import { MapMarker } from '../types/news';

/* ─── Types & constants ───────────────────────────────────── */
type EventType = 'Trafik Kazası' | 'Yangın' | 'Elektrik Kesintisi' | 'Hırsızlık' | 'Kültürel Etkinlikler';

const EVENT_FILTERS = [
  { label: 'Trafik Kazası' as EventType, emoji: '🚗', color: '#f59e0b' },
  { label: 'Yangın' as EventType, emoji: '🔥', color: '#ef4444' },
  { label: 'Elektrik Kesintisi' as EventType, emoji: '⚡', color: '#b6c4ff' },
  { label: 'Hırsızlık' as EventType, emoji: '⛓️‍💥', color: '#a855f7' },
  { label: 'Kültürel Etkinlikler' as EventType, emoji: '🎭', color: '#a43d77' },
  { label: 'Diğer' as EventType, emoji: '〰️', color: '#22c55e' },
];

const DISTRICTS = ['Tüm İlçeler', 'İzmit', 'Gebze', 'Derince', 'Körfez', 'Kartepe', 'Gölcük', 'Çayırova', 'Dilovası'];
const TIME_RANGES = ['Son 24 Saat', 'Son 3 Gün', 'Son 1 Hafta'];

const accentOf = (type: string): string =>
  ({ 'Yangın': '#ef4444', 'Trafik Kazası': '#f59e0b', 'Elektrik Kesintisi': '#b6c4ff', 'Hırsızlık': '#a855f7', 'Kültürel Etkinlikler': '#a43d77' }[type] ?? '#4b486f');

const emojiOf = (type: string): string =>
  ({ 'Yangın': '🔥', 'Trafik Kazası': '🚗', 'Elektrik Kesintisi': '⚡', 'Hırsızlık': '⛓️‍💥', 'Kültürel Etkinlikler': '🎭' }[type] ?? '〰️');

const timeAgo = (d?: string) => {
  if (!d) return '';
  const m = Math.floor((Date.now() - parseUTC(d)) / 60000);
  if (m < 60) return `${m} dk önce`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h} saat önce`;
  return `${Math.floor(h / 24)} gün önce`;
};

/** API tarihleri timezone bilgisi olmadan geliyor ("2026-04-02T18:37:00").
 *  Sonuna 'Z' ekleyerek UTC olarak parse ediyoruz. */
const parseUTC = (s: string): number => {
  if (!s) return 0;
  // Zaten timezone bilgisi varsa (Z veya +XX:XX) olduğu gibi parse et
  if (s.endsWith('Z') || s.includes('+')) return new Date(s).getTime();
  // Yoksa UTC olarak işaretle
  return new Date(s + 'Z').getTime();
};

/* ─── Shared inline style tokens ─────────────────────────── */
const S = {
  input: {
    width: '100%', background: '#262a31', color: '#dfe2eb',
    border: '1px solid rgba(255,255,255,0.06)', borderRadius: 12,
    padding: '10px 36px 10px 14px', fontSize: 13,
    fontFamily: 'Inter, system-ui, sans-serif',
    appearance: 'none' as const, outline: 'none', cursor: 'pointer',
  } as React.CSSProperties,
  label: {
    display: 'block', fontSize: 9, fontWeight: 700,
    color: '#454652', letterSpacing: '0.2em',
    textTransform: 'uppercase' as const, marginBottom: 8,
  } as React.CSSProperties,
};

/* ─── Component ───────────────────────────────────────────── */
export default function MapPage() {
  const [allMarkers, setAllMarkers] = useState<MapMarker[]>([]);
  const [markers, setMarkers] = useState<MapMarker[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTypes, setActiveTypes] = useState<Set<EventType>>(
    new Set(EVENT_FILTERS.map(e => e.label)) // Bu satır artık 'Diğer'i de içerecek
  );
  const [district, setDistrict] = useState('Tüm İlçeler');
  const [timeRange, setTimeRange] = useState('Son 3 Gün');
  const [isCustomDate, setIsCustomDate] = useState(false);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [search, setSearch] = useState('');
  const [scraping, setScraping] = useState(false);
  const [scrapeMsg, setScrapeMsg] = useState<string | null>(null);

  /* fetch */
  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await newsService.getMarkers();
      if (res?.markers) { setAllMarkers(res.markers); setMarkers(res.markers); }
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  /* scrape trigger + poll */
  const handleScrape = useCallback(async () => {
    if (scraping) return;
    setScraping(true);
    setScrapeMsg(null);
    try {
      await newsService.triggerScrape();
      // Poll every 2s until idle
      const poll = setInterval(async () => {
        const s = await newsService.getScrapeStatus();
        if (s.status === 'idle') {
          clearInterval(poll);
          setScraping(false);
          setScrapeMsg(s.last_error ? `Hata: ${s.last_error}` : 'Veri çekildi ✅');
          await loadData(); // refresh markers
          setTimeout(() => setScrapeMsg(null), 5000);
        }
      }, 2000);
    } catch (e: any) {
      setScraping(false);
      const isConflict = e.response?.status === 409 || e.status === 409 || e.message?.includes('409');
      setScrapeMsg(isConflict ? 'Zaten çalışıyor…' : `Hata: ${e.message}`);
      setTimeout(() => setScrapeMsg(null), 5000);
    }
  }, [scraping, loadData]);

  /* filter */
  useEffect(() => {
    // 1. Kategori (Type) Filtrelemesi – type null/undefined ise "Diğer" say
    let r = allMarkers.filter(m => {
      const t = (m.type ?? 'Diğer') as EventType;
      return activeTypes.has(t);
    });

    // 2. İlçe Filtrelemesi
    if (district !== 'Tüm İlçeler') {
      r = r.filter(m => m.district === district);
    }

    // 3. Arama Filtrelemesi
    if (search.trim()) {
      const q = search.toLowerCase();
      r = r.filter(m => m.title?.toLowerCase().includes(q) || m.district?.toLowerCase().includes(q));
    }

    // 4. Tarih Filtreleme Mantığı (Yeni Eklenen Kısım)
    const now = Date.now();

    if (isCustomDate) {
      // Özel Tarih Aralığı Seçiliyse
      if (startDate) {
        const start = new Date(startDate).setHours(0, 0, 0, 0);
        r = r.filter(m => m.published_at && new Date(m.published_at).getTime() >= start);
      }
      if (endDate) {
        const end = new Date(endDate).setHours(23, 59, 59, 999);
        r = r.filter(m => m.published_at && new Date(m.published_at).getTime() <= end);
      }
    } else {
      // Hazır Zaman Aralıkları Seçiliyse
      let msLimit = 0;
      if (timeRange === 'Son 24 Saat') msLimit = 24 * 60 * 60 * 1000;
      else if (timeRange === 'Son 3 Gün') msLimit = 3 * 24 * 60 * 60 * 1000;
      else if (timeRange === 'Son 1 Hafta') msLimit = 7 * 24 * 60 * 60 * 1000;

      if (msLimit > 0) {
        // published_at yoksa tarihi bilinmiyor → zaman filtresinden geçirme
        // parseUTC ile timezone-naive stringleri doğru UTC olarak yorumluyoruz
        r = r.filter(m => m.published_at && (now - parseUTC(m.published_at)) <= msLimit);
      }
    }

    setMarkers(r);

    // Bağımlılıklar listesine tarih state'lerini de ekledik
  }, [allMarkers, activeTypes, district, search, timeRange, startDate, endDate, isCustomDate]);

  const toggleType = (t: EventType) =>
    setActiveTypes(prev => { const n = new Set(prev); n.has(t) ? n.delete(t) : n.add(t); return n; });

  const handleTimeChange = (val: string) => {
    setTimeRange(val);
    setIsCustomDate(val === 'Özel Tarih Seç...');
  };

  /* ── render ── */
  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      height: '100vh', background: '#10141a',
      color: '#dfe2eb', overflow: 'hidden', position: 'relative',
      fontFamily: 'Inter, system-ui, sans-serif',
    }}>

      {/* ── Loading overlay ── */}
      {loading && (
        <div style={{
          position: 'absolute', inset: 0, zIndex: 200,
          background: 'rgba(16,20,26,0.85)',
          backdropFilter: 'blur(10px)',
          display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center', gap: 16,
        }}>
          <div style={{
            width: 50, height: 50,
            border: '4px solid rgba(182,196,255,0.12)',
            borderTopColor: '#b6c4ff',
            borderRadius: '50%',
            animation: '_sentinel_spin 0.85s linear infinite',
          }} />
          <span style={{ color: '#b6c4ff', fontSize: 10, fontWeight: 700, letterSpacing: '0.3em' }}>
            RADAR TARANIYOR…
          </span>
        </div>
      )}

      {/* ── Header ── */}
      <header style={{
        position: 'fixed', top: 0, width: '100%', height: 64, zIndex: 100,
        background: 'rgba(16,20,26,0.82)',
        backdropFilter: 'blur(24px)',
        borderBottom: '1px solid rgba(255,255,255,0.05)',
        boxShadow: '0 4px 40px rgba(0,0,0,0.5)',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0 24px',
      }}>
        {/* Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{
            width: 40, height: 40, borderRadius: '50%',
            background: '#00267e',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 20, position: 'relative',
            boxShadow: '0 0 0 2px rgba(182,196,255,0.2), 0 0 20px rgba(182,196,255,0.15)',
          }}>📡</div>
          <span style={{
            fontFamily: 'Manrope, Inter, sans-serif',
            fontWeight: 800, fontSize: 18,
            letterSpacing: '-0.02em', textTransform: 'uppercase' as const,
            color: '#b6c4ff',
          }}>Haber Radar</span>
        </div>

        {/* Search */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 10,
          background: '#1c2026', borderRadius: 99,
          padding: '9px 20px', border: '1px solid rgba(255,255,255,0.06)',
          width: '32%', minWidth: 220,
        }}>
          <span style={{ fontSize: 16, color: '#454652' }}>🔍</span>
          <input
            placeholder="Kocaeli'de ara…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            // onKeyDown satırını tamamen silebilirsin, useEffect sen yazdıkça filtreleyecek
            style={{
              background: 'transparent', border: 'none', outline: 'none',
              fontSize: 13, color: '#dfe2eb', width: '100%',
              fontFamily: 'Inter, system-ui, sans-serif',
            }}
          />
        </div>

        {/* Right side */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <button
            onClick={loadData}
            style={{
              width: 38, height: 38, borderRadius: '50%',
              background: 'transparent', border: '1px solid rgba(255,255,255,0.08)',
              cursor: 'pointer', color: '#b6c4ff', fontSize: 18,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}
            title="Yenile"
          >↻</button>

          {/* Scrape button */}
          <button
            onClick={handleScrape}
            disabled={scraping}
            title={scraping ? 'Kazıma devam ediyor…' : 'Güncel veri çek'}
            style={{
              display: 'flex', alignItems: 'center', gap: 6,
              padding: '8px 16px', borderRadius: 99,
              background: scraping ? '#1c2026' : scrapeMsg?.startsWith('Hata') ? '#3b0000' : '#00267e',
              border: `1px solid ${scraping ? 'rgba(255,255,255,0.06)' : scrapeMsg?.startsWith('Hata') ? '#ef4444' : '#b6c4ff'}`,
              color: scraping ? '#454652' : scrapeMsg?.startsWith('Hata') ? '#ef4444' : '#b6c4ff',
              fontSize: 12, fontWeight: 700, cursor: scraping ? 'not-allowed' : 'pointer',
              letterSpacing: '0.05em', transition: 'all 0.2s',
            }}
          >
            {scraping
              ? <span style={{ display: 'inline-block', animation: '_sentinel_spin 0.9s linear infinite' }}>⟳</span>
              : '🕷️'}
            {scraping ? 'Çekiliyor…' : scrapeMsg ?? 'Veri Çek'}
          </button>

          {/* Live badge */}
          <div style={{
            display: 'flex', alignItems: 'center', gap: 8,
            background: '#1c2026', border: '1px solid rgba(255,255,255,0.06)',
            padding: '7px 14px', borderRadius: 99,
          }}>
            <span style={{
              width: 7, height: 7, borderRadius: '50%',
              background: '#22c55e', display: 'inline-block',
              boxShadow: '0 0 8px #22c55e',
            }} />
            <span style={{ fontSize: 10, fontWeight: 700, color: '#fff', letterSpacing: '0.15em' }}>CANLI</span>
            <div style={{ width: 1, height: 12, background: 'rgba(255,255,255,0.08)' }} />
            <span style={{ fontSize: 10, fontWeight: 700, color: '#908f9d' }}>{markers.length} haber</span>
          </div>

          {/* Avatar */}
          <div style={{
            width: 36, height: 36, borderRadius: '50%',
            background: '#00267e', border: '1px solid rgba(255,255,255,0.1)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 16,
          }}>👤</div>
        </div>
      </header>

      {/* ── Body ── */}
      <main style={{ display: 'flex', flex: 1, paddingTop: 64, overflow: 'hidden' }}>

        {/* ── Sidebar ── */}
        <aside style={{
          width: 296, flexShrink: 0,
          background: '#181c22',
          borderRight: '1px solid rgba(255,255,255,0.05)',
          overflowY: 'auto',
          overflowX: 'hidden',
          zIndex: 40,
          boxShadow: '4px 0 30px rgba(0,0,0,0.4)',
        }}>
          <div style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 28 }}>

            {/* Brand */}
            <div>
              <div style={{ fontFamily: 'Manrope, Inter, sans-serif', fontWeight: 800, fontSize: 20, color: '#dfe2eb' }}>
                Kocaeli News
              </div>
              <div style={{ fontSize: 9, fontWeight: 700, color: '#454652', letterSpacing: '0.22em', textTransform: 'uppercase', marginTop: 4 }}>
                The Sentinel Perspective
              </div>
            </div>

            {/* Filters */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>

              {/* District */}
              <div>
                <label style={S.label}>İlçe</label>
                <div style={{ position: 'relative' }}>
                  <select value={district} onChange={e => setDistrict(e.target.value)} style={S.input}>
                    {DISTRICTS.map(d => <option key={d}>{d}</option>)}
                  </select>
                  <span style={{ position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)', pointerEvents: 'none', color: '#454652', fontSize: 16 }}>▾</span>
                </div>
              </div>

              {/* Time range */}
              <div>
                <label style={S.label}>Zaman Aralığı</label>
                <div style={{ position: 'relative' }}>
                  <select
                    value={timeRange}
                    onChange={e => handleTimeChange(e.target.value)} // Burayı güncelledik
                    style={S.input}
                  >
                    {TIME_RANGES.map(r => <option key={r}>{r}</option>)}
                    <option>Özel Tarih Seç...</option> {/* Bu seçeneği ekledik */}
                  </select>
                  <span style={{ position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)', pointerEvents: 'none', color: '#454652', fontSize: 16 }}>▾</span>
                </div>

                {/* --- Yeni Eklenen Input Bloğu --- */}
                {isCustomDate && (
                  <div style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 8 }}>
                    <div style={{ display: 'flex', gap: 8 }}>
                      <input
                        type="date"
                        style={{ ...S.input, padding: '8px' }}
                        onChange={(e) => setStartDate(e.target.value)}
                      />
                      <input
                        type="date"
                        style={{ ...S.input, padding: '8px' }}
                        onChange={(e) => setEndDate(e.target.value)}
                      />
                    </div>
                  </div>
                )}
              </div>

              {/* Event types */}
              <div>
                <label style={S.label}>Olay Türü</label>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {EVENT_FILTERS.map(({ label, emoji, color }) => {
                    const on = activeTypes.has(label);
                    return (
                      <label key={label} style={{
                        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                        padding: '10px 12px', borderRadius: 12, cursor: 'pointer',
                        background: on ? `${color}14` : 'rgba(255,255,255,0.03)',
                        border: `1px solid ${on ? color + '30' : 'rgba(255,255,255,0.04)'}`,
                        transition: 'all 0.15s',
                      }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                          <span style={{ fontSize: 18 }}>{emoji}</span>
                          <span style={{ fontSize: 12, fontWeight: 500, color: on ? '#dfe2eb' : '#908f9d' }}>{label}</span>
                        </div>
                        <input
                          type="checkbox"
                          checked={on}
                          onChange={() => toggleType(label)}
                          style={{ accentColor: color, width: 15, height: 15, cursor: 'pointer' }}
                        />
                      </label>
                    );
                  })}
                </div>
              </div>

              {/* Action buttons */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                <button
                  // onClick kısmını siliyoruz, artık otomatik çalışıyor
                  style={{
                    background: '#262a31', color: '#dfe2eb',
                    border: '1px solid rgba(255,255,255,0.07)',
                    borderRadius: 12, padding: '12px 0',
                    fontSize: 12, fontWeight: 700, cursor: 'pointer',
                    fontFamily: 'Inter, system-ui, sans-serif',
                    transition: 'background 0.15s',
                  }}
                >
                  Filtrele
                </button>
                <button
                  onClick={loadData}
                  style={{
                    background: '#b6c4ff', color: '#002780',
                    border: 'none', borderRadius: 12, padding: '12px 0',
                    fontSize: 12, fontWeight: 800, cursor: 'pointer',
                    fontFamily: 'Inter, system-ui, sans-serif',
                    boxShadow: '0 0 20px rgba(182,196,255,0.25)',
                    transition: 'all 0.15s',
                    display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
                  }}
                  onMouseOver={e => (e.currentTarget.style.boxShadow = '0 0 30px rgba(182,196,255,0.45)')}
                  onMouseOut={e => (e.currentTarget.style.boxShadow = '0 0 20px rgba(182,196,255,0.25)')}
                >
                  Veri Çek ↻
                </button>
              </div>
            </div>

            {/* Divider */}
            <div style={{ height: 1, background: 'rgba(255,255,255,0.05)' }} />

            {/* News feed */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10, paddingBottom: 16 }}>
              <div style={{ fontSize: 9, fontWeight: 700, color: '#454652', letterSpacing: '0.2em', textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: 8, position: 'sticky', top: 0, background: '#181c22', paddingBottom: 6 }}>
                <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#ef4444', display: 'inline-block', boxShadow: '0 0 8px #ef4444' }} />
                Son Haberler
              </div>

              {markers.length === 0 && !loading && (
                <div style={{ color: '#454652', fontSize: 12, textAlign: 'center', padding: '32px 0' }}>
                  Haber bulunamadı.
                </div>
              )}

              {markers.map(news => {
                const accent = accentOf(news.type);
                const emoji = emojiOf(news.type);
                return (
                  <div key={news._id} style={{
                    background: 'rgba(255,255,255,0.03)',
                    border: '1px solid rgba(255,255,255,0.04)',
                    borderRadius: 12, padding: '12px 14px',
                    cursor: 'pointer', transition: 'background 0.15s',
                    display: 'flex', gap: 12, alignItems: 'flex-start',
                  }}
                    onMouseOver={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.07)')}
                    onMouseOut={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.03)')}
                  >
                    {/* Icon bubble */}
                    <div style={{
                      flexShrink: 0, width: 36, height: 36, borderRadius: 10,
                      background: `${accent}18`,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontSize: 17, marginTop: 1,
                    }}>{emoji}</div>

                    <div style={{ flex: 1, minWidth: 0 }}>
                      <p style={{
                        margin: 0, fontSize: 12, fontWeight: 600,
                        lineHeight: 1.45, color: '#dfe2eb',
                        overflow: 'hidden', display: '-webkit-box',
                        WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' as const,
                      }}>{news.title}</p>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 6, flexWrap: 'wrap' }}>
                        {news.district && (
                          <span style={{ fontSize: 9, fontWeight: 700, color: '#908f9d', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                            {news.district}
                          </span>
                        )}
                        {news.district && <span style={{ fontSize: 9, color: '#31353c' }}>•</span>}
                        <span style={{ fontSize: 9, fontWeight: 800, color: accent, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                          {news.type}
                        </span>
                        {news.published_at && (
                          <>
                            <span style={{ fontSize: 9, color: '#31353c' }}>•</span>
                            <span style={{ fontSize: 9, color: '#454652' }}>{timeAgo(news.published_at)}</span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </aside>

        {/* ── Map area ── */}
        <section style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
          {/* Zoom controls */}
          <div style={{ position: 'absolute', bottom: 32, right: 32, zIndex: 30, display: 'flex', flexDirection: 'column', gap: 10 }}>
            {['+', '−'].map(icon => (
              <button key={icon} style={{
                width: 44, height: 44, borderRadius: '50%',
                background: 'rgba(28,32,38,0.82)', backdropFilter: 'blur(10px)',
                border: '1px solid rgba(255,255,255,0.08)',
                color: '#dfe2eb', fontSize: 20, fontWeight: 300,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                cursor: 'pointer', boxShadow: '0 4px 20px rgba(0,0,0,0.4)',
                transition: 'background 0.15s',
              }}
                onMouseOver={e => (e.currentTarget.style.background = 'rgba(38,42,49,0.95)')}
                onMouseOut={e => (e.currentTarget.style.background = 'rgba(28,32,38,0.82)')}
              >{icon}</button>
            ))}
            <button style={{
              width: 44, height: 44, borderRadius: '50%', marginTop: 8,
              background: 'rgba(28,32,38,0.82)', backdropFilter: 'blur(10px)',
              border: '1px solid rgba(182,196,255,0.25)',
              color: '#b6c4ff', fontSize: 18,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              cursor: 'pointer', boxShadow: '0 4px 20px rgba(0,0,0,0.4)',
            }}>◎</button>
          </div>

          <MapContainer markers={markers} />
        </section>
      </main>
    </div>
  );
}