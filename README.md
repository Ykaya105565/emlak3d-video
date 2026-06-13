# Emlak 3D Video Platformu

Türkiye geneli emlakçı platformu. Taşınmazın **dış mekânı** gerçek coğrafi konumda
(Google Photorealistic 3D Tiles, yoksa 2D fallback), **iç mekânı** ise kaynak
hiyerarşisine göre **(1) CityGML 3D tur → (2) Fotoğraflar → (3) İlan verisi grafik**
olarak seslendirmeli video haline getirilir.

---

## Hızlı Başlangıç

### 1. Ortamı Hazırla

```bash
git clone <repo>
cd emlak2

# .env dosyasını oluştur ve API anahtarlarını ekle
cp .env.example .env
# .env dosyasını düzenle: GOOGLE_MAPS_API_KEY, CLAUDE_API_KEY, TTS_API_KEY
```

### 2. Tüm Sistemi Başlat

```bash
docker-compose up --build
```

Servisler:
| Servis | URL |
|--------|-----|
| Frontend (CRM) | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| MinIO Konsol | http://localhost:9001 (minioadmin / minioadmin123) |
| Render Worker | http://localhost:8001 |

### 3. Demo Veri (opsiyonel)

```bash
# Altyapı çalışırken yeni terminalde:
docker-compose exec backend python scripts/seed_db.py
# demo@example.com / demo1234
```

---

## Faz 0 — GML Hattı Testi

**Önce .gml dosyanızı koyun:**

```bash
cp M-94777652-A.gml data/sample/
cp M-94777652-B.gml data/sample/  # opsiyonel
```

**Oda envanteri çıkar:**

```bash
# Python bağımlılıkları (render klasöründe)
cd render
pip install -r requirements.txt

# Test çalıştır
cd ..
python scripts/phase0_gml_test.py data/sample/M-94777652-A.gml
```

Çıktı:
- `data/sample/M-94777652-A_inventory.json` — oda envanteri
- Terminalde: oda tablosu, kat planı, bağımsız bölümler, tur sırası

**glTF modeli üret:**

```bash
python scripts/phase0_gml_test.py data/sample/M-94777652-A.gml --export-gltf output/model.glb
```

**Three.js tur keyframe'leri:**

```bash
cd render
node src/threejs/interior_walk.js \
  --inventory ../data/sample/M-94777652-A_inventory.json \
  --fps 25 --duration 30 \
  --output /tmp/interior_frames
```

---

## Anahtarsız MP4 Üretimi (Faz 0 — Hızlı Test)

**API anahtarı gerektirmez.** GML → PIL kareler → sessiz audio → MP4.

```bash
# 1. Ortamı kur (uv veya pip)
python -m venv .venv && .venv\Scripts\activate   # Windows
pip install lxml pyproj shapely numpy Pillow loguru gtts "imageio[ffmpeg]"

# 2. Örnek GML ile 30 saniyelik video üret
python scripts/render_phase0.py sample_data/M-12345.gml --duration 30

# Sonuç: output/M-12345_<timestamp>/tour_<timestamp>.mp4

# Seçenekler
python scripts/render_phase0.py sample_data/M-12345.gml \
  --duration 60 \          # video süresi (15/30/60/90)
  --fps 25 \               # kare hızı
  --tts gtts \             # TTS: auto | gtts | pyttsx3 | silent
  --title "Örnek Daire" \  # anlatıda kullanılacak başlık
  --keep-frames            # PNG karelerini silme
```

**TTS öncelik sırası (auto):**
1. ElevenLabs → `ELEVENLABS_API_KEY` varsa
2. gTTS → internet gerektiren Google TTS (ücretsiz, anahtar yok)
3. pyttsx3 → tamamen yerel, internet yok
4. silent → sessiz audio

---

## Geliştirme

### Backend (sadece API)

```bash
cd backend
pip install -r requirements.txt
# .env dosyası kökünde olmalı; altyapı docker-compose ile çalışmalı
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### Frontend (sadece UI)

```bash
cd frontend
npm install
npm run dev
```

### Render Worker (Python)

```bash
cd render
pip install -r requirements.txt
python src/pipeline.py  # HTTP API, port 8001
```

### Celery Worker

```bash
cd backend
celery -A app.core.celery_app worker --loglevel=info -Q render,default
```

---

## Proje Yapısı

```
emlak2/
├── backend/          FastAPI + Celery (API, auth, kredi, kuyruk)
├── frontend/         React + TS + Vite (CRM, form, önizleme)
├── render/           Render worker (GML, three.js, Remotion, ffmpeg)
├── data/sample/      Örnek .gml dosyaları buraya
├── scripts/          Faz 0 test + DB seed
├── CLAUDE.md         Geliştirici kılavuzu
└── TODO.md           Faz yol haritası
```

---

## İç Mekân Kaynak Hiyerarşisi

| Öncelik | Kaynak | Açıklama |
|---------|--------|----------|
| **1** | **CityGML (.gml)** | Gerçek oda geometrisi, alan, isim — resmî MAKS/TAKBİS verisi |
| 2 | Fotoğraflar | Ken Burns + 2.5D parallax efekti |
| 3 | Sadece ilan verisi | After-effects tarzı bilgi animasyonu — iç mekân UYDURULMAZ |

---

## API Anahtarları

`.env` dosyasına eklenecekler:

| Anahtar | Nerede alınır |
|---------|--------------|
| `GOOGLE_MAPS_API_KEY` | Google Cloud Console → Maps Platform |
| `CLAUDE_API_KEY` | console.anthropic.com |
| `TTS_API_KEY` | Google Cloud TTS veya ElevenLabs |
| `CESIUM_ION_TOKEN` | ion.cesium.com (opsiyonel) |

---

## Notlar

- **KVKK:** Tüm yükleme/işleme öncesi onay akışı zorunludur (backend'de uygulanır)
- **"Temsilîdir" ibaresi:** GML kaplama/mobilya ve Villa Hayali görsellerinde videoda görünür
- **Müzik:** Sadece telifsiz/lisanslı kütüphane — `render/assets/music/` klasörüne koyun
- **Google 3D Tiles ticari kullanımı:** Ticari dağıtım sözleşme öncesi hukuken doğrulanmalıdır (bkz. CLAUDE.md §8)

---

## Faz Durumu

- [x] **ADIM 1** — Anahtarsız MP4 (GML→PIL→TTS→MP4): `output/test_phase0/` altında gerçek video ✅
- [x] **ADIM 2** — Uçtan uca iş akışı: Alembic migration, Celery→render-worker HTTP, PIL fallback ✅
- [x] **ADIM 3** — İç mekân hiyerarşisi: InteriorGML / InteriorPhoto / InteriorData / VillaHayali Remotion kompozisyonları ✅
- [x] **ADIM 4** — Dış mekân 2D fallback: GML centroid WGS84 → drone orbit animasyonu ✅
- [x] **ADIM 5** — Villa Hayali: TAKS/KAKS imar zarfı hesabı + PIL görselleştirme ✅
- [x] **ADIM 6** — Referans verisi: 35 oda tipi, 24 kredi tarife, 8 imar türü, 3 müzik kaydı ✅
- [ ] **Docker Test** — `docker-compose up --build` (Docker Desktop gerekli)
- [ ] **gTTS Test** — `--tts gtts` (internet bağlantısı gerekli)
- [ ] **Faz 1 MVP** — Gerçek kullanıcı + ödeme + ilan akışı
- [ ] **Faz 2** — Cesium 3D Tiles entegrasyonu (anahtar gerekli)
