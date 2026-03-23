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
          <div style={{ padding: '10px', maxWidth: '250px' }}>
            <h3 style={{ margin: '0 0 8px 0', fontSize: '1rem' }}>{selected.title}</h3>
            <p style={{ fontSize: '0.85rem', color: '#666' }}>{selected.district} / {selected.type}</p>
            <a 
              href={selected.urls[0]} 
              target="_blank" 
              rel="noreferrer"
              style={{ color: '#007bff', textDecoration: 'none', fontWeight: 'bold' }}
            >
              Haberin Kaynağına Git →
            </a>
          </div>
        </InfoWindow>
      )}
    </GoogleMap>
  ) : <div>Yükleniyor...</div>;
};

export default MapContainer;