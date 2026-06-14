# Emlak 3D Video Platformu — Teknik Plan (v4 · GML İç Mekân + Tüm Kararlar)

> **Ürün:** Türkiye geneli emlakçı platformu. Taşınmazın **dış mekânı** gerçek coğrafi konumda (fotorealistik 3D, yoksa 2D fallback), **iç mekânı** ise öncelik sırasıyla **(1) yüklenen CityGML (.gml) dosyasından gerçek 3D tur**, yoksa **(2) fotoğraflardan**, yoksa **(3) ilan bilgilerinden after-effects tarzı hareketli grafikle** üretilir. Video **seslendirmeli + efektlidir**. Boş arsada **Villa Hayali** konsept videosu yapılır. Emlakçı videoyu **indirir**, **ticari kullanım hakkı kendisine ait**; sen **video başına ücret** alırsın.

---

## 0. Kilitlenen Kararların Tümü

| # | Konu | Karar |
|---|------|-------|
| 1 | **İç mekân kaynağı** | **GML varsa → gerçek 3D tur**; yoksa fotoğraf; yoksa ilan verisinden efektli grafik |
| 2 | **3D kapsama dışı** | Fotorealistik yoksa **2D görsel** (uydu/harita üzerinde efektli animasyon) |
| 3 | **KVKK** | Tasarımdan itibaren uyumlu (privacy-by-design) |
| 4 | **Müzik** | **Telifsiz/lisanslı müzik kütüphanesi** |
| 5 | **Video hakkı** | **Ticari kullanım/dağıtım hakkı emlakçıya ait** *(üst lisans şartı doğrulanmalı — bkz. §9)* |
| 6 | **Geocoding** | Birincil **Google**, fallback **OSM/Nominatim** *(kararım — §6)* |
| 7 | **Villa Hayali imar** | TAKS/KAKS/çekme **emlakçı girer** |
| 8 | **Video süresi** | **Kullanıcı belirler** (kredi maliyetini etkiler) |
| 9 | **Kredi fiyatı** | Süre × çözünürlük × iç mekân tipine göre modellenir |
| 10 | **Ölçek/ops** | Paket bazlı kuyruk önceliği + worker auto-scaling *(kararım — §10)* |

---

## 1. Senin Dosyandan Kanıt (M-94777652-A/B.gml)

Yüklediğin dosyalar **CityGML 2.0 LoD4** — Türkiye **MAKS/TAKBİS** "Mimari Bina" modelleri. İçinden çıkanlar:

- **İki bina** (A, B), aynı taşınmaz: **ada 2363 / parsel 9**, TAKBİS no 94777652, **EPSG:5254 (TUREF/TM30)**, ikisi de 2 katlı.
- **Gerçek iç mekân geometrisi:** 28 oda, 68 kapı, 32 pencere (LoD4 yüzeyleri).
- **İsimli ve işlevli odalar:** A binasında 1 Salon · 4 Oda · 3 Banyo · 3 Balkon · 2 Hol · Merdiven · Kiler · Isı Merkezi — `partUsage` kodlarıyla.
- **Bağımsız bölüm (daire) gruplaması:** Her oda `independentSectionObjectReference` ile bir daireye bağlı (A'da 2 bağımsız bölüm).

> **Sonuç:** Bu dosyayla, fotoğraf olmadan **gerçek, isimli, alanı geodezik hesaplanabilir** bir iç mekân turu + otomatik anlatım üretilebilir. Bu, Türkiye'ye özgü ve rakiplerin yapamayacağı bir ayrışma. Taban poligonlarından oda alanı hesabı senin için rutin.

---

## 2. İç Mekân Kaynak Hiyerarşisi (Ürünün Yeni Kalbi)

Dış mekân her zaman gerçek coğrafyadan gelir. İç mekân ise **mevcut en iyi kaynağa** göre otomatik seçilir:

```
ÖNCELİK 1 — CityGML (.gml) yüklendi    →  GERÇEK 3D İÇ MEKÂN TURU
   Oda geometrisi + isim + alan + kat + daire → otomatik yürüyüş + anlatım
   (En yüksek değer · resmî veri · fotoğraf gerekmez)

ÖNCELİK 2 — Fotoğraf var                →  FOTOĞRAF TABANLI
   Ken Burns / 2.5D parallax + veri kartları (gerçek görseller)

ÖNCELİK 3 — Sadece ilan bilgisi          →  AFTER-EFFECTS TARZI GRAFİK
   Girilen tüm alanlardan hareketli kartlar, şematik oda dökümü, özellik
   vurguları + seslendirme (iç mekân UYDURULMAZ; bilgi animasyonu)
```

**Dürüstlük ilkesi:** Öncelik 3'te gerçek iç mekân yoktur → fotorealistik iç görsel uydurulmaz; bunun yerine bilgiyi efektli grafikle anlatan dürüst bir video kurulur. GML'de ise **geometri/alan gerçektir, kaplama/mobilya temsilîdir** (bu ayrım videoda belirtilir).

---

## 3. CityGML İç Mekân Hattı (Yeni Ana Bileşen)

```
.gml (CityGML LoD4)
   │
   ▼ 1) AYRIŞTIRMA
   citygml-tools → CityJSON (programatik işlemesi kolay)
   ├── Oda yüzeyleri (Taban/Duvar), kapı/pencere
   ├── Öznitelik: oda adı, partUsage, daire referansı, kat
   └── EPSG:5254 → pyproj ile WGS84/ECEF (gerçek konuma oturtmak için)
   │
   ▼ 2) GEOMETRİ → MESH
   Yüzey üçgenleme → glTF (web'de three.js/Cesium ile render)
   │
   ▼ 3) ÖLÇÜM (senin alanın)
   Taban poligon alanı → oda m² · daire net alanı · kat planı
   │
   ▼ 4) OTOMATİK YÜRÜYÜŞ KAMERASI
   Giriş → Salon → Hol → Odalar → Banyo sırası; kapı geçişleri;
   göz hizası (~1.6 m); yumuşak easing
   │
   ▼ 5) ANLATIM (veriden)
   "2 bağımsız bölüm; her dairede salon, 2 oda, banyo; ~X m² net;
    güney cepheli balkon..." → Claude → premium TTS
```

**Araç seti:** `citygml-tools`/`citygml4j` (CityGML↔CityJSON), Python (lxml/`cjio`) ile öznitelik + alan, `pyproj` (EPSG:5254→WGS84), glTF üretimi, three.js/Cesium ile render. Bu hat aynı zamanda binayı **gerçek konumuna** (dış fotorealistik sahneye) oturtmak için de koordinatları sağlar — iç ve dış tek videoda birleşir.

---

## 4. Dış Mekân & 2D Fallback (Karar 2)

| Durum | Çıktı |
|-------|-------|
| Fotorealistik 3D var | Sinematik 3D uçuş (Google 3D Tiles) |
| **Yok** | **2D görsel animasyon:** uydu/harita görüntüsü üzerinde pan/zoom, parsel/konum vurgusu, mesafe/POI grafikleri, efektli geçişler |

2D fallback, Remotion ile hareketli harita/uydu kompozisyonu olarak üretilir; ucuz, hızlı, her yerde çalışır. Girişte kapsama kontrolü kullanıcıya beklenen kaliteyi söyler.

---

## 5. Video Kompozisyon & Süre (Karar 8)

```
KATMAN 1 — Geospatial 3D (Cesium)        : dış uçuş / villa / 2D fallback
KATMAN 2 — İç mekân 3D (three.js, GML)   : oda turu  (varsa)
KATMAN 3 — Kompozisyon/Efekt (Remotion)  : foto, hareketli kart, geçiş,
                                            intro/outro, marka, "after-effects"
KATMAN 4 — Ses (ffmpeg)                   : TTS + telifsiz müzik (ducking) + master
```
- **Süreyi kullanıcı seçer** (ör. 15 / 30 / 60 / 90 sn). Sistem anlatım ve shot sayısını seçilen süreye göre otomatik dağıtır (kısa → özet; uzun → oda oda detay).
- 16:9 + dikey 9:16; 1080p / 4K.

---

## 6. Geocoding Sağlayıcı + Fallback (Karar 6 — kararım)
- **Birincil: Google Geocoding** (Türkiye adres kapsamı/doğruluğu en iyi).
- **Fallback: Nominatim/OSM** (maliyet düşürme + Google boşlukları).
- **Parsel:** TKGM/MAKS verisi (GML'de zaten ada/parsel mevcut — doğrulama için kullanılır).
- Adres → koordinat sonucu haritada kullanıcıya doğrulatılır (yanlış pin = yanlış video).

---

## 7. Villa Hayali (Karar 7)
- Emlakçı **TAKS / KAKS / çekme mesafeleri / maks kat**'ı **elle girer**.
- Sistem yapılaşma zarfını hesaplar → villa modelini zarfa oturtur → gerçek konum + manzarada efektli "beliriş" + seslendirme.
- Zorunlu ibare: **"Temsilîdir; kesin haklar için belediyeden imar durumu alınmalıdır."**

---

## 8. Hukuk & Uyum

### KVKK (Karar 3) — privacy-by-design
- Açık rıza/onay kutuları (foto/GML yükleme, veri işleme), aydınlatma metni.
- Veri minimizasyonu, şifreleme (transit + at-rest), erişim logları, silme/saklama politikası.
- Yüklenen GML/foto'da kişisel veri olabilir (malik, adres) → işleme amacı sınırlı, gerekirse maskeleme.
- Alt işleyenlerle (TTS, 3D Tiles, bulut) veri işleme sözleşmeleri.

### Müzik (Karar 4)
- **Telifsiz/lisanslı kütüphane** (ör. ticari kullanıma uygun lisanslı katalog). Her parçanın ticari + alt-lisanslama hakkı doğrulanır.

### Video Ticari Hakkı (Karar 5) ⚠️ doğrulanmalı
- Politika: üretilen videonun **ticari kullanım/dağıtım hakkı emlakçıya ait**.
- **Kritik:** Bunu verebilmek için **üst kaynakların** (özellikle Google Photorealistic 3D Tiles ile üretilen videonun ticari dağıtımı, müzik, harita) lisanslarının buna izin vermesi şart. Bu, **sözleşme öncesi hukuken doğrulanması gereken 1 numaralı madde.** GML iç mekân (kullanıcının kendi/resmî verisi) ve 2D fallback yollarında bu bağımlılık daha hafiftir; risk asıl fotorealistik dış sahnede.

---

## 9. Kredi Modeli (Karar 9)

Kredi = **süre × çözünürlük × iç mekân tipi × özellik**. Örnek iskelet:

| Bileşen | Kredi etkisi |
|---------|--------------|
| Süre | 15sn baz → her +15sn artış |
| Çözünürlük | 1080p baz · 4K +1 |
| İç mekân: ilan verisi (öncelik 3) | +0 (en ucuz) |
| İç mekân: fotoğraf | +0–1 |
| **İç mekân: GML 3D tur** | **+2** (ayrıştırma + render maliyetli) |
| **Villa Hayali (arsa)** | **+3** |
| 2D fallback | −1 (ucuz) |

- Her render'ın **gerçek maliyeti** (3D Tiles çağrısı + Cesium + three.js + Remotion + TTS + depolama) ölçülür; kredi fiyatı marjla buna oturtulur.
- 1 ücretsiz **watermark'lı** deneme → markasız indirme kredi ister.

---

## 10. Ölçek & Operasyon (Karar 10 — kararım)
- **Kuyruk önceliği paket bazlı:** üst paket emlakçıların render'ı öne alınır.
- **Worker auto-scaling:** yük arttıkça GPU worker eklenir, boşta küçülür (maliyet kontrolü).
- **Maliyet tavanı/alarm:** video başı maliyet eşiği aşılırsa uyarı.
- **Önbellek:** aynı konumun 3D Tiles/2D karesi tekrar kullanılır.

---

## 11. Mimari Özet

```
FRONTEND (React+TS): CRM · zengin ilan formu · GML/foto yükleme · 3D önizleme · süre/stil seçimi · indirme
BACKEND (FastAPI): auth/çok-kiracılı · kredi cüzdanı · geocoding+parsel · GML ayrıştırma · imar zarfı · senaryo(Claude)+TTS · render kuyruğu(Celery/Redis) · KVKK günlükleri
RENDER WORKER (GPU): Cesium(dış/villa) · three.js(GML iç) · Remotion(efekt/foto/metin) · ffmpeg(ses+master+watermark)
VERİ: PostgreSQL+PostGIS · S3 · Google 3D Tiles · TKGM/MAKS · DEM · telifsiz müzik
```

---

## 12. Yol Haritası (güncel)

### Faz 0 — Fizibilite (1–2 hafta) ⚠️
- [ ] **GML hattı:** `M-94777652-A.gml` → CityJSON → glTF → three.js'te oda turu (SENİN gerçek dosyanla)
- [ ] Cesium ile gerçek konumda dış uçuş
- [ ] Remotion ile efekt + veri kartı + TTS → indirilebilir örnek MP4
- **Çıktı:** "Gerçek GML'den iç tur + dış uçuş + efekt + ses" satılabilir kalitede mi?

### Faz 1 — MVP (7–9 hafta)
- [ ] Zengin form + GML/foto yükleme + iç mekân hiyerarşisi (3 yol)
- [ ] Veri-güdümlü senaryo + premium TTS + Remotion şablonları
- [ ] Kullanıcı süre seçimi + kredi cüzdanı + MP4 indirme + KVKK onayları
- [ ] Kapsama kontrolü + 2D fallback

### Faz 2 — Arsa + Villa Hayali (5–7 hafta)
- [ ] Parsel + imar zarfı (TAKS/KAKS elle) + villa kütüphanesi + efektli beliriş
- [ ] 4K + dikey 9:16 + ek stiller

### Faz 3 — Premium & Ölçek
- [ ] Drone fotogrametri (ultra), 2.5D foto parallax, auto-scaling, analitik

---

## 13. Sıradaki Adım

Faz 0'ın en kritik ve en ikna edici parçası artık net: **senin gerçek `M-94777652-A.gml` dosyandan** çalışan bir iç mekân turu çıkarmak. Önerim, hemen şunu yapalım:

1. GML → CityJSON dönüşümü + Python ile oda envanteri & **oda alanları** (geodezik) çıkarımı,
2. glTF üretip three.js'te basit bir otomatik oda yürüyüşü,
3. Üstüne Remotion ile oda isimli kartlar + TTS taslağı.

Bu, tüm ürünün en riskli ve en değerli iddiasını (fotoğrafsız, resmî veriden gerçek iç mekân turu) tek hamlede kanıtlar. Başlayalım mı — ilk adım olarak GML'den oda envanteri + alan hesabını mı çıkarayım?
