import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { listingsApi, videosApi } from "../api/listings";
import type { VideoJob } from "../types";

const DURATIONS = [15, 30, 60, 90];
const CREDIT_LABELS: Record<string, string> = {
  gml_3d: "GML 3D Tur (+2 kredi)",
  photos: "Fotoğraf (+1 kredi)",
  listing_data: "İlan Verisi (+0 kredi)",
};

export default function VideoStudioPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [duration, setDuration] = useState(30);
  const [resolution, setResolution] = useState<"1080p" | "4k">("1080p");
  const [orientation, setOrientation] = useState<"16:9" | "9:16">("16:9");
  const [isWatermarked, setIsWatermarked] = useState(true);
  const [job, setJob] = useState<VideoJob | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const { data: listing } = useQuery({
    queryKey: ["listing", id],
    queryFn: () => listingsApi.get(id!),
    enabled: !!id,
  });

  // Tamamlanana kadar job'u poll et
  useEffect(() => {
    if (!job || job.status === "completed" || job.status === "failed") return;
    const interval = setInterval(async () => {
      const updated = await videosApi.getJob(job.id);
      setJob(updated);
    }, 3000);
    return () => clearInterval(interval);
  }, [job]);

  const creditCost = (() => {
    const dur = Math.max(1, duration / 15);
    const res = resolution === "4k" ? 1 : 0;
    const interior = listing?.interior_source === "gml_3d" ? 2 : listing?.interior_source === "photos" ? 1 : 0;
    return isWatermarked ? 0 : dur + res + interior;
  })();

  async function handleRender() {
    if (!id) return;
    setLoading(true);
    setError("");
    try {
      const j = await videosApi.requestRender({
        listing_id: id,
        duration_seconds: duration,
        resolution,
        orientation,
        is_watermarked: isWatermarked,
      });
      setJob(j);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Render başlatılamadı");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-2xl mx-auto">
        <div className="flex items-center gap-3 mb-6">
          <button onClick={() => navigate(`/listings/${id}`)} className="text-gray-400 hover:text-gray-600 text-sm">← Geri</button>
          <h1 className="text-xl font-bold text-gray-900">Video Stüdyo</h1>
        </div>

        {listing && (
          <div className="bg-white rounded-xl border border-gray-200 p-4 mb-4 text-sm">
            <p className="font-medium text-gray-800">{listing.title}</p>
            <p className="text-gray-500 text-xs mt-0.5">
              İç mekân: {listing.interior_source ? CREDIT_LABELS[listing.interior_source] : "Belirsiz"}
            </p>
          </div>
        )}

        {/* Ayarlar */}
        {!job && (
          <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-6">
            <div>
              <p className="text-sm font-semibold text-gray-700 mb-3">Video Süresi</p>
              <div className="grid grid-cols-4 gap-2">
                {DURATIONS.map((d) => (
                  <button key={d} onClick={() => setDuration(d)}
                    className={`py-2 rounded-lg text-sm font-medium border transition-colors
                      ${duration === d ? "bg-brand-600 text-white border-brand-600" : "border-gray-300 text-gray-600 hover:border-brand-400"}`}>
                    {d}sn
                  </button>
                ))}
              </div>
            </div>

            <div>
              <p className="text-sm font-semibold text-gray-700 mb-3">Çözünürlük</p>
              <div className="grid grid-cols-2 gap-2">
                {(["1080p", "4k"] as const).map((r) => (
                  <button key={r} onClick={() => setResolution(r)}
                    className={`py-2 rounded-lg text-sm font-medium border transition-colors
                      ${resolution === r ? "bg-brand-600 text-white border-brand-600" : "border-gray-300 text-gray-600 hover:border-brand-400"}`}>
                    {r === "4k" ? "4K (+1 kredi)" : "1080p"}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <p className="text-sm font-semibold text-gray-700 mb-3">Format</p>
              <div className="grid grid-cols-2 gap-2">
                {([["16:9", "Yatay (YouTube, web)"], ["9:16", "Dikey (Instagram, TikTok)"]] as const).map(([o, label]) => (
                  <button key={o} onClick={() => setOrientation(o)}
                    className={`py-2 px-3 rounded-lg text-sm font-medium border transition-colors text-left
                      ${orientation === o ? "bg-brand-600 text-white border-brand-600" : "border-gray-300 text-gray-600 hover:border-brand-400"}`}>
                    {label}
                  </button>
                ))}
              </div>
            </div>

            <div className="border-t pt-4">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <p className="text-sm font-semibold text-gray-700">Ücretsiz Önizleme</p>
                  <p className="text-xs text-gray-500">Watermark'lı, indirilebilir</p>
                </div>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="checkbox" checked={isWatermarked} onChange={e => setIsWatermarked(e.target.checked)}
                    className="h-4 w-4 text-brand-600 rounded" />
                  <span className="text-sm text-gray-600">Watermark'lı</span>
                </label>
              </div>

              <div className="bg-gray-50 rounded-lg p-3 flex items-center justify-between mb-4">
                <span className="text-sm text-gray-600">Kredi maliyeti</span>
                <span className={`font-bold text-lg ${creditCost === 0 ? "text-green-600" : "text-brand-600"}`}>
                  {creditCost === 0 ? "Ücretsiz" : `${creditCost} kredi`}
                </span>
              </div>

              {error && <p className="text-red-600 text-sm mb-3">{error}</p>}

              <button onClick={handleRender} disabled={loading}
                className="w-full bg-brand-600 hover:bg-brand-700 text-white font-medium py-3 rounded-xl transition-colors disabled:opacity-50">
                {loading ? "Başlatılıyor..." : "Video Oluştur"}
              </button>
            </div>
          </div>
        )}

        {/* Job durumu */}
        {job && (
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className={`w-3 h-3 rounded-full ${
                job.status === "completed" ? "bg-green-500" :
                job.status === "failed" ? "bg-red-500" : "bg-brand-500 animate-pulse"}`} />
              <p className="text-sm font-semibold text-gray-800">
                {job.status === "pending" ? "Sıraya alındı" :
                 job.status === "processing" ? "Oluşturuluyor..." :
                 job.status === "completed" ? "Video hazır!" : "Hata oluştu"}
              </p>
            </div>

            {(job.status === "pending" || job.status === "processing") && (
              <div className="w-full bg-gray-100 rounded-full h-2 mb-4">
                <div className="bg-brand-500 h-2 rounded-full transition-all duration-500"
                  style={{ width: `${job.progress_pct}%` }} />
              </div>
            )}

            {job.status === "completed" && job.output_url && (
              <a href={job.output_url} download
                className="block w-full text-center bg-green-600 hover:bg-green-700 text-white font-medium py-3 rounded-xl">
                MP4 İndir {job.is_watermarked ? "(Watermark'lı)" : "(Markasız)"}
              </a>
            )}

            {job.status === "failed" && (
              <button onClick={() => setJob(null)}
                className="w-full border border-gray-300 text-gray-600 py-2 rounded-xl text-sm">
                Tekrar Dene
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
