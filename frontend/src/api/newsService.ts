import apiClient from "./client";
import { MapMarker } from "../types/news";

export const newsService = {

  getMarkers: async () => {
    const { data } = await apiClient.get<{ markers: MapMarker[]; total: number }>(
      "/news/map/markers"
    );
    return data;
  },

  getNews: async (params: any) => {
    const { data } = await apiClient.get("/news", { params });
    return data;
  },

  getFilters: async () => {
    const { data } = await apiClient.get("/news/filters");
    return data;
  },

  /** Trigger a full scrape run in the backend background. */
  triggerScrape: async () => {
    const { data } = await apiClient.post<{ status: string; message: string }>(
      "/scrape/trigger"
    );
    return data;
  },

  /** Poll the current scrape status. */
  getScrapeStatus: async () => {
    const { data } = await apiClient.get<{
      status: "idle" | "running";
      last_run: string | null;
      last_error: string | null;
    }>("/scrape/status");
    return data;
  },
};