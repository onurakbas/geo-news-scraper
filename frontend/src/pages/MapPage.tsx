import { useEffect, useState, useCallback } from 'react';
import {
  Search, RefreshCw, Car, Flame, Zap, ShieldAlert,
  Music2, LayoutGrid, MapPin, Clock, Filter,
  CalendarDays, ChevronDown, Newspaper,
} from 'lucide-react';
import MapContainer from '../components/map/MapContainer';
import { newsService } from '../api/newsService';
import { MapMarker } from '../types/news';

/* ─── Types & constants ───────────────────────────────────── */
type EventType =
  | 'Trafik Kazası'
  | 'Yangın'
  | 'Elektrik Kesintisi'
  | 'Hırsızlık'
  | 'Kültürel Etkinlikler'
  | 'Diğer';

const EVENT_FILTERS: { label: EventType; Icon: React.ElementType; color: string }[] = [
  { label: 'Trafik Kazası', Icon: Car, color: '#f59e0b' },
  { label: 'Yangın', Icon: Flame, color: '#ef4444' },
  { label: 'Elektrik Kesintisi', Icon: Zap, color: '#b6c4ff' },
  { label: 'Hırsızlık', Icon: ShieldAlert, color: '#a855f7' },
  { label: 'Kültürel Etkinlikler', Icon: Music2, color: '#a43d77' },
  { label: 'Diğer', Icon: LayoutGrid, color: '#22c55e' },
];

const iconOf = (type: string): React.ElementType => {
  const map: Record<string, React.ElementType> = {
    'Trafik Kazası': Car, 'Yangın': Flame, 'Elektrik Kesintisi': Zap,
    'Hırsızlık': ShieldAlert, 'Kültürel Etkinlikler': Music2,
  };
  return map[type] ?? LayoutGrid;
};

const accentOf = (type: string): string =>
  ({ 'Yangın': '#ef4444', 'Trafik Kazası': '#f59e0b', 'Elektrik Kesintisi': '#b6c4ff', 'Hırsızlık': '#a855f7', 'Kültürel Etkinlikler': '#a43d77' }[type] ?? '#22c55e');

const DISTRICTS = ['Tüm İlçeler', 'İzmit', 'Gebze', 'Derince', 'Körfez', 'Kartepe', 'Gölcük', 'Çayırova', 'Dilovası'];
const TIME_RANGES = ['Tüm Zamanlar', 'Son 24 Saat', 'Son 3 Gün'];

const parseUTC = (s: string): number => {
  if (!s) return 0;
  if (s.endsWith('Z') || s.includes('+')) return new Date(s).getTime();
  return new Date(s + 'Z').getTime();
};

const timeAgo = (d?: string) => {
  if (!d) return '';
  const m = Math.floor((Date.now() - parseUTC(d)) / 60000);
  if (m < 60) return `${m} dk önce`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h} saat önce`;
  return `${Math.floor(h / 24)} gün önce`;
};

const fmtDate = (s?: string) => {
  if (!s) return '—';
  const d = new Date(s.endsWith('Z') || s.includes('+') ? s : s + 'Z');
  return d.toLocaleDateString('tr-TR', { day: '2-digit', month: '2-digit', year: 'numeric' });
};

/* ─── Shared style tokens ─────────────────────────────────── */
const inputStyle: React.CSSProperties = {
  width: '100%', background: '#1e222a', color: '#dfe2eb',
  border: '1px solid rgba(255,255,255,0.07)', borderRadius: 10,
  padding: '9px 32px 9px 12px', fontSize: 13,
  fontFamily: 'Inter, system-ui, sans-serif',
  appearance: 'none', outline: 'none', cursor: 'pointer',
};
const labelStyle: React.CSSProperties = {
  display: 'block', fontSize: 9, fontWeight: 700,
  color: '#3d4150', letterSpacing: '0.18em',
  textTransform: 'uppercase', marginBottom: 7,
};

/* ─── Detail Sidebar ──────────────────────────────────────── */
function DetailPanel({ marker, onClose }: { marker: MapMarker; onClose: () => void }) {
  const accent = accentOf(marker.type);
  const Icon = iconOf(marker.type);

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        style={{
          position: 'fixed', inset: 0, zIndex: 199,
          background: 'rgba(0,0,0,0.35)', backdropFilter: 'blur(2px)',
        }}
      />
      {/* Panel */}
      <aside style={{
        position: 'fixed', top: 64, right: 0, bottom: 0,
        width: 320, zIndex: 200,
        background: 'linear-gradient(180deg, #1a1e26 0%, #14181f 100%)',
        borderLeft: '1px solid rgba(255,255,255,0.06)',
        boxShadow: '-20px 0 60px rgba(0,0,0,0.6)',
        display: 'flex', flexDirection: 'column',
        fontFamily: 'Inter, system-ui, sans-serif',
        animation: 'slideInRight 0.22s cubic-bezier(0.16,1,0.3,1)',
        overflowY: 'auto',
      }}>
        <style>{`
          @keyframes slideInRight {
            from { transform: translateX(100%); opacity: 0; }
            to   { transform: translateX(0);    opacity: 1; }
          }
        `}</style>

        {/* Header */}
        <div style={{
          padding: '18px 20px 16px',
          borderBottom: '1px solid rgba(255,255,255,0.05)',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          position: 'sticky', top: 0,
          background: 'linear-gradient(180deg, #1a1e26 0%, #14181f 100%)',
        }}>
          <span style={{
            display: 'flex', alignItems: 'center', gap: 7,
            padding: '4px 10px', borderRadius: 99,
            background: `${accent}18`, border: `1px solid ${accent}35`,
            color: accent, fontSize: 10, fontWeight: 700, letterSpacing: '0.1em',
          }}>
            <Icon size={11} strokeWidth={2.5} /> {(marker.type ?? 'DİĞER').toUpperCase()}
          </span>
          <button
            onClick={onClose}
            style={{
              width: 28, height: 28, borderRadius: 8,
              background: 'rgba(255,255,255,0.05)',
              border: '1px solid rgba(255,255,255,0.08)',
              color: '#908f9d', cursor: 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <path d="M18 6L6 18M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div style={{ padding: '20px', flex: 1, display: 'flex', flexDirection: 'column', gap: 20 }}>
          {/* Title */}
          <p style={{
            margin: 0, fontSize: 15, fontWeight: 700,
            lineHeight: 1.5, color: '#f0f2f8',
            fontFamily: 'Manrope, Inter, sans-serif',
          }}>
            {marker.title}
          </p>

          {/* Meta rows */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {/* Date */}
            {marker.published_at && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <div style={{
                  width: 32, height: 32, borderRadius: 8,
                  background: 'rgba(255,255,255,0.04)',
                  border: '1px solid rgba(255,255,255,0.07)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                }}>
                  <CalendarDays size={14} color="#5a5e72" strokeWidth={2} />
                </div>
                <div>
                  <div style={{ fontSize: 11, color: '#dfe2eb', fontWeight: 500 }}>{fmtDate(marker.published_at)}</div>
                  <div style={{ fontSize: 10, color: '#454652', marginTop: 1 }}>{timeAgo(marker.published_at)}</div>
                </div>
              </div>
            )}

            {/* Location */}
            {(marker.district || marker.neighborhood) && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <div style={{
                  width: 32, height: 32, borderRadius: 8,
                  background: 'rgba(255,255,255,0.04)',
                  border: '1px solid rgba(255,255,255,0.07)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                }}>
                  <MapPin size={14} color="#5a5e72" strokeWidth={2} />
                </div>
                <div>
                  {marker.neighborhood && (
                    <div style={{ fontSize: 11, color: '#dfe2eb', fontWeight: 500 }}>{marker.neighborhood}</div>
                  )}
                  {marker.district && (
                    <div style={{ fontSize: 10, color: '#454652', marginTop: 1 }}>{marker.district}</div>
                  )}
                </div>
              </div>
            )}

            {/* Sources */}
            {(marker.sources ?? []).length > 0 && (
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
                <div style={{
                  width: 32, height: 32, borderRadius: 8,
                  background: 'rgba(255,255,255,0.04)',
                  border: '1px solid rgba(255,255,255,0.07)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                }}>
                  <Newspaper size={14} color="#5a5e72" strokeWidth={2} />
                </div>
                <div style={{ paddingTop: 6 }}>
                  {(marker.sources ?? []).map((src, i) => (
                    <span key={i} style={{
                      display: 'inline-block', marginRight: 6,
                      fontSize: 11, color: accent, fontWeight: 600,
                    }}>{src}</span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* CTA footer – per-source links */}
        <div style={{ padding: '14px 20px', borderTop: '1px solid rgba(255,255,255,0.05)' }}>
          {(() => {
            const sources = marker.sources ?? [];
            const urls = marker.urls ?? [];

            // Her kaynak için URL eşleştir (sıra korunsun)
            const entries: { src: string; url: string }[] = sources.map((src, i) => ({
              src,
              url: urls[i] ?? urls[0] ?? '#',
            }));

            if (entries.length === 0) {
              return null;
            }

            if (entries.length === 1) {
              // Tek kaynak: büyük buton
              return (
                <a
                  href={entries[0].url}
                  target="_blank" rel="noreferrer"
                  style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                    width: '100%', background: accent, color: '#0c0f14',
                    fontWeight: 800, fontSize: 12, letterSpacing: '0.04em',
                    padding: '11px 0', borderRadius: 10,
                    textDecoration: 'none', transition: 'opacity 0.15s',
                  }}
                  onMouseOver={e => (e.currentTarget.style.opacity = '0.85')}
                  onMouseOut={e => (e.currentTarget.style.opacity = '1')}
                >
                  {entries[0].src}
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <path d="M5 12h14M12 5l7 7-7 7" />
                  </svg>
                </a>
              );
            }

            // Çoklu kaynak: liste
            return (
              <div>
                <div style={{
                  fontSize: 9, fontWeight: 700, color: '#3d4150',
                  letterSpacing: '0.15em', textTransform: 'uppercase',
                  marginBottom: 10, display: 'flex', alignItems: 'center', gap: 6,
                }}>
                  <div style={{
                    background: `${accent}22`, color: accent,
                    borderRadius: 99, padding: '2px 7px',
                    fontSize: 9, fontWeight: 800,
                  }}>{entries.length}</div>
                  kaynakta yayınlandı
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {entries.map(({ src, url }, i) => (
                    <a
                      key={i}
                      href={url}
                      target="_blank" rel="noreferrer"
                      style={{
                        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                        padding: '9px 12px', borderRadius: 9,
                        background: 'rgba(255,255,255,0.04)',
                        border: '1px solid rgba(255,255,255,0.07)',
                        textDecoration: 'none', transition: 'all 0.15s',
                      }}
                      onMouseOver={e => {
                        e.currentTarget.style.background = `${accent}12`;
                        e.currentTarget.style.borderColor = `${accent}30`;
                      }}
                      onMouseOut={e => {
                        e.currentTarget.style.background = 'rgba(255,255,255,0.04)';
                        e.currentTarget.style.borderColor = 'rgba(255,255,255,0.07)';
                      }}
                    >
                      <span style={{ fontSize: 12, color: '#dfe2eb', fontWeight: 600 }}>{src}</span>
                      <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke={accent} strokeWidth="2.5">
                        <path d="M5 12h14M12 5l7 7-7 7" />
                      </svg>
                    </a>
                  ))}
                </div>
              </div>
            );
          })()}
        </div>
      </aside>
    </>
  );
}

/* ─── Component ───────────────────────────────────────────── */
export default function MapPage() {
  const [allMarkers, setAllMarkers] = useState<MapMarker[]>([]);
  const [markers, setMarkers] = useState<MapMarker[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<MapMarker | null>(null);
  const [activeTypes, setActiveTypes] = useState<Set<EventType>>(
    new Set(EVENT_FILTERS.map(e => e.label))
  );
  const [district, setDistrict] = useState('Tüm İlçeler');
  const [timeRange, setTimeRange] = useState('Tüm Zamanlar');
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

  /* scrape */
  const handleScrape = useCallback(async () => {
    if (scraping) return;
    setScraping(true); setScrapeMsg(null);
    try {
      await newsService.triggerScrape();
      const poll = setInterval(async () => {
        const s = await newsService.getScrapeStatus();
        if (s.status === 'idle') {
          clearInterval(poll); setScraping(false);
          setScrapeMsg(s.last_error ? `Hata: ${s.last_error}` : 'Tamamlandı');
          await loadData();
          setTimeout(() => setScrapeMsg(null), 5000);
        }
      }, 2000);
    } catch (e: any) {
      setScraping(false);
      const isConflict = e.response?.status === 409 || e.message?.includes('409');
      setScrapeMsg(isConflict ? 'Zaten çalışıyor…' : `Hata: ${e.message}`);
      setTimeout(() => setScrapeMsg(null), 5000);
    }
  }, [scraping, loadData]);

  /* filter */
  // MapPage.tsx içindeki filter useEffect bloğu
  useEffect(() => {
    let r = allMarkers.filter(m => {
      const t = (m.type ?? 'Diğer') as EventType;
      return activeTypes.has(t);
    });

    if (district !== 'Tüm İlçeler') r = r.filter(m => m.district === district);

    if (search.trim()) {
      const q = search.toLowerCase();
      r = r.filter(m => m.title?.toLowerCase().includes(q) || m.district?.toLowerCase().includes(q));
    }

    const now = Date.now();
    if (isCustomDate) {
      // Başlangıç tarihi seçiliyse: O günün 00:00'ından büyük olanlar
      if (startDate) {
        const s = new Date(startDate).setHours(0, 0, 0, 0);
        r = r.filter(m => m.published_at && parseUTC(m.published_at) >= s);
      }
      // Bitiş tarihi seçiliyse: O günün 23:59'undan küçük olanlar
      if (endDate) {
        const e = new Date(endDate).setHours(23, 59, 59, 999);
        r = r.filter(m => m.published_at && parseUTC(m.published_at) <= e);
      }
    } else {
      let ms = 0;
      if (timeRange === 'Son 24 Saat') ms = 86400000;
      else if (timeRange === 'Son 3 Gün') ms = 259200000;
      // 1 hafta kontrolü buradan da kaldırıldı

      if (ms > 0) r = r.filter(m => m.published_at && (now - parseUTC(m.published_at)) <= ms);
    }

    setMarkers(r);
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
      <style>{`
        @keyframes _sentinel_spin { to { transform: rotate(360deg); } }
      `}</style>

      {/* Loading overlay */}
      {loading && (
        <div style={{
          position: 'absolute', inset: 0, zIndex: 300,
          background: 'rgba(16,20,26,0.88)', backdropFilter: 'blur(10px)',
          display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center', gap: 16,
        }}>
          <div style={{
            width: 46, height: 46,
            border: '3px solid rgba(182,196,255,0.1)',
            borderTopColor: '#b6c4ff', borderRadius: '50%',
            animation: '_sentinel_spin 0.85s linear infinite',
          }} />
          <span style={{ color: '#b6c4ff', fontSize: 10, fontWeight: 700, letterSpacing: '0.3em' }}>
            YÜKLENIYOR…
          </span>
        </div>
      )}

      {/* ── Header ── */}
      <header style={{
        position: 'fixed', top: 0, width: '100%', height: 60, zIndex: 100,
        background: 'rgba(14,18,24,0.9)',
        backdropFilter: 'blur(20px)',
        borderBottom: '1px solid rgba(255,255,255,0.05)',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0 20px',
        boxSizing: 'border-box',
      }}>
        {/* Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 34, height: 34, borderRadius: 9,
            background: 'linear-gradient(135deg, #1a2e80 0%, #0d1a55 100%)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            border: '1px solid rgba(182,196,255,0.18)',
          }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#b6c4ff" strokeWidth="2">
              <circle cx="12" cy="12" r="2" /><path d="M12 2a10 10 0 0 1 0 20M12 2a10 10 0 0 0 0 20M2 12h20" />
              <path d="M12 2c2.5 2.5 4 5.8 4 10s-1.5 7.5-4 10M12 2C9.5 4.5 8 7.8 8 12s1.5 7.5 4 10" />
            </svg>
          </div>
          <span style={{
            fontFamily: 'Manrope, Inter, sans-serif',
            fontWeight: 800, fontSize: 16, letterSpacing: '-0.01em',
            color: '#e8ecf8',
          }}>Haber Radar</span>
        </div>

        {/* Search */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 9,
          background: '#1a1e26', borderRadius: 10,
          padding: '8px 16px', border: '1px solid rgba(255,255,255,0.06)',
          width: '34%', minWidth: 220,
        }}>
          <Search size={14} color="#3d4150" strokeWidth={2.5} />
          <input
            placeholder="Kocaeli'de ara…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            style={{
              background: 'transparent', border: 'none', outline: 'none',
              fontSize: 13, color: '#dfe2eb', width: '100%',
              fontFamily: 'Inter, system-ui, sans-serif',
            }}
          />
          {search && (
            <button onClick={() => setSearch('')} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#454652', display: 'flex' }}>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path d="M18 6L6 18M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>

        {/* Right: only refresh */}
        <button
          onClick={loadData}
          title="Yenile"
          style={{
            width: 36, height: 36, borderRadius: 9,
            background: 'rgba(255,255,255,0.04)',
            border: '1px solid rgba(255,255,255,0.07)',
            cursor: 'pointer', color: '#b6c4ff',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            transition: 'background 0.15s',
          }}
          onMouseOver={e => (e.currentTarget.style.background = 'rgba(182,196,255,0.1)')}
          onMouseOut={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.04)')}
        >
          <RefreshCw size={15} strokeWidth={2.2} />
        </button>
      </header>

      {/* ── Body ── */}
      <main style={{ display: 'flex', flex: 1, paddingTop: 60, overflow: 'hidden' }}>

        {/* ── Left sidebar ── */}
        <aside style={{
          width: 280, flexShrink: 0,
          background: '#13171e',
          borderRight: '1px solid rgba(255,255,255,0.045)',
          overflowY: 'auto', overflowX: 'hidden',
          zIndex: 40,
        }}>
          <div style={{ padding: '20px 18px', display: 'flex', flexDirection: 'column', gap: 24 }}>

            {/* Filters section */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>

              {/* İlçe */}
              <div>
                <label style={labelStyle}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                    <MapPin size={9} strokeWidth={2.5} /> İlçe
                  </span>
                </label>
                <div style={{ position: 'relative' }}>
                  <select value={district} onChange={e => setDistrict(e.target.value)} style={inputStyle}>
                    {DISTRICTS.map(d => <option key={d}>{d}</option>)}
                  </select>
                  <ChevronDown size={13} strokeWidth={2} color="#3d4150"
                    style={{ position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)', pointerEvents: 'none' }} />
                </div>
              </div>

              {/* Zaman aralığı */}
              <div>
                <label style={labelStyle}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                    <Clock size={9} strokeWidth={2.5} /> Zaman Aralığı
                  </span>
                </label>
                <div style={{ position: 'relative' }}>
                  <select value={timeRange} onChange={e => handleTimeChange(e.target.value)} style={inputStyle}>
                    {TIME_RANGES.map(r => <option key={r}>{r}</option>)}
                    <option>Özel Tarih Seç...</option>
                  </select>
                  <ChevronDown size={13} strokeWidth={2} color="#3d4150"
                    style={{ position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)', pointerEvents: 'none' }} />
                </div>
                {isCustomDate && (
                  <div style={{ marginTop: 10, display: 'flex', gap: 8 }}>
                    <input type="date" style={{ ...inputStyle, padding: '7px 8px' }} onChange={e => setStartDate(e.target.value)} />
                    <input type="date" style={{ ...inputStyle, padding: '7px 8px' }} onChange={e => setEndDate(e.target.value)} />
                  </div>
                )}
              </div>

              {/* Olay türü */}
              <div>
                <label style={labelStyle}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                    <Filter size={9} strokeWidth={2.5} /> Olay Türü
                  </span>
                </label>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {EVENT_FILTERS.map(({ label, Icon, color }) => {
                    const on = activeTypes.has(label);
                    return (
                      <label key={label} style={{
                        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                        padding: '9px 11px', borderRadius: 9, cursor: 'pointer',
                        background: on ? `${color}12` : 'rgba(255,255,255,0.02)',
                        border: `1px solid ${on ? color + '28' : 'rgba(255,255,255,0.04)'}`,
                        transition: 'all 0.15s',
                      }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
                          <Icon size={15} color={on ? color : '#3d4150'} strokeWidth={2} />
                          <span style={{ fontSize: 12, fontWeight: 500, color: on ? '#dfe2eb' : '#4a4e5d' }}>{label}</span>
                        </div>
                        <input
                          type="checkbox" checked={on} onChange={() => toggleType(label)}
                          style={{ accentColor: color, width: 14, height: 14, cursor: 'pointer' }}
                        />
                      </label>
                    );
                  })}
                </div>
              </div>

              {/* Veri Çek button */}
              <button
                onClick={handleScrape}
                disabled={scraping}
                style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 7,
                  padding: '10px 0', borderRadius: 10, width: '100%',
                  background: scraping ? 'rgba(255,255,255,0.04)' : 'rgba(182,196,255,0.1)',
                  border: `1px solid ${scraping ? 'rgba(255,255,255,0.06)' : 'rgba(182,196,255,0.2)'}`,
                  color: scraping ? '#3d4150' : '#b6c4ff',
                  fontSize: 12, fontWeight: 600, cursor: scraping ? 'not-allowed' : 'pointer',
                  transition: 'all 0.15s',
                }}
              >
                <RefreshCw size={13} strokeWidth={2.2}
                  style={{ animation: scraping ? '_sentinel_spin 0.9s linear infinite' : 'none' }} />
                {scraping ? 'Çekiliyor…' : scrapeMsg ?? 'Veri Çek'}
              </button>
            </div>

            {/* Divider */}
            <div style={{ height: 1, background: 'rgba(255,255,255,0.045)', margin: '0 -2px' }} />

            {/* News feed */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, paddingBottom: 20 }}>
              {/* Section header with count */}
              <div style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                position: 'sticky', top: 0,
                background: '#13171e', paddingBottom: 8, paddingTop: 2,
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                  <div style={{
                    width: 6, height: 6, borderRadius: '50%',
                    background: '#ef4444', boxShadow: '0 0 7px #ef4444',
                  }} />
                  <span style={{ fontSize: 9, fontWeight: 700, color: '#3d4150', letterSpacing: '0.18em', textTransform: 'uppercase' }}>
                    Son Haberler
                  </span>
                </div>
                <span style={{
                  fontSize: 10, fontWeight: 700,
                  color: '#5a5e72',
                  background: 'rgba(255,255,255,0.05)',
                  border: '1px solid rgba(255,255,255,0.07)',
                  borderRadius: 99, padding: '2px 8px',
                }}>
                  {markers.length}
                </span>
              </div>

              {markers.length === 0 && !loading && (
                <div style={{ color: '#3d4150', fontSize: 12, textAlign: 'center', padding: '28px 0' }}>
                  Haber bulunamadı.
                </div>
              )}

              {markers.map(news => {
                const accent = accentOf(news.type);
                const Icon = iconOf(news.type);
                return (
                  <div
                    key={news._id}
                    onClick={() => setSelected(news)}
                    style={{
                      background: selected?._id === news._id
                        ? `${accent}10`
                        : 'rgba(255,255,255,0.025)',
                      border: `1px solid ${selected?._id === news._id ? accent + '25' : 'rgba(255,255,255,0.04)'}`,
                      borderRadius: 10, padding: '11px 12px',
                      cursor: 'pointer', transition: 'all 0.15s',
                      display: 'flex', gap: 10, alignItems: 'flex-start',
                    }}
                    onMouseOver={e => { if (selected?._id !== news._id) e.currentTarget.style.background = 'rgba(255,255,255,0.05)'; }}
                    onMouseOut={e => { if (selected?._id !== news._id) e.currentTarget.style.background = 'rgba(255,255,255,0.025)'; }}
                  >
                    {/* Icon bubble */}
                    <div style={{
                      flexShrink: 0, width: 32, height: 32, borderRadius: 8,
                      background: `${accent}15`,
                      border: `1px solid ${accent}20`,
                      display: 'flex', alignItems: 'center', justifyContent: 'center', marginTop: 1,
                    }}>
                      <Icon size={14} color={accent} strokeWidth={2} />
                    </div>

                    <div style={{ flex: 1, minWidth: 0 }}>
                      <p style={{
                        margin: 0, fontSize: 12, fontWeight: 600,
                        lineHeight: 1.45, color: '#dfe2eb',
                        overflow: 'hidden', display: '-webkit-box',
                        WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' as const,
                      }}>{news.title}</p>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 5, marginTop: 5, flexWrap: 'wrap' }}>
                        {news.district && (
                          <span style={{ fontSize: 9, fontWeight: 600, color: '#4a4e5d', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                            {news.district}
                          </span>
                        )}
                        {news.district && <span style={{ fontSize: 8, color: '#252930' }}>•</span>}
                        <span style={{ fontSize: 9, fontWeight: 700, color: accent, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                          {news.type}
                        </span>
                        {news.published_at && (
                          <>
                            <span style={{ fontSize: 8, color: '#252930' }}>•</span>
                            <span style={{ fontSize: 9, color: '#3d4150' }}>{timeAgo(news.published_at)}</span>
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
          <MapContainer
            markers={markers}
            onMarkerClick={(m) => setSelected(m)}
            selectedId={selected?._id ?? null}
          />
        </section>
      </main>

      {/* ── Detail sidebar ── */}
      {selected && <DetailPanel marker={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}