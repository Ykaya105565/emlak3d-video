"""
Türkiye'deki tüm yaygın CRS'leri destekleyen EPSG tespit modülü.

GML srsName özniteliğinden veya koordinat büyüklüğünden EPSG kodu çıkarır.
Asla sabit koordinat/şehir kullanmaz — tüm bilgi GML'den gelir.

Desteklenen sistemler:
  TUREF / ITRF96 TM (ulusal TAKBİS/MAKS standardı)
    EPSG:5253 = TUREF / TM27   (dil. 27°E; Batı Trakya, Ege)
    EPSG:5254 = TUREF / TM30   (dil. 30°E; Marmara, Orta Ege)
    EPSG:5255 = TUREF / TM33   (dil. 33°E; İç Anadolu Batı)
    EPSG:5256 = TUREF / TM36   (dil. 36°E; İç Anadolu Orta)
    EPSG:5257 = TUREF / TM39   (dil. 39°E; İç-Doğu Anadolu)
    EPSG:5258 = TUREF / TM42   (dil. 42°E; Doğu Anadolu)
    EPSG:5259 = TUREF / TM45   (dil. 45°E; Güneydoğu + Van)
  WGS84 UTM (uluslararası GPS)
    EPSG:32635 = UTM 35N, EPSG:32636 = UTM 36N
    EPSG:32637 = UTM 37N, EPSG:32638 = UTM 38N
  ED50 UTM (eski kadastro)
    EPSG:23035-23038
  Coğrafi (derece)
    EPSG:4326 (WGS84), EPSG:4258 (ETRS89)
"""

from __future__ import annotations
import re
from typing import Optional
from loguru import logger

# ────────────────────────────────────────────────────────────────────────────
# Easting aralıklarına göre TUREF/TM dilim tespiti
# (TAKBİS veri setlerinde gözlemlenen tipik sınırlar)
# ────────────────────────────────────────────────────────────────────────────
_TUREF_ZONES = [
    # (east_min, east_max, epsg, zone_name)
    (120_000, 580_000, 5253, "TUREF/TM27"),
    (270_000, 730_000, 5254, "TUREF/TM30"),
    (420_000, 880_000, 5255, "TUREF/TM33"),
    (570_000, 1_030_000, 5256, "TUREF/TM36"),
    (720_000, 1_180_000, 5257, "TUREF/TM39"),
    (870_000, 1_330_000, 5258, "TUREF/TM42"),
    (1_020_000, 1_480_000, 5259, "TUREF/TM45"),
]

_WGS84_UTM_ZONES = [
    (120_000, 580_000, 32635, "WGS84/UTM35N"),
    (270_000, 730_000, 32636, "WGS84/UTM36N"),
    (420_000, 880_000, 32637, "WGS84/UTM37N"),
    (570_000, 1_030_000, 32638, "WGS84/UTM38N"),
]

_ED50_UTM_ZONES = [
    (120_000, 580_000, 23035, "ED50/UTM35N"),
    (270_000, 730_000, 23036, "ED50/UTM36N"),
    (420_000, 880_000, 23037, "ED50/UTM37N"),
    (570_000, 1_030_000, 23038, "ED50/UTM38N"),
]

# EPSG → İnsan okunur isim
EPSG_NAMES: dict[int, str] = {}
for _lst in (_TUREF_ZONES, _WGS84_UTM_ZONES, _ED50_UTM_ZONES):
    for *_, _epsg, _name in _lst:
        EPSG_NAMES[_epsg] = _name
EPSG_NAMES.update({4326: "WGS84", 4258: "ETRS89", 3857: "WebMercator"})


# ────────────────────────────────────────────────────────────────────────────
# srsName → EPSG
# ────────────────────────────────────────────────────────────────────────────

def epsg_from_srs_name(srs_name: str) -> Optional[int]:
    """
    GML srsName özniteliğinden EPSG kodu döndür.

    Örnekler:
      'urn:ogc:def:crs:EPSG::5254'   → 5254
      'EPSG:5254'                     → 5254
      'urn:ogc:def:crs:EPSG:6.6:4326'→ 4326
      'http://...epsg.org/.../5254'   → 5254
      'urn:ogc:def:crs:TUREF::TM30'  → 5254  (özel eşleştirme)
      ''                              → None
    """
    if not srs_name:
        return None

    srs = srs_name.strip()

    # 1. Doğrudan EPSG:NNNN
    m = re.search(r"EPSG[:\/](\d{4,5})", srs, re.IGNORECASE)
    if m:
        return int(m.group(1))

    # 2. URN formatı: urn:ogc:def:crs:EPSG::NNNN
    m = re.search(r"epsg[:\s]+(\d{4,5})", srs, re.IGNORECASE)
    if m:
        return int(m.group(1))

    # 3. HTTP URI'de rakam: .../5254
    m = re.search(r"/(\d{4,5})/?$", srs)
    if m:
        return int(m.group(1))

    # 4. TUREF TM## özel isimlendirmesi
    turef_map = {
        "TM27": 5253, "TM30": 5254, "TM33": 5255,
        "TM36": 5256, "TM39": 5257, "TM42": 5258, "TM45": 5259,
    }
    m = re.search(r"TM(\d+)", srs, re.IGNORECASE)
    if m:
        key = f"TM{m.group(1)}"
        if key in turef_map:
            return turef_map[key]

    # 5. "CRS84" = WGS84 (bazı GML üreticileri)
    if "CRS84" in srs.upper() or "WGS84" in srs.upper():
        return 4326

    logger.warning(f"srsName tanınamadı: '{srs_name}' — koordinat büyüklüğünden çıkarım yapılacak")
    return None


def epsg_from_coords(x: float, y: float) -> Optional[int]:
    """
    Koordinat büyüklüğünden EPSG tahmin et.
    x = easting (veya lng), y = northing (veya lat)
    """
    # WGS84 coğrafi (derece)
    if -180.0 <= x <= 180.0 and -90.0 <= y <= 90.0:
        return 4326

    # Türkiye metrici: northing 3.6M–4.8M, easting değişken
    TR_NORTH_MIN, TR_NORTH_MAX = 3_600_000, 4_800_000
    if TR_NORTH_MIN <= y <= TR_NORTH_MAX:
        # TUREF deneyelim
        for e_min, e_max, epsg, name in _TUREF_ZONES:
            if e_min <= x <= e_max:
                logger.info(f"Koordinat büyüklüğünden tahmin: {name} (EPSG:{epsg})")
                return epsg
        # WGS84 UTM
        for e_min, e_max, epsg, name in _WGS84_UTM_ZONES:
            if e_min <= x <= e_max:
                logger.info(f"Koordinat büyüklüğünden tahmin: {name} (EPSG:{epsg})")
                return epsg

    # Northing x'te, easting y'de olabilir (axis order farklılığı)
    if TR_NORTH_MIN <= x <= TR_NORTH_MAX:
        for e_min, e_max, epsg, name in _TUREF_ZONES:
            if e_min <= y <= e_max:
                logger.warning(f"Eksen sırası farklı görünüyor — {name} (EPSG:{epsg}) ters eksenle")
                return epsg

    return None


def resolve_crs(srs_name: str, sample_coords: Optional[list[float]] = None) -> tuple[Optional[int], str]:
    """
    srsName (ve isteğe bağlı örnek koordinat) → (epsg, açıklama).
    epsg=None → bilinmeyen (pipeline uyarı verir, devam eder).
    """
    epsg = epsg_from_srs_name(srs_name)
    if epsg:
        name = EPSG_NAMES.get(epsg, f"EPSG:{epsg}")
        logger.info(f"CRS: {name} (EPSG:{epsg}) — kaynak: srsName")
        return epsg, name

    if sample_coords and len(sample_coords) >= 2:
        epsg = epsg_from_coords(sample_coords[0], sample_coords[1])
        if epsg:
            name = EPSG_NAMES.get(epsg, f"EPSG:{epsg}")
            logger.warning(f"CRS srsName'den okunamadı; koordinat büyüklüğünden tahmin: {name}")
            return epsg, name

    logger.warning(
        f"CRS belirlenemedi (srsName='{srs_name}'). "
        "Veri WGS84 (derece) olarak yorumlanacak. Yanlış koordinat olabilir."
    )
    return None, "Bilinmeyen"


def make_transformer(epsg: Optional[int]):
    """
    EPSG → WGS84 (EPSG:4326) dönüştürücü.
    epsg=None veya 4326 → identity transform.
    """
    from pyproj import Transformer
    if epsg is None or epsg == 4326:
        return None
    try:
        return Transformer.from_crs(f"EPSG:{epsg}", "EPSG:4326", always_xy=True)
    except Exception as e:
        logger.error(f"Transformer oluşturulamadı EPSG:{epsg} → 4326: {e}")
        return None


def to_wgs84(x: float, y: float, transformer) -> tuple[float, float]:
    """(x, y) → (lng, lat) WGS84."""
    if transformer is None:
        return x, y
    try:
        lng, lat = transformer.transform(x, y)
        return lng, lat
    except Exception:
        return x, y
