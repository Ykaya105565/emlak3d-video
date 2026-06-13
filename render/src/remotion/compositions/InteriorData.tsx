/**
 * Öncelik 3: Sadece ilan verisi → after-effects tarzı hareketli grafik.
 * Gerçek iç mekân yoktur — UYDURMA yapılmaz.
 * Sadece ilan bilgisi animasyonlu kartlarla sunulur.
 */

import {
  AbsoluteFill,
  Audio,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

interface Props {
  listingData: string;
  audioPath: string;
  isWatermarked: boolean;
}

interface DataCard {
  icon: string;
  label: string;
  value: string;
}

function AnimatedCard({ card, delay }: { card: DataCard; delay: number }) {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const localFrame = Math.max(0, frame - delay);
  const opacity = spring({ fps, frame: localFrame, config: { damping: 14 } });
  const y = interpolate(Math.min(localFrame, 20), [0, 20], [30, 0]);

  return (
    <div style={{
      background: "rgba(255,255,255,0.08)",
      border: "1px solid rgba(255,255,255,0.12)",
      borderRadius: 16,
      padding: "20px 24px",
      display: "flex",
      alignItems: "center",
      gap: 16,
      opacity,
      transform: `translateY(${y}px)`,
    }}>
      <span style={{ fontSize: 36 }}>{card.icon}</span>
      <div>
        <p style={{ color: "rgba(255,255,255,0.5)", fontSize: 13, margin: 0, fontFamily: "sans-serif", textTransform: "uppercase", letterSpacing: 0.8 }}>
          {card.label}
        </p>
        <p style={{ color: "#fff", fontSize: 22, margin: "2px 0 0", fontFamily: "sans-serif", fontWeight: 700 }}>
          {card.value}
        </p>
      </div>
    </div>
  );
}

export function InteriorData({ listingData, audioPath, isWatermarked }: Props) {
  const data = JSON.parse(listingData || "{}");
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleOpacity = spring({ fps, frame, config: { damping: 12 } });
  const titleY = interpolate(Math.min(frame, 30), [0, 30], [20, 0]);

  const cards: DataCard[] = [
    data.gross_area && { icon: "📐", label: "Brüt Alan", value: `${data.gross_area} m²` },
    data.net_area && { icon: "🏠", label: "Net Alan", value: `${data.net_area} m²` },
    data.room_count && { icon: "🚪", label: "Oda Sayısı", value: String(data.room_count) },
    data.floor != null && { icon: "🏢", label: "Kat", value: `${data.floor}. Kat` },
    data.total_floors && { icon: "🏗️", label: "Toplam Kat", value: String(data.total_floors) },
    data.price && { icon: "💰", label: "Fiyat", value: `${data.price?.toLocaleString("tr-TR")} ${data.currency || "TRY"}` },
  ].filter(Boolean) as DataCard[];

  return (
    <AbsoluteFill style={{
      background: "linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%)",
    }}>
      {/* Başlık */}
      <div style={{
        position: "absolute", top: 80, left: 80, right: 80,
        opacity: titleOpacity,
        transform: `translateY(${titleY}px)`,
      }}>
        <p style={{ color: "rgba(255,255,255,0.5)", fontSize: 14, margin: 0, fontFamily: "sans-serif", textTransform: "uppercase", letterSpacing: 2 }}>
          {data.city} {data.district ? `· ${data.district}` : ""}
        </p>
        <h1 style={{ color: "#fff", fontSize: 42, margin: "8px 0", fontFamily: "sans-serif", fontWeight: 800, lineHeight: 1.2 }}>
          {data.title || "Satılık Taşınmaz"}
        </h1>
        {data.address_text && (
          <p style={{ color: "rgba(255,255,255,0.6)", fontSize: 16, margin: 0, fontFamily: "sans-serif" }}>
            📍 {data.address_text}
          </p>
        )}
      </div>

      {/* Bilgi kartları */}
      <div style={{
        position: "absolute", bottom: 120, left: 80, right: 80,
        display: "grid",
        gridTemplateColumns: "repeat(3, 1fr)",
        gap: 16,
      }}>
        {cards.slice(0, 6).map((card, i) => (
          <AnimatedCard key={i} card={card} delay={i * 8 + 20} />
        ))}
      </div>

      {/* Alt bilgi */}
      <div style={{
        position: "absolute", bottom: 32, left: 80, right: 80,
        display: "flex", alignItems: "center", justifyContent: "space-between",
      }}>
        <p style={{ color: "rgba(255,255,255,0.4)", fontSize: 12, fontFamily: "sans-serif" }}>
          Detaylı bilgi için emlakçınızla iletişime geçin.
        </p>
      </div>

      {/* Alt çizgi */}
      <div style={{ position: "absolute", bottom: 0, left: 0, right: 0, height: 4, background: "linear-gradient(90deg, #a855f7, #ec4899)" }} />

      {isWatermarked && (
        <div style={{ position: "absolute", top: 24, right: 24, background: "rgba(255,255,255,0.1)", color: "rgba(255,255,255,0.8)", fontSize: 14, padding: "6px 14px", borderRadius: 8, fontFamily: "sans-serif", fontWeight: 600 }}>
          ÖNIZLEME
        </div>
      )}

      {audioPath && <Audio src={audioPath} />}
    </AbsoluteFill>
  );
}
