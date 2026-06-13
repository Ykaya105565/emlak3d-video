import { apiClient } from "./client";
import type { Listing } from "../types";

export const listingsApi = {
  list: () => apiClient.get<Listing[]>("/listings").then((r) => r.data),
  get: (id: string) => apiClient.get<Listing>(`/listings/${id}`).then((r) => r.data),
  create: (data: Partial<Listing>) => apiClient.post<Listing>("/listings", data).then((r) => r.data),
  confirmLocation: (id: string, lat: number, lng: number) =>
    apiClient.patch(`/listings/${id}/confirm-location`, null, { params: { lat, lng } }),
};

export const uploadsApi = {
  uploadGml: (listingId: string, file: File, kvkkConsent: boolean) => {
    const form = new FormData();
    form.append("file", file);
    form.append("kvkk_consent", String(kvkkConsent));
    return apiClient.post(`/uploads/gml/${listingId}`, form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
  uploadPhotos: (listingId: string, files: File[], kvkkConsent: boolean) => {
    const form = new FormData();
    files.forEach((f) => form.append("files", f));
    form.append("kvkk_consent", String(kvkkConsent));
    return apiClient.post(`/uploads/photos/${listingId}`, form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
};

export const geocodingApi = {
  geocode: (address: string, city?: string) =>
    apiClient.post("/geocoding", { address, city }).then((r) => r.data),
};

export const videosApi = {
  requestRender: (params: {
    listing_id: string;
    duration_seconds: number;
    resolution: string;
    orientation: string;
    is_watermarked: boolean;
  }) => apiClient.post("/videos/render", params).then((r) => r.data),
  getJob: (jobId: string) => apiClient.get(`/videos/${jobId}`).then((r) => r.data),
};

export const creditsApi = {
  getWallet: () => apiClient.get("/credits/wallet").then((r) => r.data),
  getTransactions: () => apiClient.get("/credits/transactions").then((r) => r.data),
};

export const authApi = {
  register: (data: {
    email: string;
    password: string;
    full_name: string;
    company_name: string;
    kvkk_consent: boolean;
  }) => apiClient.post("/auth/register", data).then((r) => r.data),
  login: (email: string, password: string) =>
    apiClient.post("/auth/login", { email, password }).then((r) => r.data),
};
