import { useEffect, useState } from 'react';
import { styled } from '@stitches/react';
import MapContainer from '../components/map/MapContainer';
import { newsService } from '../api/newsService';
import { MapMarker } from '../types/news';

// --- YENİ PROFESYONEL STYLED COMPONENTS ---

// Tüm ekranı kaplayan ana kapsayıcı
const MainLayout = styled('main', {
  width: '100vw',
  height: '100vh',
  position: 'relative',
  overflow: 'hidden',
});

// Haritanın üzerinde yüzen Filtre Kartı
const FloatingFilterCard = styled('div', {
  position: 'absolute',
  top: '20px',
  left: '20px',
  width: '320px',
  background: 'rgba(255, 255, 255, 0.9)',
  backdropFilter: 'blur(12px)',
  padding: '1.5rem',
  borderRadius: '20px',
  boxShadow: '0 10px 40px rgba(0, 0, 0, 0.15)',
  zIndex: 1000, // En üstte olduğundan emin olalım
  border: '1px solid rgba(255, 255, 255, 0.4)',
  pointerEvents: 'auto', // Tıklanabilir olmasını sağlar
});

const CardTitle = styled('h2', {
  fontSize: '1.1rem',
  fontWeight: 'bold',
  marginBottom: '1rem',
  color: '#333',
});

// --- ANA BİLEŞEN ---

export default function MapPage() {
  const [markers, setMarkers] = useState<MapMarker[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadData = async () => {
      try {
        const response = await newsService.getMarkers();
        if (response && Array.isArray(response.markers)) {
          setMarkers(response.markers);
        }
      } catch (error) {
        console.error("Veri çekilirken hata:", error);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, []);

  // MapPage.tsx içinde return kısmını şu şekilde güncelle:

  return (
    <MainLayout>
      {/* LOADING EKRANI (TypeScript hatasını çözer ve profesyonel durur) */}
      {loading && (
        <div style={{
          position: 'absolute', top: 0, left: 0, width: '100%', height: '100%',
          background: 'rgba(255,255,255,0.7)', zIndex: 100,
          display: 'flex', alignItems: 'center', justifyContent: 'center'
        }}>
          <strong>Haberler Radar Tarafından Taranıyor...</strong>
        </div>
      )}

      <FloatingFilterCard>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '15px' }}>
          <CardTitle style={{ margin: 0 }}>Haber Radar</CardTitle>
          <span style={{ fontSize: '0.7rem', color: '#ff4d4f', fontWeight: 'bold', border: '1px solid #ff4d4f', padding: '2px 6px', borderRadius: '10px' }}>CANLI</span>
        </div>

        <div style={{ maxHeight: '400px', overflowY: 'auto', paddingRight: '5px' }}>
          {markers.map((news) => (
            <div
              key={news._id}
              onClick={() => {/* Buraya haritayı o noktaya odaklama kodu gelecek */ }}
              style={{
                padding: '12px', background: '#fff', borderRadius: '12px', marginBottom: '10px',
                cursor: 'pointer', border: '1px solid #eee', transition: 'all 0.2s'
              }}
              onMouseOver={(e) => e.currentTarget.style.borderColor = '#007bff'}
              onMouseOut={(e) => e.currentTarget.style.borderColor = '#eee'}
            >
              <div style={{ fontSize: '0.85rem', fontWeight: 'bold', color: '#222' }}>{news.title}</div>
              <div style={{ fontSize: '0.7rem', color: '#888', marginTop: '5px' }}>📍 {news.district} | {news.type}</div>
            </div>
          ))}
        </div>
      </FloatingFilterCard>

      <MapContainer markers={markers} />
    </MainLayout>
  );
}