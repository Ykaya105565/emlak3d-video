# CLAUDE.md — Emlak 3D Video Platformu

Türkiye geneli emlakçı platformu. Taşınmazın **dış mekânı** gerçek coğrafi konumda
(fotorealistik 3D, yoksa 2D fallback), **iç mekânı** ise kaynak hiyerarşisine göre
(GML > fotoğraf > ilan verisi) seslendirmeli + efektli video olarak üretilir.

## Stack

| Katman | Teknoloji |
|--------|-----------|
| Frontend | React 18 + TypeScript + Vite, CesiumJS (dış 3D), three.js (iç GML), Remotion |
| Backend | FastAPI, SQLAlchemy, Celery + Redis, Alembic |
| Render Worker | Node.js + Remotion CLI, ffmpeg, citygml-tools, Python (pyproj, lxml, trimesh) |
| Veritabanı | PostgreSQL 15 + PostGIS 3, MinIO (S3 uyumlu depo) |
| Auth | JWT (RS256), çok-kiracılı (tenant per emlakçı) |
| AI/TTS | Claude API (senaryo), Google Cloud TTS veya ElevenLabs |
| Geocoding | Google Geocoding API (birincil), Nominatim/OSM (fallback) |
| Harita/3D | Google Photorealistic 3D Tiles (dış), TKGM/MAKS (parsel) |

## Dizin Yapısı

```
emlak2/
├── CLAUDE.md
├── TODO.md
├── docker-compose.yml
├── .env.example
├── frontend/            # React + TS + Vite
│   ├── src/
│   │   ├── components/
│   │   │   ├── crm/         # CRM listeleme, müşteri
│   │   │   ├── listing/     # İlan formu (zengin)
│   │   │   ├── upload/      # GML/foto yükleme
│   │   │   ├── preview/     # CesiumJS dış + three.js iç önizleme
│   │   │   └── video/       # Süre/stil seçimi, indirme
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── api/             # Backend API istemcisi
│   │   └── types/
│   ├── package.json
│   └── vite.config.ts
├── backend/             # FastAPI
│   ├── app/
│   │   ├── api/
│   │   │   ├── auth.py
│   │   │   ├── listings.py
│   │   │   ├── uploads.py
│   │   │   ├── geocoding.py
│   │   │   ├── credits.py
│   │   │   ├── videos.py
│   │   │   └── kvkk.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── security.py
│   │   │   └── database.py
│   │   ├── models/          # SQLAlchemy ORM
│   │   ├── schemas/         # Pydantic schemas
│   │   ├── services/
│   │   │   ├── gml_parser.py      # CityGML → CityJSON → mesh
│   │   │   ├── geocoding.py
│   │   │   ├── scenario.py        # Claude API senaryo üretimi
│   │   │   ├── tts.py
│   │   │   ├── render_queue.py    # Celery görev tetikleyici
│   │   │   └── kvkk.py
│   │   └── main.py
│   ├── alembic/
│   ├── requirements.txt
│   └── Dockerfile
├── render/              # Render worker
│   ├── src/
│   │   ├── gml/
│   │   │   ├── parse.py           # citygml-tools sarmalayıcı
│   │   │   ├── measure.py         # Geodezik oda alanı (pyproj)
│   │   │   └── gltf_export.py     # glTF üretimi
│   │   ├── cesium/
│   │   │   └── exterior_shot.js   # CesiumJS dış uçuş
│   │   ├── threejs/
│   │   │   └── interior_walk.js   # three.js oda yürüyüşü
│   │   ├── remotion/
│   │   │   ├── compositions/
│   │   │   │   ├── ExteriorScene.tsx
│   │   │   │   ├── InteriorGML.tsx
│   │   │   │   ├── InteriorPhoto.tsx
│   │   │   │   ├── InteriorData.tsx
│   │   │   │   └── VillaHayali.tsx
│   │   │   └── index.tsx
│   │   └── pipeline.py            # Uçtan uca orkestrasyon
│   ├── requirements.txt
│   ├── package.json
│   └── Dockerfile
├── data/
│   └── sample/                    # Örnek .gml dosyaları buraya koyulur
└── scripts/
    ├── phase0_gml_test.py         # Faz 0 hızlı test
    └── seed_db.py
```

## Temel Komutlar

```bash
# Tüm sistemi ayağa kaldır
docker-compose up --build

# Sadece altyapı (db, redis, minio)
docker-compose up db redis minio

# Backend geliştirme (altyapı çalışıyorken)
cd backend && uvicorn app.main:app --reload --port 8000

# Frontend geliştirme
cd frontend && npm run dev

# Render worker (Python GML hattı)
cd render && python src/pipeline.py --gml data/sample/M-94777652-A.gml

# DB migration
cd backend && alembic upgrade head

# Faz 0 GML testi
python scripts/phase0_gml_test.py data/sample/M-94777652-A.gml
```

## Kritik Kurallar

1. **İç mekân kaynak hiyerarşisi:** GML varsa → gerçek 3D tur; yoksa fotoğraf; yoksa
   ilan verisinden grafik. Fotoğraf/GML yoksa iç mekân asla UYDURULMAZ.
2. **KVKK:** Her yükleme/işleme öncesi açık rıza onay kutusu ve aydınlatma metni zorunlu.
3. **"Temsilîdir" ibaresi:** GML kaplama/mobilya ve Villa Hayali görsellerinde videoda
   mutlaka gösterilir.
4. **Müzik:** Sadece telifsiz/ticari kullanıma uygun lisanslı kütüphane. Başka müzik yok.
5. **Video hakkı:** Ticari kullanım/dağıtım hakkı emlakçıya ait. Üst kaynak lisansları
   (Google 3D Tiles, müzik) sözleşme öncesi hukuken doğrulanmalı.
6. **Geocoding:** Google birincil → Nominatim fallback. Sonuç haritada kullanıcıya
   doğrulatılır.
7. **Koordinat sistemi:** GML EPSG:5254 (TUREF/TM30) → pyproj ile WGS84.
8. **Kredi modeli:** süre × çözünürlük × iç mekân tipi × özellik çarpanları.

## API Anahtarları (.env.example)

- `GOOGLE_MAPS_API_KEY` — Geocoding + 3D Tiles
- `CLAUDE_API_KEY` — Senaryo üretimi
- `TTS_PROVIDER` + `TTS_API_KEY` — Google TTS veya ElevenLabs
- `DATABASE_URL`, `REDIS_URL`, `MINIO_*`

## Faz Durumu

- [ ] **Faz 0:** GML hattı kanıtı (bkz. TODO.md)
- [ ] **Faz 1:** MVP
- [ ] **Faz 2:** Villa Hayali
- [ ] **Faz 3:** Premium & Ölçek
