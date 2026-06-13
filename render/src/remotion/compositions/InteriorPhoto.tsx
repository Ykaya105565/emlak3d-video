/**
 * Öncelik 2: Fotoğraflardan Ken Burns / 2.5D parallax efektli video.
 */

import {
  AbsoluteFill,
  Audio,
  Img,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

interface Props {
  photoUrls: string[];
  listingData: string;
  audioPath: string;
  isWatermarked: boolean;
}

function KenBurnsPhoto({ src, startFrame, endFrame, index }: {
  src: string;
  startFrame: number;
  endFrame: number;
  index: number;
}) {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  if (frame < startFrame || frame > endFrame) return null;

  const localProgress = (frame - startFrame) / (endFrame - startFrame);

  // Her fotoğrafa farklı Ken Burns yönü
  const directions = [
    { scaleFrom: 1.05, scaleTo: 1.15, xFrom: 0, xTo: -2, yFrom: 0, yTo: -1 },
    { scaleFrom: 1.10, scaleTo: 1.0,  xFrom: -2, xTo: 0, yFrom: -1, yTo: 0 },
    { scaleFrom: 1.0,  scaleTo: 1.12, xFrom: 1, xTo: -1, yFrom: 0, yTo: -2 },
  ];
  const dir = directions[index % directions.length];

  const scale = interpolate(localProgress, [0, 1], [dir.scaleFrom, dir.scaleTo]);
  const tx = interpolate(localProgress, [0, 1], [dir.xFrom, dir.xTo]);
  const ty = interpolate(localProgress, [0, 1], [dir.yFrom, dir.yTo]);
  const opacity = interpolate(localProgress, [0, 0.1, 0.85, 1], [0, 1, 1, 0]);

  return (
    <div style={{ position: "absolute", inset: 0, opacity }}>
      <Img
        src={src}
        style={{
          width: "100%", height: "100%", objectFit: "cover",
          transform: `scale(${scale}) translate(${tx}%, ${ty}%)`,
          transformOrigin: "center center",
        }}
      />
    </div>
  );
}

export function InteriorPhoto({ photoUrls, listingData, audioPath, isWatermarked }: Props) {
  const { durationInFrames } = useVideoConfig();
  const framesPerPhoto = Math.ceil(durationInFrames / (photoUrls.length || 1));
  const data = JSON.parse(listingData || "{}");

  return (
    <AbsoluteFill style={{ background: "#111" }}>
      {photoUrls.map((url, i) => (
        <KenBurnsPhoto
          key={i}
          src={url}
          startFrame={i * framesPerPhoto}
          endFrame={(i + 1) * framesPerPhoto}
          index={i}
        />
      ))}

      {/* Bilgi kartı */}
      {data.title && (
        <div style={{
          position: "absolute", bottom: 80, left: 60,
          background: "rgba(0,0,0,0.7)", backdropFilter: "blur(12px)",
          borderRadius: 14, padding: "14px 22px",
          border: "1px solid rgba(255,255,255,0.12)",
        }}>
          <p style={{ color: "#fff", fontSize: 22, fontWeight: 700, margin: 0, fontFamily: "sans-serif" }}>
            {data.title}
          </p>
          {data.gross_area && (
            <p style={{ color: "rgba(255,255,255,0.7)", fontSize: 16, margin: "4px 0 0", fontFamily: "sans-serif" }}>
              {data.gross_area} m² · {data.room_count} oda
            </p>
          )}
        </div>
      )}

      <div style={{ position: "absolute", bottom: 0, left: 0, right: 0, height: 4, background: "linear-gradient(90deg, #f59e0b, #ef4444)" }} />

      {isWatermarked && (
        <div style={{ position: "absolute", top: 24, right: 24, background: "rgba(0,0,0,0.6)", color: "rgba(255,255,255,0.8)", fontSize: 14, padding: "6px 14px", borderRadius: 8, fontFamily: "sans-serif", fontWeight: 600 }}>
          ÖNIZLEME
        </div>
      )}

      {audioPath && <Audio src={audioPath} />}
    </AbsoluteFill>
  );
}
