# TODO — Emlak 3D Video Platformu

## FAZ 0 — Fizibilite (1-2 hafta) [ŞU AN]

### 0.1 Proje İskeleti
- [x] CLAUDE.md oluştur
- [x] TODO.md oluştur
- [x] docker-compose.yml + .env.example
- [x] Monorepo dizin yapısı (frontend/ backend/ render/)
- [ ] `docker-compose up` → tüm servisler ayağa kalkar

### 0.2 GML Hattı (render/)
- [x] Python (lxml+pyproj+shapely) ile oda envanteri çıkarımı:
  - [x] Oda adları (`partUsage`, `name`, `gen:stringAttribute`)
  - [x] Kat bilgisi
  - [x] Bağımsız bölüm gruplandırması (BuildingPart + bagimsizbölüm_no)
  - [x] Dinamik EPSG: srsName → tüm TUREF/TM27-45 + WGS84/ED50 + bilinmeyen → uyarı
  - [x] Taban poligon → local_m → area_m2 (Shapely)
  - [x] WGS84 dönüşümü (pyproj always_xy=True)
- [x] glTF üretimi (trimesh.creation.extrude_polygon → .glb)
- [x] `srs_utils.py`: EPSG tespit, TUREF TM27-45, koordinat büyüklüğü fallback

### 0.3 Three.js İç Mekân Turu
- [ ] glTF yükleme (three.js / React Three Fiber)
- [ ] Otomatik kamera yürüyüşü: giriş → salon → hol → odalar → banyo
- [ ] Kapı geçiş animasyonları
- [ ] Göz hizası kamera (~1.6 m), yumuşak easing
- [ ] Oda adı kartları (overlay)

### 0.4 CesiumJS Dış Uçuş
- [ ] Google 3D Tiles entegrasyonu
- [ ] Koordinat: EPSG:5254 → WGS84 (pyproj/GML'den)
- [ ] Sinematik dış uçuş (drone hissiyatı)
- [ ] 2D fallback: kapsama yoksa uydu/harita animasyonu (Leaflet/OpenLayers)

### 0.5 Remotion Kompozisyonu
- [ ] `InteriorGML.tsx` — three.js iç tur sahnesi
- [ ] `ExteriorScene.tsx` — Cesium dış uçuş
- [ ] Oda isimli kartlar (overlay animasyon)
- [ ] TTS taslağı: oda envanterinden otomatik metin → ses
- [ ] Efektler: geçiş, intro/outro
- [ ] MP4 export (`remotion render`)

### 0.5 Anahtarsız PIL Video Hattı ✅
- [x] `frame_generator.py`: PIL 1920×1080 kare üretimi (kat planı + oda kartı + footer)
- [x] `tts.py`: gTTS (ücretsiz) → pyttsx3 (yerel) → sessizlik zinciri
- [x] `pipeline_phase0.py`: GML → kareler → TTS → MP4 (imageio[ffmpeg] veya sistem ffmpeg)
- [x] `scripts/render_phase0.py`: CLI orkestratör

### 0.6 Faz 0 Doğrulaması ✅
- [x] `sample_data/M-12345.gml` (EPSG:5254 TUREF/TM30) → 12 oda, 2 bağımsız bölüm
- [x] `output/test_phase0/tour_*.mp4` — 0.4 MB, 15 saniye, anahtarsız
- [x] README'ye `scripts/render_phase0.py` çalıştırma talimatı
- [x] Alembic: `0001_initial_schema.py` + `0002_seed_reference_data.py`

---

## FAZ 1 — MVP (7-9 hafta)

### 1.1 Backend Çekirdek
- [ ] FastAPI app + JWT auth (RS256)
- [ ] Çok-kiracılı yapı (tenant per emlakçı)
- [ ] PostgreSQL + PostGIS model migrasyonları (Alembic)
- [ ] MinIO dosya depolama entegrasyonu

### 1.2 CRM & İlan Formu
- [ ] Taşınmaz CRUD (konum, tip, m², oda sayısı, kat, fiyat)
- [ ] Zengin ilan formu (tüm alanlar)
- [ ] GML dosya yükleme + doğrulama + KVKK onay kutusu
- [ ] Foto yükleme (çoklu) + KVKK onay kutusu
- [ ] Kapsama kontrolü → kullanıcıya kalite bilgisi

### 1.3 İç Mekân Kaynak Hiyerarşisi (3 Yol)
- [ ] GML → gerçek 3D tur pipeline (Faz 0'dan)
- [ ] Fotoğraf → Ken Burns / 2.5D parallax + veri kartları
- [ ] Sadece ilan verisi → after-effects tarzı grafik animasyon
- [ ] Otomatik kaynak seçimi (GML > foto > veri)

### 1.4 Senaryo & TTS
- [ ] Claude API ile veri-güdümlü senaryo üretimi
- [ ] Premium TTS (Google Cloud TTS veya ElevenLabs)
- [ ] Telifsiz müzik kütüphanesi + ducking (ffmpeg)

### 1.5 Video Pipeline
- [ ] Remotion şablonları (tüm 3 iç mekân yolu + dış)
- [ ] Kullanıcı süre seçimi (15/30/60/90 sn)
- [ ] 16:9 + dikey 9:16; 1080p / 4K
- [ ] Celery + Redis render kuyruğu
- [ ] Watermark'lı önizleme MP4
- [ ] Markasız indirme (kredi harcar)

### 1.6 Kredi Sistemi
- [ ] Kredi cüzdanı (backend)
- [ ] Fiyat hesaplama: süre × çözünürlük × iç mekân tipi × özellik
- [ ] Satın alma akışı (Stripe veya iyzico)
- [ ] 1 ücretsiz watermark'lı deneme / taşınmaz

### 1.7 KVKK
- [ ] Açık rıza/onay kutuları (yükleme, işleme)
- [ ] Aydınlatma metni
- [ ] Erişim logları + silme/saklama politikası
- [ ] Alt işleyenlerle veri işleme sözleşme şablonları

### 1.8 Geocoding + Parsel
- [ ] Google Geocoding API entegrasyonu
- [ ] Nominatim fallback
- [ ] Adres → koordinat → haritada kullanıcı doğrulaması
- [ ] TKGM/MAKS ada/parsel doğrulaması

---

## FAZ 2 — Arsa & Villa Hayali (5-7 hafta)

- [ ] Parsel seçimi + imar zarfı hesabı
- [ ] Emlakçı TAKS/KAKS/çekme/maks kat girişi
- [ ] Villa modeli kütüphanesi (yapılaşma zarfına oturt)
- [ ] Efektli "beliriş" animasyonu (gerçek konumda)
- [ ] "Temsilîdir" ibaresi + belediye imar durumu uyarısı
- [ ] 4K + dikey 9:16 + ek stiller
- [ ] Villa Hayali kredi modeli (+3 kredi)

---

## FAZ 3 — Premium & Ölçek

- [ ] Drone fotogrametri (ultra kalite)
- [ ] 2.5D foto parallax (gelişmiş)
- [ ] Worker auto-scaling (GPU)
- [ ] Kuyruk önceliği (paket bazlı)
- [ ] Maliyet tavanı/alarm sistemi
- [ ] 3D Tiles / 2D kare önbelleği
- [ ] Analitik dashboard
