import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { listingsApi, creditsApi } from "../api/listings";
import { useAuthStore } from "../store/auth";
import type { Listing } from "../types";

const INTERIOR_LABELS: Record<string, string> = {
  gml_3d: "GML 3D Tur",
  photos: "Fotoğraf",
  listing_data: "İlan Verisi",
};

const INTERIOR_COLORS: Record<string, string> = {
  gml_3d: "bg-green-100 text-green-800",
  photos: "bg-blue-100 text-blue-800",
  listing_data: "bg-gray-100 text-gray-700",
};

export default function DashboardPage() {
  const navigate = useNavigate();
  const { logout } = useAuthStore();

  const { data: listings = [], isLoading } = useQuery({
    queryKey: ["listings"],
    queryFn: listingsApi.list,
  });

  const { data: wallet } = useQuery({
    queryKey: ["wallet"],
    queryFn: creditsApi.getWallet,
  });

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-brand-600 rounded-lg flex items-center justify-center">
            <span className="text-white text-xs font-bold">3D</span>
          </div>
          <span className="font-bold text-gray-900">Emlak 3D Platform</span>
        </div>
        <div className="flex items-center gap-4">
          {wallet && (
            <div className="text-sm bg-brand-50 border border-brand-200 text-brand-700 px-3 py-1 rounded-full font-medium">
              {wallet.balance.toFixed(1)} Kredi
            </div>
          )}
          <button
            onClick={logout}
            className="text-sm text-gray-500 hover:text-gray-700"
          >
            Çıkış
          </button>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-xl font-bold text-gray-900">İlanlarım</h1>
          <Link
            to="/listings/new"
            className="bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
          >
            + Yeni İlan
          </Link>
        </div>

        {isLoading ? (
          <div className="text-center py-16 text-gray-400">Yükleniyor...</div>
        ) : listings.length === 0 ? (
          <div className="text-center py-16">
            <p className="text-gray-400 mb-4">Henüz ilan oluşturmadınız.</p>
            <Link
              to="/listings/new"
              className="text-brand-600 hover:underline text-sm font-medium"
            >
              İlk ilanınızı oluşturun
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {listings.map((l: Listing) => (
              <div
                key={l.id}
                onClick={() => navigate(`/listings/${l.id}`)}
                className="bg-white rounded-xl border border-gray-200 p-5 cursor-pointer hover:shadow-md transition-shadow"
              >
                <div className="flex items-start justify-between mb-3">
                  <h3 className="font-semibold text-gray-900 text-sm leading-tight line-clamp-2">
                    {l.title}
                  </h3>
                  {l.interior_source && (
                    <span className={`text-xs px-2 py-0.5 rounded-full ml-2 shrink-0 ${INTERIOR_COLORS[l.interior_source]}`}>
                      {INTERIOR_LABELS[l.interior_source]}
                    </span>
                  )}
                </div>
                <p className="text-xs text-gray-500 mb-3">
                  {[l.district, l.city].filter(Boolean).join(", ")}
                </p>
                <div className="flex items-center justify-between text-xs text-gray-400">
                  <span>{l.gross_area ? `${l.gross_area} m²` : ""}</span>
                  <span className="font-semibold text-gray-700">
                    {l.price ? `${l.price.toLocaleString("tr-TR")} ${l.currency}` : ""}
                  </span>
                </div>
                {l.geocoding_confirmed && (
                  <div className="mt-3 pt-3 border-t border-gray-100">
                    <button
                      onClick={(e) => { e.stopPropagation(); navigate(`/listings/${l.id}/video`); }}
                      className="w-full text-xs text-brand-600 hover:text-brand-700 font-medium"
                    >
                      Video Oluştur
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
