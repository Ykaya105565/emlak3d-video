import { useParams, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { listingsApi } from "../api/listings";
import type { Room } from "../types";

const SOURCE_INFO: Record<string, { label: string; color: string; desc: string }> = {
  gml_3d: { label: "GML 3D Tur", color: "green", desc: "Resmî CityGML verisinden gerçek iç mekân turu" },
  photos: { label: "Fotoğraf", color: "blue", desc: "Yüklenen fotoğraflardan video" },
  listing_data: { label: "İlan Verisi", color: "gray", desc: "İlan bilgilerinden hareketli grafik" },
};

export default function ListingDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const { data: listing, isLoading } = useQuery({
    queryKey: ["listing", id],
    queryFn: () => listingsApi.get(id!),
    enabled: !!id,
  });

  if (isLoading) return <div className="min-h-screen flex items-center justify-center text-gray-400">Yükleniyor...</div>;
  if (!listing) return <div className="min-h-screen flex items-center justify-center text-red-500">İlan bulunamadı</div>;

  const src = listing.interior_source ? SOURCE_INFO[listing.interior_source] : null;
  const rooms = listing.gml_room_inventory?.rooms || [];

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center gap-3 mb-6">
          <button onClick={() => navigate("/")} className="text-gray-400 hover:text-gray-600 text-sm">← Geri</button>
          <h1 className="text-xl font-bold text-gray-900 flex-1">{listing.title}</h1>
          <button
            onClick={() => navigate(`/listings/${id}/video`)}
            disabled={!listing.geocoding_confirmed}
            className="bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium px-4 py-2 rounded-lg disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Video Oluştur
          </button>
        </div>

        {!listing.geocoding_confirmed && (
          <div className="bg-amber-50 border border-amber-200 text-amber-800 rounded-xl p-4 mb-4 text-sm">
            Konum haritada onaylanmadan video üretilemez.
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          {/* İç Mekân Kaynağı */}
          {src && (
            <div className={`bg-${src.color}-50 border border-${src.color}-200 rounded-xl p-4`}>
              <p className={`text-xs font-semibold text-${src.color}-700 mb-1`}>İç Mekân Kaynağı</p>
              <p className={`text-sm font-bold text-${src.color}-900`}>{src.label}</p>
              <p className={`text-xs text-${src.color}-600 mt-1`}>{src.desc}</p>
            </div>
          )}

          {/* Temel Bilgiler */}
          <div className="bg-white border border-gray-200 rounded-xl p-4">
            <p className="text-xs text-gray-500 mb-2">Taşınmaz Bilgileri</p>
            <div className="space-y-1 text-sm">
              <div className="flex justify-between"><span className="text-gray-500">Tip</span><span className="font-medium">{listing.listing_type}</span></div>
              {listing.gross_area && <div className="flex justify-between"><span className="text-gray-500">Brüt Alan</span><span className="font-medium">{listing.gross_area} m²</span></div>}
              {listing.net_area && <div className="flex justify-between"><span className="text-gray-500">Net Alan</span><span className="font-medium">{listing.net_area} m²</span></div>}
              {listing.room_count && <div className="flex justify-between"><span className="text-gray-500">Oda</span><span className="font-medium">{listing.room_count}</span></div>}
            </div>
          </div>

          {/* Konum */}
          <div className="bg-white border border-gray-200 rounded-xl p-4">
            <p className="text-xs text-gray-500 mb-2">Konum</p>
            <p className="text-sm font-medium">{[listing.district, listing.city].filter(Boolean).join(", ")}</p>
            {listing.lat && <p className="text-xs text-gray-400 mt-1">{listing.lat?.toFixed(5)}, {listing.lng?.toFixed(5)}</p>}
            <p className={`text-xs mt-1 ${listing.geocoding_confirmed ? "text-green-600" : "text-amber-600"}`}>
              {listing.geocoding_confirmed ? "Konum onaylandı" : "Konum onay bekliyor"}
            </p>
          </div>
        </div>

        {/* GML Oda Envanteri */}
        {rooms.length > 0 && (
          <div className="bg-white border border-gray-200 rounded-xl p-6">
            <div className="flex items-center gap-2 mb-4">
              <h2 className="text-sm font-bold text-gray-900">GML Oda Envanteri</h2>
              <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">
                Resmî veri · {listing.gml_room_inventory?.crs}
              </span>
              <span className="text-xs text-gray-400 ml-auto">{rooms.length} oda</span>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
              {rooms.map((room: Room) => (
                <div key={room.id} className="bg-gray-50 rounded-lg p-3">
                  <p className="text-xs font-semibold text-gray-800">{room.name}</p>
                  <p className="text-xs text-gray-500">{room.area_m2.toFixed(1)} m²</p>
                  <p className="text-xs text-gray-400">Kat {room.floor}</p>
                </div>
              ))}
            </div>
            <p className="text-xs text-gray-400 mt-3 italic">
              * Geometri gerçek CityGML LoD4 verisinden; kaplama ve mobilya temsilîdir.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
