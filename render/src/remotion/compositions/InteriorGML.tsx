/**
 * Öncelik 1: CityGML'den gerçek 3D tur.
 * Kamera keyframe'leri interior_walk.js tarafından üretilir.
 * Bu kompozisyon:
 *  - Dışarıdan PNG kare sekansını (three.js render'ı) içe alır
 *  - Üstüne oda adı + alan kartları overlay olarak ekler
 *  - TTS sesini sync eder
 *  - Watermark (opsiyonel)
 *  - "Temsilîdir" ibaresi
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

interface Room {
  roomName: string;
  area_m2: number;
  floor: number;
}

interface Keyframe {
  frame: number;
  room: string;
  room_area: number;
  floor: number;
}

interface Props {
  inventoryJson: string;
  gltfPath: string;
  audioPath: string;
  isWatermarked: boolean;
  keyframesJson?: string;      // camera_keyframes.json içeriği
  framesDirUrl?: string;       // PNG kare dizinin URL prefix'i
}

function RoomCard({ name, area, floor, visible }: { name: string; area: number; floor: number; visible: boolean }) {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const opacity = spring({ fps, frame: visible ? 0 : 10, config: { damping: 12 } });
  const y = interpolate(visible ? 0 : 1, [0, 1], [0, 20]);

  return (
    <div style={{
      position: "absolute",
      bottom: 120,
      left: 60,
      opacity: visible ? opacity : 1 - opacity,
      transform: `translateY(${y}px)`,
      transition: "all 0.3s ease",
    }}>
      <div style={{
        background: "rgba(0,0,0,0.72)",
        backdropFilter: "blur(12px)",
        borderRadius: 16,
        padding: "16px 24px",
        border: "1px solid rgba(255,255,255,0.15)",
      }}>
        <p style={{ color: "#fff", fontSize: 28, fontWeight: 700, margin: 0, fontFamily: "sans-serif" }}>{name}</p>
        <p style={{ color: "rgba(255,255,255,0.7)", fontSize: 18, margin: "4px 0 0", fontFamily: "sans-serif" }}>
          {area.toFixed(1)} m² · Kat {floor}
        </p>
      </div>
    </div>
  );
}

function WatermarkBadge() {
  return (
    <div style={{
      position: "absolute",
      top: 24,
      right: 24,
      background: "rgba(0,0,0,0.6)",
      color: "rgba(255,255,255,0.8)",
      fontSize: 14,
      padding: "6px 14px",
      borderRadius: 8,
      fontFamily: "sans-serif",
      fontWeight: 600,
      letterSpacing: 1,
    }}>
      ÖNIZLEME
    </div>
  );
}

function RepresentativeNote() {
  return (
    <div style={{
      position: "absolute",
      bottom: 20,
      right: 24,
      background: "rgba(0,0,0,0.5)",
      color: "rgba(255,255,255,0.6)",
      fontSize: 11,
      padding: "4px 10px",
      borderRadius: 6,
      fontFamily: "sans-serif",
    }}>
      Kaplama ve mobilya temsilîdir. Geometri/alan resmî CityGML verisinden üretilmiştir.
    </div>
  );
}

export function InteriorGML({
  inventoryJson,
  audioPath,
  isWatermarked,
  keyframesJson,
  framesDirUrl,
}: Props) {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  const keyframes: Keyframe[] = keyframesJson
    ? JSON.parse(keyframesJson).keyframes || []
    : [];

  const currentKf = keyframes[frame] || keyframes[keyframes.length - 1];
  const prevKf = frame > 0 ? keyframes[frame - 1] || currentKf : currentKf;
  const roomChanged = currentKf?.room !== prevKf?.room;

  const frameUrl = framesDirUrl
    ? `${framesDirUrl}/frame_${String(frame).padStart(5, "0")}.png`
    : null;

  return (
    <AbsoluteFill style={{ background: "#111" }}>
      {/* Three.js render karesi */}
      {frameUrl && (
        <Img src={frameUrl} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
      )}

      {/* Fallback: GML yokken arka plan */}
      {!frameUrl && (
        <div style={{
          width: "100%", height: "100%",
          background: "linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)",
          display: "flex", alignItems: "center", justifyContent: "center",
        }}>
          <p style={{ color: "rgba(255,255,255,0.3)", fontSize: 18, fontFamily: "sans-serif" }}>
            3D İç Mekân Render — {currentKf?.room || "Yükleniyor"}
          </p>
        </div>
      )}

      {/* Oda adı kartı */}
      {currentKf && (
        <RoomCard
          name={currentKf.room}
          area={currentKf.room_area}
          floor={currentKf.floor}
          visible={!roomChanged}
        />
      )}

      {/* Alt çizgi */}
      <div style={{
        position: "absolute", bottom: 0, left: 0, right: 0, height: 4,
        background: "linear-gradient(90deg, #3b82f6, #8b5cf6)",
      }} />

      {/* Temsilîdir notu */}
      <RepresentativeNote />

      {/* Watermark */}
      {isWatermarked && <WatermarkBadge />}

      {/* Ses */}
      {audioPath && <Audio src={audioPath} />}
    </AbsoluteFill>
  );
}
