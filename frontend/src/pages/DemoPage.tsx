import { useState, useCallback, useRef } from "react";
import "./demo.css";

const DEMO_API = "http://localhost:8080";

type Stage =
  | "idle"
  | "hazırlanıyor"
  | "render ediliyor"
  | "ses oluşturuluyor"
  | "mp4 hazırlanıyor"
  | "tamamlandı"
  | "hata";

interface JobStatus {
  status: string;
  stage: string;
  pct: number;
  detail: string;
  has_mp4: boolean;
  error: string | null;
  room_count: number | null;
  crs: string | null;
  epsg: number | null;
  file_size_mb: number | null;
  gml_name: string | null;
}

const STAGE_ICONS: Record<string, string> = {
  "hazırlanıyor": "⚙️",
  "render ediliyor": "🎬",
  "ses oluşturuluyor": "🔊",
  "mp4 hazırlanıyor": "📹",
  "tamamlandı": "✅",
  "hata": "❌",
};

const STAGE_ORDER: Stage[] = [
  "hazırlanıyor",
  "render ediliyor",
  "ses oluşturuluyor",
  "mp4 hazırlanıyor",
  "tamamlandı",
];

const ROOM_TYPES = ["Stüdyo", "1+1", "2+1", "3+1", "3+2", "4+1", "4+2", "5+2"];
const FACADE_OPTIONS = [
  "Kuzey", "Güney", "Doğu", "Batı",
  "Kuzey-Doğu", "Kuzey-Batı", "Güney-Doğu", "Güney-Batı",
];

export default function DemoPage() {
  /* ── Form fields ── */
  const [title, setTitle] = useState("");
  const [roomType, setRoomType] = useState("3+1");
  const [grossArea, setGrossArea] = useState("120");
  const [netArea, setNetArea] = useState("100");
  const [currentFloor, setCurrentFloor] = useState("3");
  const [totalFloors, setTotalFloors] = useState("8");
  const [bathrooms, setBathrooms] = useState("1");
  const [hasBalcony, setHasBalcony] = useState("Var");
  const [facade, setFacade] = useState("Güney");
  const [buildingAge, setBuildingAge] = useState("0");
  const [duration, setDuration] = useState("30");
  const [tts, setTts] = useState("gtts");

  /* ── Job state ── */
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);
  const [currentStage, setCurrentStage] = useState<Stage>("idle");
  const [isStarting, setIsStarting] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const pollStatus = useCallback(
    async (id: string) => {
      try {
        const res = await fetch(`${DEMO_API}/demo/status/${id}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data: JobStatus = await res.json();
        setJobStatus(data);

        const s = data.stage as Stage;
        setCurrentStage(s === "tamamlandı" && data.status === "done" ? "tamamlandı" : s);

        if (data.status === "done" || data.status === "error") {
          stopPolling();
          if (data.status === "error") {
            setCurrentStage("hata");
          }
        }
      } catch (err) {
        console.error("Polling hatası:", err);
      }
    },
    [stopPolling]
  );

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!title.trim()) return;
      setIsStarting(true);
      setServerError(null);
      setJobStatus(null);
      setCurrentStage("hazırlanıyor");
      stopPolling();

      const form = new FormData();
      form.append("title", title.trim());
      form.append("room_type", roomType);
      form.append("gross_area", grossArea);
      form.append("net_area", netArea);
      form.append("current_floor", currentFloor);
      form.append("total_floors", totalFloors);
      form.append("bathrooms", bathrooms);
      form.append("has_balcony", hasBalcony === "Var" ? "true" : "false");
      form.append("facade", facade);
      form.append("building_age", buildingAge);
      form.append("duration", duration);
      form.append("tts", tts);

      try {
        const res = await fetch(`${DEMO_API}/demo/render-from-inputs`, {
          method: "POST",
          body: form,
        });
        if (!res.ok) {
          const txt = await res.text();
          throw new Error(txt || `HTTP ${res.status}`);
        }
        const { job_id } = await res.json();
        setJobId(job_id);
        // Hemen bir kere çek, sonra her 1.5 sn
        await pollStatus(job_id);
        pollRef.current = setInterval(() => pollStatus(job_id), 1500);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : String(err);
        setServerError(msg);
        setCurrentStage("hata");
      } finally {
        setIsStarting(false);
      }
    },
    [title, roomType, grossArea, netArea, currentFloor, totalFloors, bathrooms, hasBalcony, facade, buildingAge, duration, tts, stopPolling, pollStatus]
  );

  const handleReset = useCallback(() => {
    stopPolling();
    setTitle("");
    setJobId(null);
    setJobStatus(null);
    setCurrentStage("idle");
    setServerError(null);
  }, [stopPolling]);

  const isRunning =
    currentStage !== "idle" &&
    currentStage !== "tamamlandı" &&
    currentStage !== "hata";

  const isDone = currentStage === "tamamlandı" && jobStatus?.has_mp4;

  const isFormValid = title.trim().length > 0;

  return (
    <div className="demo-root">
      {/* ── Header ── */}
      <header className="demo-header">
        <div className="demo-logo">
          <span className="demo-logo-badge">3D</span>
          <span className="demo-logo-text">Emlak Demo</span>
        </div>
        <span className="demo-header-sub">Faz 0 · İlan → MP4</span>
      </header>

      <main className="demo-main">
        {/* ── Hero ── */}
        <div className="demo-hero">
          <h1 className="demo-hero-title">
            🏗️ 3D Emlak Video
          </h1>
          <p className="demo-hero-sub">
            Emlak bilgilerini girin, dakikalar içinde 3D tur videosu oluşturun.
          </p>
        </div>

        <div className="demo-layout">
          {/* ── Sol: Form ── */}
          <form className="demo-card demo-form" onSubmit={handleSubmit}>
            {/* İlan Bilgileri */}
            <div className="demo-section-title">İlan Bilgileri</div>
            <label className="demo-label demo-label-full">
              İlan Başlığı
              <input
                className="demo-input"
                type="text"
                placeholder="Deniz Manzaralı 3+1 Daire"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                required
              />
            </label>

            <div className="demo-grid-2" style={{ marginTop: "0.75rem" }}>
              <label className="demo-label">
                Oda Tipi
                <select
                  className="demo-input demo-select"
                  value={roomType}
                  onChange={(e) => setRoomType(e.target.value)}
                >
                  {ROOM_TYPES.map((r) => (
                    <option key={r} value={r}>{r}</option>
                  ))}
                </select>
              </label>
              <label className="demo-label">
                Cephe
                <select
                  className="demo-input demo-select"
                  value={facade}
                  onChange={(e) => setFacade(e.target.value)}
                >
                  {FACADE_OPTIONS.map((f) => (
                    <option key={f} value={f}>{f}</option>
                  ))}
                </select>
              </label>
            </div>

            <div className="demo-grid-2" style={{ marginTop: "0.75rem" }}>
              <label className="demo-label">
                Brüt Alan (m²)
                <input
                  className="demo-input"
                  type="number"
                  min="10" max="1000" step="1"
                  value={grossArea}
                  onChange={(e) => setGrossArea(e.target.value)}
                />
              </label>
              <label className="demo-label">
                Net Alan (m²)
                <input
                  className="demo-input"
                  type="number"
                  min="10" max="1000" step="1"
                  value={netArea}
                  onChange={(e) => setNetArea(e.target.value)}
                />
              </label>
            </div>

            {/* Bina Detayları */}
            <div className="demo-section-title" style={{ marginTop: "1.5rem" }}>Bina Detayları</div>
            <div className="demo-grid-3">
              <label className="demo-label">
                Bulunduğu Kat
                <input
                  className="demo-input"
                  type="number"
                  min="0" max="100" step="1"
                  value={currentFloor}
                  onChange={(e) => setCurrentFloor(e.target.value)}
                />
              </label>
              <label className="demo-label">
                Toplam Kat
                <input
                  className="demo-input"
                  type="number"
                  min="1" max="100" step="1"
                  value={totalFloors}
                  onChange={(e) => setTotalFloors(e.target.value)}
                />
              </label>
              <label className="demo-label">
                Banyo Sayısı
                <input
                  className="demo-input"
                  type="number"
                  min="1" max="10" step="1"
                  value={bathrooms}
                  onChange={(e) => setBathrooms(e.target.value)}
                />
              </label>
            </div>

            <div className="demo-grid-3" style={{ marginTop: "0.75rem" }}>
              <label className="demo-label">
                Balkon
                <select
                  className="demo-input demo-select"
                  value={hasBalcony}
                  onChange={(e) => setHasBalcony(e.target.value)}
                >
                  <option value="Var">Var</option>
                  <option value="Yok">Yok</option>
                </select>
              </label>
              <label className="demo-label">
                Bina Yaşı
                <input
                  className="demo-input"
                  type="number"
                  min="0" max="100" step="1"
                  value={buildingAge}
                  onChange={(e) => setBuildingAge(e.target.value)}
                />
              </label>
              {/* spacer for grid alignment */}
              <div />
            </div>

            {/* Video Ayarları */}
            <div className="demo-section-title" style={{ marginTop: "1.5rem" }}>Video Ayarları</div>
            <div className="demo-grid-2">
              <label className="demo-label">
                Video Süresi (sn)
                <input
                  className="demo-input"
                  type="number"
                  min="10" max="120" step="5"
                  value={duration}
                  onChange={(e) => setDuration(e.target.value)}
                />
                <span className="demo-input-hint">10–120 saniye</span>
              </label>
              <label className="demo-label">
                TTS Sesi
                <select
                  className="demo-input demo-select"
                  value={tts}
                  onChange={(e) => setTts(e.target.value)}
                >
                  <option value="gtts">gTTS (Google · Türkçe)</option>
                  <option value="pyttsx3">pyttsx3 (Yerel)</option>
                  <option value="silent">Sessiz</option>
                </select>
              </label>
            </div>

            {/* Submit */}
            <button
              type="submit"
              className="demo-btn-primary"
              disabled={!isFormValid || isRunning || isStarting}
            >
              {isStarting ? (
                <><span className="demo-spinner" /> Başlatılıyor…</>
              ) : isRunning ? (
                <><span className="demo-spinner" /> Render devam ediyor…</>
              ) : (
                "🚀 3D Video Oluştur"
              )}
            </button>

            {isDone && (
              <button type="button" className="demo-btn-secondary" onClick={handleReset}>
                ↩ Yeni Render
              </button>
            )}
          </form>

          {/* ── Sağ: Durum + Sonuç ── */}
          <div className="demo-right-col">
            {/* Stage Tracker */}
            {currentStage !== "idle" && (
              <div className="demo-card demo-status-card">
                <div className="demo-section-title">Durum</div>
                <div className="demo-stages">
                  {STAGE_ORDER.map((stage, i) => {
                    const currentIdx = STAGE_ORDER.indexOf(currentStage as Stage);
                    const isActive = stage === currentStage && currentStage !== "tamamlandı";
                    const isDoneStage =
                      currentStage === "tamamlandı"
                        ? true
                        : i < currentIdx;
                    const isPending = i > currentIdx && currentStage !== "tamamlandı";

                    return (
                      <div
                        key={stage}
                        className={`demo-stage-item${isActive ? " active" : ""}${isDoneStage ? " done" : ""}${isPending ? " pending" : ""}`}
                      >
                        <div className="demo-stage-dot">
                          {isDoneStage && !isActive ? (
                            <span className="demo-dot-check">✓</span>
                          ) : isActive ? (
                            <span className="demo-dot-pulse" />
                          ) : (
                            <span className="demo-dot-empty" />
                          )}
                        </div>
                        <div className="demo-stage-info">
                          <span className="demo-stage-icon">{STAGE_ICONS[stage]}</span>
                          <span className="demo-stage-name">{stage}</span>
                        </div>
                        {isActive && jobStatus && (
                          <span className="demo-stage-pct">{jobStatus.pct}%</span>
                        )}
                      </div>
                    );
                  })}
                  {currentStage === "hata" && (
                    <div className="demo-stage-item active error">
                      <div className="demo-stage-dot">
                        <span className="demo-dot-error">✕</span>
                      </div>
                      <div className="demo-stage-info">
                        <span className="demo-stage-icon">❌</span>
                        <span className="demo-stage-name">Hata oluştu</span>
                      </div>
                    </div>
                  )}
                </div>

                {/* Progress bar */}
                {jobStatus && currentStage !== "tamamlandı" && currentStage !== "hata" && (
                  <div className="demo-progress-wrap">
                    <div
                      className="demo-progress-bar"
                      style={{ width: `${jobStatus.pct}%` }}
                    />
                  </div>
                )}

                {/* Detail text */}
                {jobStatus?.detail && (
                  <div className="demo-detail-text">{jobStatus.detail}</div>
                )}

                {/* Error */}
                {serverError && (
                  <div className="demo-error-box">
                    <strong>Hata:</strong> {serverError}
                    <br />
                    <small>
                      Demo sunucusu çalışıyor mu?{" "}
                      <code>python demo_server.py</code> ile başlatın.
                    </small>
                  </div>
                )}
              </div>
            )}

            {/* Result Card */}
            {isDone && jobStatus && (
              <div className="demo-card demo-result-card">
                <div className="demo-result-header">
                  <span className="demo-result-badge">✅ Tamamlandı</span>
                  <span className="demo-result-size">
                    {jobStatus.file_size_mb?.toFixed(2)} MB
                  </span>
                </div>

                <div className="demo-meta-grid">
                  {jobStatus.room_count && (
                    <div className="demo-meta-item">
                      <span className="demo-meta-icon">🏠</span>
                      <span className="demo-meta-label">Oda / Mekan</span>
                      <span className="demo-meta-val">{jobStatus.room_count}</span>
                    </div>
                  )}
                  {jobStatus.crs && (
                    <div className="demo-meta-item">
                      <span className="demo-meta-icon">📍</span>
                      <span className="demo-meta-label">CRS</span>
                      <span className="demo-meta-val">
                        {jobStatus.crs}{jobStatus.epsg ? ` (EPSG:${jobStatus.epsg})` : ""}
                      </span>
                    </div>
                  )}
                  {jobStatus.gml_name && (
                    <div className="demo-meta-item">
                      <span className="demo-meta-icon">📄</span>
                      <span className="demo-meta-label">GML Dosyası</span>
                      <span className="demo-meta-val">{jobStatus.gml_name}</span>
                    </div>
                  )}
                </div>

                <a
                  href={`${DEMO_API}/demo/download/${jobId}`}
                  download
                  className="demo-download-btn"
                >
                  ⬇ MP4 İndir
                </a>
              </div>
            )}

            {/* Idle placeholder */}
            {currentStage === "idle" && (
              <div className="demo-card demo-idle-card">
                <div className="demo-idle-icon">🎬</div>
                <div className="demo-idle-title">Render bekleniyor</div>
                <div className="demo-idle-sub">
                  Soldaki formu doldurun ve&nbsp;
                  <strong>3D Video Oluştur</strong>&nbsp;butonuna tıklayın.
                </div>
                <div className="demo-idle-steps">
                  <div className="demo-idle-step">
                    <span>📝</span> Bilgileri gir
                  </div>
                  <div className="demo-idle-arrow">→</div>
                  <div className="demo-idle-step">
                    <span>🚀</span> Video oluştur
                  </div>
                  <div className="demo-idle-arrow">→</div>
                  <div className="demo-idle-step">
                    <span>⬇</span> MP4 indir
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
