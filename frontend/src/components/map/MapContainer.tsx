import { GoogleMap, useJsApiLoader, OverlayView } from '@react-google-maps/api';
import { useCallback } from 'react';
import { MapMarker } from '../../types/news';

/* ─── Constants ───────────────────────────────────────────── */
const KOCAELI_CENTER = { lat: 40.7654, lng: 29.9408 };
const MAP_CONTAINER_STYLE = { width: '100%', height: '100%' };

/* ─── Dark map style ──────────────────────────────────────── */
const DARK_MAP_STYLE: google.maps.MapTypeStyle[] = [
  { elementType: 'geometry',             stylers: [{ color: '#10141a' }] },
  { elementType: 'labels.text.stroke',   stylers: [{ color: '#10141a' }] },
  { elementType: 'labels.text.fill',     stylers: [{ color: '#454652' }] },
  { featureType: 'administrative.locality', elementType: 'labels.text.fill', stylers: [{ color: '#c6c5d4' }] },
  { featureType: 'poi',            elementType: 'labels',          stylers: [{ visibility: 'off' }] },
  { featureType: 'poi.park',       elementType: 'geometry',        stylers: [{ color: '#13191f' }] },
  { featureType: 'road',           elementType: 'geometry',        stylers: [{ color: '#1c2026' }] },
  { featureType: 'road',           elementType: 'geometry.stroke', stylers: [{ color: '#0a0e14' }] },
  { featureType: 'road',           elementType: 'labels.text.fill',stylers: [{ color: '#454652' }] },
  { featureType: 'road.highway',   elementType: 'geometry',        stylers: [{ color: '#242830' }] },
  { featureType: 'road.highway',   elementType: 'geometry.stroke', stylers: [{ color: '#0a0e14' }] },
  { featureType: 'road.highway',   elementType: 'labels.text.fill',stylers: [{ color: '#616672' }] },
  { featureType: 'transit',        elementType: 'geometry',        stylers: [{ color: '#13191f' }] },
  { featureType: 'water',          elementType: 'geometry',        stylers: [{ color: '#050a10' }] },
  { featureType: 'water',          elementType: 'labels.text.fill',stylers: [{ color: '#1c2026' }] },
];

/* ─── Marker config per type ──────────────────────────────── */
type Cfg = { bg: string; border: string; ping: string };

const TYPE_CFG: Record<string, Cfg> = {
  'Trafik Kazası':       { bg: '#f59e0b', border: '#d97706', ping: 'rgba(245,158,11,0.4)' },
  'Yangın':              { bg: '#ef4444', border: '#dc2626', ping: 'rgba(239,68,68,0.4)'  },
  'Elektrik Kesintisi':  { bg: '#b6c4ff', border: '#7391ff', ping: 'rgba(182,196,255,0.4)'},
  'Hırsızlık':           { bg: '#a855f7', border: '#9333ea', ping: 'rgba(168,85,247,0.4)' },
  'Kültürel Etkinlikler':{ bg: '#a43d77', border: '#8b0b54', ping: 'rgba(164,61,119,0.4)' },
};
const DEFAULT_CFG: Cfg = { bg: '#22c55e', border: '#16a34a', ping: 'rgba(34,197,94,0.4)' };
const getCfg = (type: string): Cfg => TYPE_CFG[type] ?? DEFAULT_CFG;

/* ─── Keyframes ───────────────────────────────────────────── */
let kfInjected = false;
const injectKeyframes = () => {
  if (kfInjected) return;
  kfInjected = true;
  const s = document.createElement('style');
  s.textContent = `
    @keyframes _sentinel_ping {
      0%   { transform: scale(1);   opacity: 0.7; }
      100% { transform: scale(2.6); opacity: 0;   }
    }
    @keyframes _sentinel_spin { to { transform: rotate(360deg); } }
  `;
  document.head.appendChild(s);
};

/* ─── Lucide-style SVG icons for pin body ─────────────────── */
const PinIcon = ({ type, size = 14 }: { type: string; size?: number }) => {
  const s = { width: size, height: size, display: 'flex' as const };
  const stroke = '#0c0f14';
  const sw = '2';
  switch (type) {
    case 'Trafik Kazası':
      return <svg style={s} viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth={sw}><rect x="1" y="3" width="15" height="13" rx="2"/><path d="m16 8 4 1 2 3v4h-6V8z"/><circle cx="5.5" cy="18.5" r="2.5"/><circle cx="18.5" cy="18.5" r="2.5"/></svg>;
    case 'Yangın':
      return <svg style={s} viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth={sw}><path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"/></svg>;
    case 'Elektrik Kesintisi':
      return <svg style={s} viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth={sw}><path d="M13 2 3 14h9l-1 8 10-12h-9l1-8z"/></svg>;
    case 'Hırsızlık':
      return <svg style={s} viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth={sw}><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>;
    case 'Kültürel Etkinlikler':
      return <svg style={s} viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth={sw}><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>;
    default:
      return <svg style={s} viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth={sw}><circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01"/></svg>;
  }
};

/* ─── Pin component ───────────────────────────────────────── */
interface PinProps {
  marker: MapMarker;
  isActive: boolean;
  onClick: () => void;
}

function NewsPin({ marker, isActive, onClick }: PinProps) {
  injectKeyframes();
  const cfg = getCfg(marker.type);
  const size = isActive ? 44 : 36;

  return (
    <OverlayView
      position={{ lat: marker.lat, lng: marker.lon }}
      mapPaneName={OverlayView.OVERLAY_MOUSE_TARGET}
      getPixelPositionOffset={() => ({ x: -size / 2, y: -size / 2 })}
    >
      <div onClick={onClick} style={{ width: size, height: size, position: 'relative', cursor: 'pointer' }}>
        {/* Pulse ring */}
        {isActive && (
          <div style={{
            position: 'absolute', inset: 0, borderRadius: '50%',
            background: cfg.ping,
            animation: '_sentinel_ping 1.4s ease-out infinite',
          }} />
        )}
        {/* Body */}
        <div style={{
          position: 'absolute', inset: 0, borderRadius: '50%',
          background: cfg.bg,
          border: `2.5px solid ${cfg.border}`,
          boxShadow: `0 3px 14px ${cfg.ping}, 0 2px 6px rgba(0,0,0,0.5)`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          transition: 'all 0.18s ease',
        }}>
          <PinIcon type={marker.type} size={isActive ? 18 : 15}/>
        </div>
      </div>
    </OverlayView>
  );
}

/* ─── Main ────────────────────────────────────────────────── */
interface Props {
  markers: MapMarker[];
  onMarkerClick?: (m: MapMarker) => void;
  selectedId?: string | null;
}

const MapContainer = ({ markers, onMarkerClick, selectedId }: Props) => {
  const { isLoaded } = useJsApiLoader({
    id: 'google-map-script',
    googleMapsApiKey: import.meta.env.VITE_GOOGLE_MAPS_API_KEY ?? '',
  });

  const handleClick = useCallback((m: MapMarker) => {
    onMarkerClick?.(m);
  }, [onMarkerClick]);

  if (!isLoaded) {
    return (
      <div style={{
        width: '100%', height: '100%', background: '#10141a',
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center', gap: 14,
      }}>
        <div style={{
          width: 40, height: 40,
          border: '3px solid rgba(182,196,255,0.1)',
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
    >
      {Array.isArray(markers) && markers.map((m, index) => {
        if (typeof m.lat !== 'number' || typeof m.lon !== 'number') return null;

        const radius   = 0.004 + ((index % 3) * 0.002);
        const jitterLat = m.lat + (Math.sin(index * 2.4) * radius);
        const jitterLon = m.lon + (Math.cos(index * 2.4) * radius);

        return (
          <NewsPin
            key={m._id}
            marker={{ ...m, lat: jitterLat, lon: jitterLon }}
            isActive={selectedId === m._id}
            onClick={() => handleClick(m)}
          />
        );
      })}
    </GoogleMap>
  );
};

export default MapContainer;