/**
 * Dış mekân sahnesi: Cesium PNG kareleri + overlay.
 * Önce dış uçuş, ardından iç mekâna geçiş efekti.
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
  exteriorFramesDir: string;
  lat: number;
  lng: number;
  audioPath: string;
  isWatermarked: boolean;
  addressText?: string;
  cityText?: string;
  hasCoverage?: boolean;   // false = 2D fallback
}

function LocationCard({ address, city, visible }: { address?: string; city?: string; visible: boolean }) {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const opacity = spring({ fps, frame: visible ? 0 : 8, config: { damping: 14 } });

  return (
    <div style={{
      position: "absolute",
      top: 40,
      left: 60,
      opacity: visible ? opacity : 0,
    }}>
      <div style={{
        background: "rgba(0,0,0,0.65)",
        backdropFilter: "blur(8px)",
        borderRadius: 12,
        padding: "12px 20px",
        border: "1px solid rgba(255,255,255,0.12)",
      }}>
        <p style={{ color: "rgba(255,255,255,0.6)", fontSize: 13, margin: 0, fontFamily: "sans-serif", textTransform: "uppercase", letterSpacing: 1 }}>
          {city}
        </p>
        <p style={{ color: "#fff", fontSize: 20, margin: "4px 0 0", fontFamily: "sans-serif", fontWeight: 600 }}>
          {address}
        </p>
      </div>
    </div>
  );
}

function FallbackBadge() {
  return (
    <div style={{
      position: "absolute",
      top: 24,
      left: "50%",
      transform: "translateX(-50%)",
      background: "rgba(245,158,11,0.85)",
      color: "#fff",
      fontSize: 12,
      padding: "4px 12px",
      borderRadius: 6,
      fontFamily: "sans-serif",
      fontWeight: 600,
    }}>
      Bu konumda 3D kapsama bulunmuyor — 2D uydu görüntüsü
    </div>
  );
}

export function ExteriorScene({
  exteriorFramesDir,
  lat,
  lng,
  audioPath,
  isWatermarked,
  addressText,
  cityText,
  hasCoverage = true,
}: Props) {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  const frameUrl = exteriorFramesDir
    ? `${exteriorFramesDir}/frame_${String(frame).padStart(5, "0")}.png`
    : null;

  const progress = frame / durationInFrames;
  const showAddress = progress > 0.05 && progress < 0.6;

  return (
    <AbsoluteFill style={{ background: "#0a0a0a" }}>
      {frameUrl ? (
        <Img src={frameUrl} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
      ) : (
        // Fallback görsel: basit harita placeholder
        <div style={{
          width: "100%", height: "100%",
          background: "linear-gradient(180deg, #1a3a5c 0%, #2d6a9f 50%, #1a3a5c 100%)",
          display: "flex", alignItems: "center", justifyContent: "center", flexDirection: "column", gap: 16,
        }}>
          <div style={{
            width: 80, height: 80, borderRadius: "50%",
            background: "rgba(59,130,246,0.3)",
            border: "2px solid rgba(59,130,246,0.6)",
            display: "flex", alignItems: "center", justifyContent: "center",
          }}>
            <span style={{ fontSize: 32 }}>📍</span>
          </div>
          <p style={{ color: "rgba(255,255,255,0.7)", fontFamily: "sans-serif", fontSize: 16, textAlign: "center", maxWidth: 400 }}>
            {lat.toFixed(5)}, {lng.toFixed(5)}
            <br/><small style={{ opacity: 0.6 }}>Harita verisi yükleniyor...</small>
          </p>
        </div>
      )}

      {/* Konum kartı */}
      <LocationCard address={addressText} city={cityText} visible={showAddress} />

      {/* 2D fallback uyarısı */}
      {!hasCoverage && <FallbackBadge />}

      {/* Alt çizgi */}
      <div style={{
        position: "absolute", bottom: 0, left: 0, right: 0, height: 4,
        background: "linear-gradient(90deg, #10b981, #3b82f6)",
      }} />

      {/* Watermark */}
      {isWatermarked && (
        <div style={{
          position: "absolute", top: 24, right: 24,
          background: "rgba(0,0,0,0.6)", color: "rgba(255,255,255,0.8)",
          fontSize: 14, padding: "6px 14px", borderRadius: 8, fontFamily: "sans-serif", fontWeight: 600,
        }}>
          ÖNIZLEME
        </div>
      )}

      {audioPath && <Audio src={audioPath} />}
    </AbsoluteFill>
  );
}
