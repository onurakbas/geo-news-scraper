import { GoogleMap, useJsApiLoader, Marker, InfoWindow } from '@react-google-maps/api';
import { useState } from 'react';
import { MapMarker } from '../../types/news';

const KOCAELI_CENTER = { lat: 40.7654, lng: 29.9408 };
const mapContainerStyle = { width: '100%', height: '100%' };

// Haber türüne göre iğne rengi belirleme fonksiyonu
const getMarkerIcon = (type: string) => {
  const color = type === 'Yangın' ? 'red' : type === 'Kaza' ? 'orange' : 'blue';
  return `http://maps.google.com/mapfiles/ms/icons/${color}-dot.png`;
};

interface Props {
  markers: MapMarker[];
}

const MapContainer = ({ markers }: Props) => {
  const [selected, setSelected] = useState<MapMarker | null>(null);

  const { isLoaded } = useJsApiLoader({
    id: 'google-map-script',
    googleMapsApiKey: import.meta.env.VITE_GOOGLE_MAPS_API_KEY || "",
  });

  return isLoaded ? (
    <GoogleMap
      mapContainerStyle={mapContainerStyle}
      center={KOCAELI_CENTER}
      zoom={11}
      options={{
        // Harita butonlarını kartın altından çekip başka yere taşıyoruz
        zoomControlOptions: { position: 3 }, // Sağ alt (BOTTOM_RIGHT)
        streetViewControl: false, // Gereksizse kapat alanı ferahlat
        mapTypeControlOptions: { position: 1 }, // Sağ üst (TOP_RIGHT)
        fullscreenControlOptions: { position: 9 }, // Sağ orta (RIGHT_CENTER)
      }}
    >
      {Array.isArray(markers) && markers.map((m) => (
        <Marker
          key={m._id}
          position={{
            lat: m.lat,
            lng: m.lon
          }}
          icon={getMarkerIcon(m.type)}
          onClick={() => setSelected(m)} // Tıklayınca haberi seç
        />
      ))}

      {/* HABER DETAY PENCERESİ (POPUP) */}
      {selected && (
        <InfoWindow
          position={{
            lat: selected.lat,
            lng: selected.lon
          }}
          onCloseClick={() => setSelected(null)}
        >
          {/* InfoWindow içeriğini zenginleştiriyoruz */}
          <div style={{ padding: '12px', maxWidth: '280px', color: '#1a1a1b' }}>
            <div style={{ fontSize: '0.75rem', color: '#ff4d4f', fontWeight: 600, marginBottom: '4px', textTransform: 'uppercase' }}>
              {selected.type}
            </div>
            <h3 style={{ margin: '0 0 8px 0', fontSize: '1rem', lineHeight: '1.4', fontWeight: 'bold' }}>
              {selected.title}
            </h3>

            <div style={{ fontSize: '0.8rem', color: '#555', marginBottom: '12px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <span>📍 {selected.district}</span>
              {/* Tarih formatını güzelleştiriyoruz */}
              <span>📅 {new Date(selected.published_at || Date.now()).toLocaleDateString('tr-TR')}</span>
            </div>

            <div style={{ borderTop: '1px solid #eee', paddingTop: '10px', marginTop: '10px' }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 'bold', color: '#888' }}>KAYNAKLAR:</span>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '5px', marginTop: '5px' }}>
                {/* Çoklu kaynakları dökümana uygun listeliyoruz */}
                {selected.sources?.map((source, index) => (
                  <span key={index} style={{ background: '#f0f2f5', padding: '2px 8px', borderRadius: '4px', fontSize: '0.7rem' }}>
                    {source}
                  </span>
                ))}
              </div>
            </div>

            <a
              href={selected.urls[0]}
              target="_blank"
              rel="noreferrer"
              style={{
                display: 'block', textAlign: 'center', background: '#007bff', color: '#fff',
                padding: '8px', borderRadius: '8px', textDecoration: 'none', fontWeight: 'bold',
                marginTop: '15px', fontSize: '0.85rem'
              }}
            >
              Habere Git →
            </a>
          </div>
        </InfoWindow>
      )}
    </GoogleMap>
  ) : <div>Yükleniyor...</div>;
};

export default MapContainer;