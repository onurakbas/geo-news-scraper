import apiClient from "./client";
import { MapMarker } from "../types/news";

// "export const" ile isimlendirilmiş export yapıyoruz
export const newsService = {
  
  // newsService.ts dosyasını aç ve getMarkers kısmını şu şekilde güncelle:
  getMarkers: async () => {
    // URL'in sonuna ?limit=100 ekleyerek Onur'un backend'inden daha fazla veri istiyoruz
    const { data } = await apiClient.get<{ markers: MapMarker[], total: number }>(
      "/news/map/markers?limit=100"
    );
    return data;
  },

  // Diğer fonksiyonlar şimdilik dursun, hata vermezler
  getNews: async (params: any) => {
    const { data } = await apiClient.get("/news", { params });
    return data;
  },

  getFilters: async () => {
    const { data } = await apiClient.get("/filters");
    return data;
  }
};