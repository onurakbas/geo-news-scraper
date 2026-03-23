/** TypeScript types mirroring the backend Pydantic models. */

export interface Coordinates {
  type: "Point";
  coordinates: [number, number]; // [lng, lat]
}

export interface NewsItem {
  _id: string;
  source: string;
  url: string;
  title: string;
  content: string;
  published_at: string; // ISO string
  type?: string;
  district?: string;
  city?: string;
  locations: string[];
  coordinates?: Coordinates;
}

export interface PaginatedNews {
  items: NewsItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface FilterOptions {
  types: string[];
  districts: string[];
}

export interface MapMarker {
  _id: string;
  title: string;
  type: string; 
  district: string;
  lat: number;
  lon: number;
  urls: string[]; 
  sources?: string[]; 
}
