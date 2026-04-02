import { GoogleMap, useJsApiLoader, OverlayView, InfoWindow } from '@react-google-maps/api';
import { useState, useCallback } from 'react';
import { MapMarker } from '../../types/news';

/* ─── Constants ───────────────────────────────────────────── */
const KOCAELI_CENTER = { lat: 40.7654, lng: 29.9408 };
const MAP_CONTAINER_STYLE = { width: '100%', height: '100%' };

/* ─── Dark map style ──────────────────────────────────────── */
const DARK_MAP_STYLE: google.maps.MapTypeStyle[] = [
  { elementType: 'geometry', stylers: [{ color: '#10141a' }] },
  { elementType: 'labels.text.stroke', stylers: [{ color: '#10141a' }] },
  { elementType: 'labels.text.fill', stylers: [{ color: '#454652' }] },
  { featureType: 'administrative.locality', elementType: 'labels.text.fill', stylers: [{ color: '#c6c5d4' }] },
  { featureType: 'poi', elementType: 'labels', stylers: [{ visibility: 'off' }] },
  { featureType: 'poi.park', elementType: 'geometry', stylers: [{ color: '#13191f' }] },
  { featureType: 'road', elementType: 'geometry', stylers: [{ color: '#1c2026' }] },
  { featureType: 'road', elementType: 'geometry.stroke', stylers: [{ color: '#0a0e14' }] },
  { featureType: 'road', elementType: 'labels.text.fill', stylers: [{ color: '#454652' }] },
  { featureType: 'road.highway', elementType: 'geometry', stylers: [{ color: '#242830' }] },
  { featureType: 'road.highway', elementType: 'geometry.stroke', stylers: [{ color: '#0a0e14' }] },
  { featureType: 'road.highway', elementType: 'labels.text.fill', stylers: [{ color: '#616672' }] },
  { featureType: 'transit', elementType: 'geometry', stylers: [{ color: '#13191f' }] },
  { featureType: 'water', elementType: 'geometry', stylers: [{ color: '#050a10' }] },
  { featureType: 'water', elementType: 'labels.text.fill', stylers: [{ color: '#1c2026' }] },
];

/* ─── Marker config per type ──────────────────────────────── */
type Cfg = { bg: string; border: string; emoji: string; label: string; ping: string };

const TYPE_CFG: Record<string, Cfg> = {
  'Trafik Kazası': { bg: '#f59e0b', border: '#d97706', emoji: '🚗', label: 'TRAFİK KAZASI', ping: 'rgba(245,158,11,0.4)' },
  'Yangın': { bg: '#ef4444', border: '#dc2626', emoji: '🔥', label: 'YANGIN', ping: 'rgba(239,68,68,0.4)' },
  'Elektrik Kesintisi': { bg: '#b6c4ff', border: '#7391ff', emoji: '⚡', label: 'ELEKTRİK', ping: 'rgba(182,196,255,0.4)' },
  'Hırsızlık': { bg: '#a855f7', border: '#9333ea', emoji: '⛓️‍💥', label: 'HIRSIZLIK', ping: 'rgba(168,85,247,0.4)' },
  'Kültürel Etkinlikler': { bg: '#a43d77', border: '#8b0b54', emoji: '🎭', label: 'KÜLTÜR', ping: 'rgba(34,197,94,0.4)' },
};
const DEFAULT_CFG: Cfg = { bg: '#908f9d', border: '#22c55e', emoji: '〰️', label: 'DİĞER', ping: 'rgba(144,143,157,0.4)' };
const getCfg = (type: string): Cfg => TYPE_CFG[type] ?? DEFAULT_CFG;

/* ─── Inject keyframes once ───────────────────────────────── */
let keyframesInjected = false;
const injectKeyframes = () => {
  if (keyframesInjected) return;
  keyframesInjected = true;
  const s = document.createElement('style');
  s.textContent = `
    @keyframes _sentinel_ping {
      0%   { transform: scale(1);   opacity: 0.7; }
      100% { transform: scale(2.6); opacity: 0;   }
    }
    @keyframes _sentinel_spin {
      to { transform: rotate(360deg); }
    }
    /* Strip Google's InfoWindow chrome */
    .gm-style .gm-style-iw-c {
      padding: 0 !important;
      border-radius: 20px !important;
      background: transparent !important;
      box-shadow: none !important;
      border: none !important;
      overflow: visible !important;
    }
    .gm-style .gm-style-iw-d {
      overflow: hidden !important;
      padding: 0 !important;
    }
    .gm-ui-hover-effect { display: none !important; }
    .gm-style-iw-t::after { display: none !important; }
    .gm-style-iw-tc { display: none !important; }
  `;
  document.head.appendChild(s);
};

/* ─── Pin component ───────────────────────────────────────── */
interface PinProps { marker: MapMarker; isActive: boolean; onClick: () => void }

function NewsPin({ marker, isActive, onClick }: PinProps) {
  injectKeyframes();
  const cfg = getCfg(marker.type);
  const size = isActive ? 46 : 38;

  return (
    <OverlayView
      position={{ lat: marker.lat, lng: marker.lon }}
      mapPaneName={OverlayView.OVERLAY_MOUSE_TARGET}
      getPixelPositionOffset={() => ({ x: -size / 2, y: -size / 2 })}
    >
      <div onClick={onClick} style={{ width: size, height: size, position: 'relative', cursor: 'pointer' }}>
        {/* Ping */}
        {isActive && (
          <div style={{
            position: 'absolute', inset: 0,
            borderRadius: '50%',
            background: cfg.ping,
            animation: '_sentinel_ping 1.3s ease-out infinite',
          }} />
        )}
        {/* Body */}
        <div style={{
          position: 'absolute', inset: 0,
          borderRadius: '50%',
          background: cfg.bg,
          border: `3px solid ${cfg.border}`,
          boxShadow: `0 4px 18px ${cfg.ping}, 0 2px 6px rgba(0,0,0,0.55)`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: isActive ? 21 : 17,
          transition: 'all 0.18s ease',
          userSelect: 'none',
        }}>
          {cfg.emoji}
        </div>
      </div>
    </OverlayView>
  );
}

/* ─── Popup ───────────────────────────────────────────────── */
interface PopupProps { marker: MapMarker; onClose: () => void }

function SentinelPopup({ marker, onClose }: PopupProps) {
  const cfg = getCfg(marker.type);
  const date = marker.published_at
    ? new Date(marker.published_at).toLocaleDateString('tr-TR', { day: '2-digit', month: '2-digit', year: 'numeric' })
    : '—';

  const row = (icon: string, content: React.ReactNode) => (
    <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
      <span style={{ fontSize: 13, flexShrink: 0, marginTop: 1 }}>{icon}</span>
      <span style={{ fontSize: 11, color: '#908f9d', lineHeight: 1.5 }}>{content}</span>
    </div>
  );

  return (
    <InfoWindow
      position={{ lat: marker.lat, lng: marker.lon }}
      onCloseClick={onClose}
      options={{
        disableAutoPan: false,
        pixelOffset: new window.google.maps.Size(0, -56),
        maxWidth: 300,
      }}
    >
      {/* negative margin eats Google's default padding */}
      <div style={{ margin: -14, background: 'transparent' }}>
        <div style={{
          width: 282,
          background: 'linear-gradient(145deg, #1e232b 0%, #181c22 100%)',
          border: '1px solid rgba(255,255,255,0.08)',
          borderRadius: 20,
          padding: '20px',
          fontFamily: "'Inter', system-ui, sans-serif",
          color: '#dfe2eb',
          position: 'relative',
          overflow: 'hidden',
          boxShadow: '0 24px 60px rgba(0,0,0,0.75), 0 0 0 1px rgba(255,255,255,0.04)',
        }}>
          {/* Glow */}
          <div style={{
            position: 'absolute', top: -60, right: -60,
            width: 130, height: 130, borderRadius: '50%',
            background: cfg.ping, filter: 'blur(45px)',
            pointerEvents: 'none',
          }} />

          {/* Badge + close */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
            <span style={{
              background: `${cfg.bg}1a`, color: cfg.bg,
              fontSize: 9, fontWeight: 800,
              letterSpacing: '0.14em', textTransform: 'uppercase' as const,
              padding: '4px 10px', borderRadius: 99,
              border: `1px solid ${cfg.bg}40`,
            }}>
              {cfg.emoji} {cfg.label}
            </span>
            <button onClick={onClose} style={{
              background: 'rgba(255,255,255,0.06)',
              border: '1px solid rgba(255,255,255,0.08)',
              borderRadius: 99, width: 26, height: 26,
              cursor: 'pointer', color: '#908f9d',
              fontSize: 13, lineHeight: 1,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontFamily: 'system-ui',
            }}>✕</button>
          </div>

          {/* Title */}
          <p style={{
            fontFamily: "'Manrope', 'Inter', sans-serif",
            fontWeight: 800, fontSize: 14,
            lineHeight: 1.45, color: '#fff',
            margin: '0 0 14px',
          }}>
            {marker.title}
          </p>

          {/* Meta */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 18 }}>
            {row('📅', date)}
            {(marker.district || marker.neighborhood) && row('📍',
              [marker.neighborhood, marker.district].filter(Boolean).join(', ')
            )}
            {(marker.sources ?? []).length > 0 && row('📰', (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                Kaynaklar:
                {(marker.sources ?? []).map((src, i) => (
                  <strong key={i} style={{ color: cfg.bg }}>
                    {src}{(marker.sources ?? []).length - 1 !== i ? ',' : ''}
                  </strong>
                ))}
              </div>
            ))}
          </div>

          {/* CTA */}
          <a
            href={marker.urls?.[0] ?? '#'}
            target="_blank"
            rel="noreferrer"
            style={{
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
              width: '100%', background: cfg.bg, color: '#10141a',
              fontWeight: 800, fontSize: 12, letterSpacing: '0.04em',
              padding: '11px 0', borderRadius: 12,
              textDecoration: 'none',
              boxShadow: `0 6px 22px ${cfg.ping}`,
              transition: 'opacity 0.15s',
            }}
            onMouseOver={e => (e.currentTarget.style.opacity = '0.82')}
            onMouseOut={e => (e.currentTarget.style.opacity = '1')}
          >
            Habere Git →
          </a>
        </div>
      </div>
    </InfoWindow>
  );
}

/* ─── Main ────────────────────────────────────────────────── */
interface Props { markers: MapMarker[] }

const MapContainer = ({ markers }: Props) => {
  const [selected, setSelected] = useState<MapMarker | null>(null);

  const { isLoaded } = useJsApiLoader({
    id: 'google-map-script',
    googleMapsApiKey: import.meta.env.VITE_GOOGLE_MAPS_API_KEY ?? '',
  });

  const handleClick = useCallback((m: MapMarker) => {
    setSelected(prev => (prev?._id === m._id ? null : m));
  }, []);

  if (!isLoaded) {
    return (
      <div style={{
        width: '100%', height: '100%', background: '#10141a',
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center', gap: 14,
      }}>
        <div style={{
          width: 44, height: 44,
          border: '4px solid rgba(182,196,255,0.12)',
          borderTopColor: '#b6c4ff', borderRadius: '50%',
          animation: '_sentinel_spin 0.9s linear infinite',
        }} />
        <span style={{
          fontFamily: 'Inter, sans-serif', color: '#b6c4ff',
          fontSize: 10, fontWeight: 700, letterSpacing: '0.3em',
        }}>HARİTA YÜKLENİYOR…</span>
      </div>
    );
  }

  return (
    <GoogleMap
      mapContainerStyle={MAP_CONTAINER_STYLE}
      center={KOCAELI_CENTER}
      zoom={11}
      options={{
        styles: DARK_MAP_STYLE,
        disableDefaultUI: true,
        gestureHandling: 'greedy',
        clickableIcons: false,
      }}
      onClick={() => setSelected(null)}
    >
      {Array.isArray(markers) && markers.map((m, index) => {
        if (typeof m.lat !== 'number' || typeof m.lon !== 'number') return null;

        // Çakışmayı önlemek için belirgin bir dairesel sapma (Jittering) ekleyelim
        // 0.00015 değeri zoom 11'de 1 pikselden küçüktü, bu yüzden üst üste biniyordu.
        // Daha geniş bir radius kullanarak pinlerin etrafa yayılmasını sağlıyoruz.
        const radius = 0.004 + ((index % 3) * 0.002);
        const jitterLat = m.lat + (Math.sin(index * 2.4) * radius);
        const jitterLon = m.lon + (Math.cos(index * 2.4) * radius);

        return (
          <NewsPin
            key={m._id}
            marker={{ ...m, lat: jitterLat, lon: jitterLon }}
            isActive={selected?._id === m._id}
            onClick={() => handleClick(m)}
          />
        );
      })}

      {selected && <SentinelPopup marker={selected} onClose={() => setSelected(null)} />}
    </GoogleMap>
  );
};

export default MapContainer;