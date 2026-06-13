/**
 * Villa Hayali kompozisyonu — Faz 2
 * İmar zarfı analizi: parsel + yapılaşma zarfı + bilgi tablosu
 *
 * ÖNEMLI: Tüm görseller ve 3D modeller temsilîdir.
 * Ruhsat alınmadan yapı yapılamaz.
 */

import {
  AbsoluteFill,
  Audio,
  Img,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

interface Props {
  envelopeJson: string;    // compute_building_envelope() çıktısı
  frameUrl?: string;       // PIL üretilen statik kare URL'i (opsiyonel)
  audioPath: string;
  isWatermarked: boolean;
  listingData?: string;    // JSON
}

function InfoRow({ label, value, color = "#fff" }: { label: string; value: string; color?: string }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 0",
                  borderBottom: "1px solid rgba(255,255,255,0.08)" }}>
      <span style={{ color: "rgba(255,255,255,0.5)", fontSize: 16, fontFamily: "sans-serif" }}>{label}</span>
      <span style={{ color, fontSize: 18, fontFamily: "sans-serif", fontWeight: 600 }}>{value}</span>
    </div>
  );
}

export function VillaHayali({ envelopeJson, frameUrl, audioPath, isWatermarked, listingData }: Props) {
  const envelope = JSON.parse(envelopeJson || "{}");
  const data = JSON.parse(listingData || "{}");
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  // Fade-in
  const mainOpacity = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: "clamp" });
  // Panel slide-in
  const panelX = interpolate(frame, [10, 35], [80, 0], { extrapolateRight: "clamp" });

  const s = envelope.setbacks || {};

  return (
    <AbsoluteFill style={{ background: "#0d1117" }}>
      {/* Plan görüntüsü (PIL üretilmiş) */}
      {frameUrl ? (
        <Img src={frameUrl} style={{ width: "100%", height: "100%", objectFit: "cover", opacity: mainOpacity }} />
      ) : (
        /* Fallback: arka plan */
        <AbsoluteFill style={{
          background: "linear-gradient(135deg, #0d1117 0%, #161b22 50%, #1a2233 100%)",
          opacity: mainOpacity,
        }}>
          {/* Basit ızgara efekti */}
          <svg width="100%" height="100%" style={{ position: "absolute", opacity: 0.1 }}>
            <defs>
              <pattern id="grid" width="60" height="60" patternUnits="userSpaceOnUse">
                <path d="M 60 0 L 0 0 0 60" fill="none" stroke="#4b5563" strokeWidth="0.5"/>
              </pattern>
            </defs>
            <rect width="100%" height="100%" fill="url(#grid)" />
          </svg>

          {/* Parsel temsili */}
          <div style={{
            position: "absolute",
            left: "10%", top: "15%",
            width: "50%", height: "70%",
            border: "2px solid rgba(100, 200, 80, 0.6)",
            background: "rgba(34, 80, 34, 0.2)",
          }}>
            {/* Yapılaşma zarfı */}
            <div style={{
              position: "absolute",
              left: `${(s.left || 3) / ((envelope.parcel_side_m || 22)) * 100}%`,
              bottom: `${(s.rear || 3) / ((envelope.parcel_side_m || 22)) * 100}%`,
              right: `${(s.right || 3) / ((envelope.parcel_side_m || 22)) * 100}%`,
              top: `${(s.front || 5) / ((envelope.parcel_side_m || 22)) * 100}%`,
              border: "3px solid rgba(139, 92, 246, 0.9)",
              background: "rgba(139, 92, 246, 0.15)",
              display: "flex", alignItems: "center", justifyContent: "center",
            }}>
              <span style={{ color: "rgba(200, 180, 255, 0.9)", fontSize: 18, fontFamily: "sans-serif" }}>
                YAPI ZARFI
              </span>
            </div>
          </div>
        </AbsoluteFill>
      )}

      {/* Bilgi paneli (sağda) */}
      <div style={{
        position: "absolute",
        right: 0, top: 0, bottom: 0,
        width: 420,
        background: "rgba(0, 0, 0, 0.85)",
        backdropFilter: "blur(20px)",
        borderLeft: "1px solid rgba(255,255,255,0.1)",
        padding: "40px 32px",
        transform: `translateX(${panelX}px)`,
        opacity: mainOpacity,
      }}>
        <p style={{ color: "rgba(139, 92, 246, 0.9)", fontSize: 13, fontFamily: "sans-serif",
                    textTransform: "uppercase", letterSpacing: 2, margin: "0 0 8px" }}>
          Villa Hayali
        </p>
        <h2 style={{ color: "#fff", fontSize: 24, fontFamily: "sans-serif",
                     fontWeight: 700, margin: "0 0 24px", lineHeight: 1.3 }}>
          {data.title || "İmar Zarfı Analizi"}
        </h2>

        <InfoRow label="Parsel Alanı"  value={`${envelope.parcel_area_m2?.toLocaleString("tr-TR")} m²`} color="#6ee7b7" />
        <InfoRow label="TAKS"          value={String(envelope.taks)} color="#93c5fd" />
        <InfoRow label="KAKS (Emsal)"  value={String(envelope.kaks)} color="#93c5fd" />
        <InfoRow label="Maks. Taban"   value={`${envelope.max_footprint_m2} m²`} color="#86efac" />
        <InfoRow label="Maks. Toplam"  value={`${envelope.max_total_area_m2} m²`} color="#86efac" />
        <InfoRow label="Maks. Kat"     value={String(envelope.max_floors)} color="#fde68a" />
        <InfoRow label="Maks. Yük."    value={`${envelope.max_height_m} m`} color="#fde68a" />

        <div style={{ marginTop: 24, padding: 16, borderRadius: 8,
                      background: "rgba(80, 60, 0, 0.4)", border: "1px solid rgba(200, 150, 0, 0.4)" }}>
          <p style={{ color: "rgba(200, 160, 50, 0.9)", fontSize: 12, fontFamily: "sans-serif",
                      margin: 0, lineHeight: 1.6 }}>
            ★  Bu analiz bilgi amaçlıdır. Yapı ruhsatı için yetkili
            mimar/mühendis ile çalışınız. Tüm görseller temsilîdir.
          </p>
        </div>
      </div>

      {/* Header */}
      <div style={{
        position: "absolute", top: 0, left: 0, right: 420,
        height: 70, background: "rgba(0,0,0,0.7)",
        display: "flex", alignItems: "center", padding: "0 40px",
        opacity: mainOpacity,
      }}>
        <span style={{ color: "#8b5cf6", fontFamily: "sans-serif", fontSize: 20, fontWeight: 700 }}>
          VİLLA HAYALİ
        </span>
        <span style={{ color: "rgba(255,255,255,0.5)", fontFamily: "sans-serif", fontSize: 15, marginLeft: 20 }}>
          {data.city || ""}
        </span>
      </div>

      {/* Alt çizgi */}
      <div style={{ position: "absolute", bottom: 0, left: 0, right: 420, height: 4,
                    background: "linear-gradient(90deg, #8b5cf6, #a855f7)" }} />

      {/* Temsilîdir */}
      <div style={{
        position: "absolute", bottom: 12, left: 20,
        color: "rgba(255,255,255,0.35)", fontSize: 11, fontFamily: "sans-serif",
      }}>
        Temsilîdir — Ruhsat alınmadan yapı yapılamaz.
      </div>

      {isWatermarked && (
        <div style={{ position: "absolute", top: 80, right: 440,
                      background: "rgba(0,0,0,0.7)", color: "rgba(255,255,255,0.8)",
                      fontSize: 13, padding: "5px 12px", borderRadius: 6, fontFamily: "sans-serif" }}>
          ÖNIZLEME
        </div>
      )}

      {audioPath && <Audio src={audioPath} />}
    </AbsoluteFill>
  );
}
