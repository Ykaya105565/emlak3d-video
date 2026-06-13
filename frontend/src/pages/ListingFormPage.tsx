import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { listingsApi, uploadsApi, geocodingApi } from "../api/listings";
import type { ListingType } from "../types";

export default function ListingFormPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState<"form" | "location" | "upload">("form");
  const [listingId, setListingId] = useState<string | null>(null);
  const [geocodeResult, setGeocodeResult] = useState<any>(null);
  const [gmlFile, setGmlFile] = useState<File | null>(null);
  const [photos, setPhotos] = useState<File[]>([]);
  const [kvkkGml, setKvkkGml] = useState(false);
  const [kvkkPhoto, setKvkkPhoto] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [form, setForm] = useState({
    title: "",
    listing_type: "apartment" as ListingType,
    price: "",
    currency: "TRY",
    address_text: "",
    city: "",
    district: "",
    gross_area: "",
    net_area: "",
    room_count: "",
    floor: "",
    total_floors: "",
    description: "",
  });

  async function handleFormSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      // Önce geocode
      const geo = await geocodingApi.geocode(form.address_text, form.city);
      setGeocodeResult(geo);

      // İlan oluştur
      const listing = await listingsApi.create({
        ...form,
        price: form.price ? parseFloat(form.price) : undefined,
        gross_area: form.gross_area ? parseFloat(form.gross_area) : undefined,
        net_area: form.net_area ? parseFloat(form.net_area) : undefined,
        room_count: form.room_count ? parseInt(form.room_count) : undefined,
        floor: form.floor ? parseInt(form.floor) : undefined,
        total_floors: form.total_floors ? parseInt(form.total_floors) : undefined,
        lat: geo.lat,
        lng: geo.lng,
        geocoding_provider: geo.provider,
      });
      setListingId(listing.id);
      setStep("location");
    } catch (err: any) {
      setError(err.response?.data?.detail || "Hata oluştu");
    } finally {
      setLoading(false);
    }
  }

  async function handleConfirmLocation() {
    if (!listingId || !geocodeResult) return;
    await listingsApi.confirmLocation(listingId, geocodeResult.lat, geocodeResult.lng);
    setStep("upload");
  }

  async function handleUploadSubmit() {
    if (!listingId) return;
    setLoading(true);
    try {
      if (gmlFile && kvkkGml) {
        await uploadsApi.uploadGml(listingId, gmlFile, true);
      }
      if (photos.length > 0 && kvkkPhoto) {
        await uploadsApi.uploadPhotos(listingId, photos, true);
      }
      navigate(`/listings/${listingId}`);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Yükleme hatası");
    } finally {
      setLoading(false);
    }
  }

  if (step === "location") {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-lg w-full max-w-lg p-8">
          <h2 className="text-lg font-bold mb-2">Konumu Doğrulayın</h2>
          <p className="text-sm text-gray-500 mb-6">
            Bulunan konum: <strong>{geocodeResult?.formatted_address}</strong>
            <br />
            Kaynak: {geocodeResult?.provider} ({(geocodeResult?.confidence * 100).toFixed(0)}% güven)
          </p>
          <div className="bg-gray-100 rounded-lg h-48 flex items-center justify-center text-gray-400 text-sm mb-6">
            [Harita — {geocodeResult?.lat?.toFixed(6)}, {geocodeResult?.lng?.toFixed(6)}]
            <br />
            <small>Geliştirme ortamında harita API anahtarı gereklidir</small>
          </div>
          <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg p-3 mb-4">
            Bu konumun doğru olduğunu onaylıyorsunuz. Yanlış konum yanlış video üretir.
          </p>
          <div className="flex gap-3">
            <button
              onClick={() => setStep("form")}
              className="flex-1 border border-gray-300 text-gray-700 py-2 rounded-lg text-sm"
            >
              Adresi Düzelt
            </button>
            <button
              onClick={handleConfirmLocation}
              className="flex-1 bg-brand-600 text-white py-2 rounded-lg text-sm font-medium"
            >
              Konumu Onayla
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (step === "upload") {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-lg w-full max-w-lg p-8">
          <h2 className="text-lg font-bold mb-2">Dosya Yükle (Opsiyonel)</h2>
          <p className="text-sm text-gray-500 mb-6">
            En iyi video için CityGML dosyası yükleyin. Yoksa fotoğraf, yoksa ilan verisi kullanılır.
          </p>

          <div className="mb-6 p-4 border-2 border-dashed border-gray-300 rounded-xl">
            <p className="text-sm font-medium text-gray-700 mb-2">CityGML (.gml) — Öncelik 1</p>
            <input
              type="file"
              accept=".gml,.xml"
              onChange={(e) => setGmlFile(e.target.files?.[0] || null)}
              className="text-xs text-gray-500 mb-3 block"
            />
            {gmlFile && (
              <div className="flex items-start gap-2 mt-2">
                <input type="checkbox" id="kvkk-gml" checked={kvkkGml} onChange={(e) => setKvkkGml(e.target.checked)} className="mt-0.5" />
                <label htmlFor="kvkk-gml" className="text-xs text-gray-600">
                  Bu GML dosyasının KVKK kapsamında işlenmesine onay veriyorum. Dosya
                  yalnızca bu ilan videosunun üretimi için kullanılacaktır.
                </label>
              </div>
            )}
          </div>

          <div className="mb-6 p-4 border-2 border-dashed border-gray-300 rounded-xl">
            <p className="text-sm font-medium text-gray-700 mb-2">Fotoğraflar — Öncelik 2</p>
            <input
              type="file"
              accept="image/*"
              multiple
              onChange={(e) => setPhotos(Array.from(e.target.files || []))}
              className="text-xs text-gray-500 mb-3 block"
            />
            {photos.length > 0 && (
              <div className="flex items-start gap-2 mt-2">
                <input type="checkbox" id="kvkk-photo" checked={kvkkPhoto} onChange={(e) => setKvkkPhoto(e.target.checked)} className="mt-0.5" />
                <label htmlFor="kvkk-photo" className="text-xs text-gray-600">
                  Fotoğrafların KVKK kapsamında işlenmesine onay veriyorum.
                </label>
              </div>
            )}
          </div>

          {error && <p className="text-red-600 text-sm mb-4">{error}</p>}

          <div className="flex gap-3">
            <button
              onClick={() => navigate(`/listings/${listingId}`)}
              className="flex-1 border border-gray-300 text-gray-700 py-2 rounded-lg text-sm"
            >
              Şimdi Değil
            </button>
            <button
              onClick={handleUploadSubmit}
              disabled={loading}
              className="flex-1 bg-brand-600 text-white py-2 rounded-lg text-sm font-medium disabled:opacity-50"
            >
              {loading ? "Yükleniyor..." : "Yükle ve Devam Et"}
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-2xl mx-auto">
        <div className="flex items-center gap-3 mb-6">
          <button onClick={() => navigate("/")} className="text-gray-400 hover:text-gray-600 text-sm">← Geri</button>
          <h1 className="text-xl font-bold text-gray-900">Yeni İlan</h1>
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
          {error && <div className="bg-red-50 text-red-700 rounded-lg p-3 text-sm mb-4">{error}</div>}

          <form onSubmit={handleFormSubmit} className="space-y-5">
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">İlan Başlığı *</label>
                <input required value={form.title} onChange={e => setForm(f => ({...f, title: e.target.value}))}
                  className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-brand-500 focus:outline-none" />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Taşınmaz Tipi *</label>
                <select value={form.listing_type} onChange={e => setForm(f => ({...f, listing_type: e.target.value as ListingType}))}
                  className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-brand-500 focus:outline-none">
                  <option value="apartment">Daire</option>
                  <option value="house">Müstakil Ev</option>
                  <option value="land">Arsa</option>
                  <option value="commercial">İşyeri</option>
                  <option value="office">Ofis</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Fiyat</label>
                <div className="flex gap-2">
                  <input type="number" value={form.price} onChange={e => setForm(f => ({...f, price: e.target.value}))}
                    placeholder="0" className="flex-1 border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-brand-500 focus:outline-none" />
                  <select value={form.currency} onChange={e => setForm(f => ({...f, currency: e.target.value}))}
                    className="border rounded-lg px-2 py-2 text-sm focus:outline-none">
                    <option>TRY</option><option>USD</option><option>EUR</option>
                  </select>
                </div>
              </div>

              <div className="col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">Adres *</label>
                <input required value={form.address_text} onChange={e => setForm(f => ({...f, address_text: e.target.value}))}
                  placeholder="Mahalle, cadde, sokak, no..." className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-brand-500 focus:outline-none" />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">İl *</label>
                <input required value={form.city} onChange={e => setForm(f => ({...f, city: e.target.value}))}
                  className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-brand-500 focus:outline-none" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">İlçe</label>
                <input value={form.district} onChange={e => setForm(f => ({...f, district: e.target.value}))}
                  className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-brand-500 focus:outline-none" />
              </div>

              {[
                {key: "gross_area", label: "Brüt Alan (m²)"},
                {key: "net_area", label: "Net Alan (m²)"},
                {key: "room_count", label: "Oda Sayısı"},
                {key: "floor", label: "Bulunduğu Kat"},
                {key: "total_floors", label: "Toplam Kat"},
              ].map(({key, label}) => (
                <div key={key}>
                  <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
                  <input type="number" value={(form as any)[key]} onChange={e => setForm(f => ({...f, [key]: e.target.value}))}
                    className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-brand-500 focus:outline-none" />
                </div>
              ))}

              <div className="col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">Açıklama</label>
                <textarea value={form.description} onChange={e => setForm(f => ({...f, description: e.target.value}))}
                  rows={3} className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-brand-500 focus:outline-none" />
              </div>
            </div>

            <button type="submit" disabled={loading}
              className="w-full bg-brand-600 hover:bg-brand-700 text-white font-medium py-2.5 rounded-lg transition-colors disabled:opacity-50">
              {loading ? "İşleniyor..." : "Devam Et — Konumu Doğrula"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
