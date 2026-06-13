export type ListingType = "apartment" | "house" | "land" | "commercial" | "office";
export type InteriorSourceType = "gml_3d" | "photos" | "listing_data";
export type VideoResolution = "1080p" | "4k";
export type VideoOrientation = "16:9" | "9:16";
export type VideoJobStatus = "pending" | "processing" | "completed" | "failed";

export interface Listing {
  id: string;
  title: string;
  listing_type: ListingType;
  price?: number;
  currency: string;
  city?: string;
  district?: string;
  address_text?: string;
  lat?: number;
  lng?: number;
  geocoding_confirmed: boolean;
  gross_area?: number;
  net_area?: number;
  room_count?: number;
  floor?: number;
  total_floors?: number;
  interior_source?: InteriorSourceType;
  has_3d_coverage?: boolean;
  gml_room_inventory?: RoomInventory;
}

export interface RoomInventory {
  rooms: Room[];
  independent_sections: IndependentSection[];
  crs: string;
  source_file: string;
}

export interface Room {
  id: string;
  name: string;
  usage: string;
  floor: number;
  area_m2: number;
  centroid_wgs84: [number, number, number];
  independent_section_id?: string;
}

export interface IndependentSection {
  id: string;
  rooms: string[];
  total_area_m2: number;
}

export interface VideoJob {
  id: string;
  status: VideoJobStatus;
  progress_pct: number;
  credit_cost: number;
  is_watermarked: boolean;
  output_url?: string;
}

export interface CreditWallet {
  balance: number;
  tenant_id: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}
