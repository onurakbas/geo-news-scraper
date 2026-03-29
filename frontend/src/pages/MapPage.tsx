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
        <CardTitle>Haber Radar</CardTitle>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {/* İlçe Filtresi */}
          <div>
            <label style={{ fontSize: '0.75rem', fontWeight: 'bold', color: '#666' }}>İlçe Seçin</label>
            <select style={{ width: '100%', padding: '8px', borderRadius: '8px', border: '1px solid #ddd', marginTop: '4px' }}>
              <option value="">Tüm Kocaeli</option>
              <option value="izmit">İzmit</option>
              <option value="gebze">Gebze</option>
              <option value="kartepe">Kartepe</option>
            </select>
          </div>

          {/* Tür Filtresi */}
          <div>
            <label style={{ fontSize: '0.75rem', fontWeight: 'bold', color: '#666' }}>Olay Türü</label>
            <select style={{ width: '100%', padding: '8px', borderRadius: '8px', border: '1px solid #ddd', marginTop: '4px' }}>
              <option value="">Tüm Olaylar</option>
              <option value="trafik">Trafik Kazası</option>
              <option value="yangin">Yangın</option>
              <option value="hirsizlik">Hırsızlık</option>
            </select>
          </div>

          {/* Tarih Filtresi */}
          <div>
            <label style={{ fontSize: '0.75rem', fontWeight: 'bold', color: '#666' }}>Zaman Aralığı</label>
            <input type="date" style={{ width: '100%', padding: '8px', borderRadius: '8px', border: '1px solid #ddd', marginTop: '4px' }} />
          </div>

        <button style={{
            width: '100%', padding: '10px', borderRadius: '8px', border: 'none',
            background: '#007bff', color: '#fff', fontWeight: 'bold', cursor: 'pointer',
            marginTop: '10px'
          }}>
            Filtrele
          </button>

          {/* --- EKSİK OLAN HABER LİSTESİ BURASI --- */}
          <div style={{ 
            marginTop: '20px', 
            maxHeight: '300px', 
            overflowY: 'auto',
            paddingRight: '5px' 
          }}>
            <h3 style={{ fontSize: '0.9rem', marginBottom: '10px', color: '#666' }}>Son Haberler ({markers.length})</h3>
            {markers.map((news) => (
              <div 
                key={news._id}
                style={{ 
                  padding: '10px', 
                  background: '#f8f9fa', 
                  borderRadius: '10px', 
                  marginBottom: '8px',
                  border: '1px solid #eee',
                  fontSize: '0.8rem'
                }}
              >
                <div style={{ fontWeight: 'bold', color: '#333' }}>{news.title}</div>
                <div style={{ color: '#888', marginTop: '4px' }}>📍 {news.district} | {news.type}</div>
              </div>
            ))}
          </div>
        </div>
      </FloatingFilterCard>

      <MapContainer markers={markers} />
    </MainLayout>
  );
}