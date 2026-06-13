"""
CityGML LoD4 → oda envanteri (JSON).

ÖNEMLİ ULUSAL İLKELER:
  - Koordinatlar GML'den dinamik okunur; hardcode yok.
  - EPSG srsName'den okunur; bilinmiyorsa büyüklükten tahmin edilir.
  - Tüm Türkiye TUREF dilimlerini (TM27-TM45) + WGS84/ED50 UTM'i destekler.
  - Bilinmeyen SRS → hata değil, net uyarı + devam.

Çıktı şeması:
{
  "source_file": "...",
  "crs": "TUREF/TM30",
  "epsg": 5254,
  "buildings": [...],           # bina meta
  "building_centroid_wgs84": [lat, lng],
  "building_bbox_local": {...}, # metre cinsinden yerel koordinat
  "rooms": [
    {
      "id": "...",
      "name": "Salon",
      "usage": "Salon",
      "floor": 0,
      "area_m2": 23.4,
      "centroid_wgs84": [lat, lng, z],
      "centroid_local_m": [x_m, y_m, z_m],
      "polygon_local_m": [[x,y,z], ...],
      "polygon_wgs84": [[lat,lng,z], ...],
      "independent_section_id": "..."
    }
  ],
  "independent_sections": [...],
  "room_count": N,
  "section_count": N
}
"""

from __future__ import annotations
import re
from pathlib import Path
from typing import Optional

import numpy as np
from lxml import etree
from shapely.geometry import Polygon
from loguru import logger

from .srs_utils import epsg_from_srs_name, epsg_from_coords, make_transformer, to_wgs84, EPSG_NAMES

# XML ad alanları
NS = {
    "gml": "http://www.opengis.net/gml",
    "gml32": "http://www.opengis.net/gml/3.2",
    "bldg": "http://www.opengis.net/citygml/building/2.0",
    "bldg3": "http://www.opengis.net/citygml/building/3.0",
    "gen": "http://www.opengis.net/citygml/generics/2.0",
    "core": "http://www.opengis.net/citygml/2.0",
}

# partUsage / usage kodu → Türkçe oda tipi
PART_USAGE = {
    "1000": "Oda",         "1010": "Salon",       "1020": "Yatak Odası",
    "1030": "Çocuk Odası", "1040": "Banyo",        "1050": "WC",
    "1060": "Hol",         "1070": "Koridor",      "1080": "Mutfak",
    "1090": "Kiler",       "1100": "Balkon",        "1110": "Teras",
    "1120": "Merdiven",    "1130": "Garaj",         "1140": "Isı Merkezi",
    "1150": "Depo",        "1160": "Ortak Alan",    "1170": "Ofis",
    "1180": "Teknik Hacim","1190": "Sığınak",
    # Ek TAKBİS kodları
    "2000": "Dükkan",      "2010": "Depo",         "2020": "Ofis",
    "3000": "Otopark",
}

CEILING_H = 2.80  # varsayılan kat yüksekliği (m)


def _iter_elements(el):
    """lxml comment/PI düğümlerini atlayarak gerçek elementleri döndür."""
    for child in el.iter():
        if isinstance(child.tag, str):
            yield child


# ─────────────────────────────────────────────────────────────────────────────
#  Ana giriş noktası
# ─────────────────────────────────────────────────────────────────────────────

def parse_gml_file(gml_path: str) -> dict:
    path = Path(gml_path)
    if not path.exists():
        raise FileNotFoundError(f"GML dosyası bulunamadı: {gml_path}")

    logger.info(f"GML parse başlıyor: {path.name} ({path.stat().st_size/1024:.1f} KB)")

    tree = etree.parse(str(path))
    root = tree.getroot()

    # 1. CRS tespit
    epsg, crs_name, transformer = _detect_crs(root)

    # 2. Üst seviye bina elementlerini bul (BuildingPart alt eleman olarak SAYILMAYACAk)
    bldg_els = root.findall(".//bldg:Building", NS)
    if not bldg_els:
        # CityGML 3.0 denemesi
        bldg_els = root.findall(".//{http://www.opengis.net/citygml/building/3.0}Building")
    if not bldg_els:
        # Yalnızca BuildingPart varsa (kök seviye parçalar)
        bldg_els = root.findall(".//bldg:BuildingPart", NS)

    logger.info(f"Bina/bölüm elemanı: {len(bldg_els)}")

    # 3. Tüm oda koordinatlarını topla (yerel koordinat için merkez gerekli)
    all_epsg_coords: list[tuple[float, float]] = []
    raw_rooms: list[dict] = []
    section_map: dict[str, list[str]] = {}

    seen_room_ids: set[str] = set()  # çoklama önleme
    for bldg_el in bldg_els:
        rooms, secs, epsg_pts = _parse_building(bldg_el, epsg)
        for r in rooms:
            if r.get("id") and r["id"] not in seen_room_ids:
                seen_room_ids.add(r["id"])
                raw_rooms.append(r)
            elif not r.get("id"):
                raw_rooms.append(r)
        for k, v in secs.items():
            section_map.setdefault(k, []).extend(v)
        all_epsg_coords.extend(epsg_pts)

    if not raw_rooms:
        logger.warning("Oda elementi bulunamadı — GML yapısı beklenenden farklı olabilir")

    # 4. Yerel koordinat sistemi (bina merkezi = 0,0)
    bldg_center_epsg = _centroid_of_points(all_epsg_coords) if all_epsg_coords else (0.0, 0.0)
    bldg_center_wgs84 = _to_wgs84_pair(bldg_center_epsg[0], bldg_center_epsg[1], transformer)

    # 5. Odaları zenginleştir (local coords + WGS84)
    rooms_out = []
    for r in raw_rooms:
        poly_epsg = r.pop("_poly_epsg", [])
        centroid_epsg = r.pop("_centroid_epsg", [bldg_center_epsg[0], bldg_center_epsg[1], 0.0])

        poly_local = _to_local(poly_epsg, bldg_center_epsg)
        centroid_local = (
            centroid_epsg[0] - bldg_center_epsg[0],
            centroid_epsg[1] - bldg_center_epsg[1],
            centroid_epsg[2] if len(centroid_epsg) > 2 else 0.0,
        )
        poly_wgs84 = [
            list(_to_wgs84_pair(p[0], p[1], transformer)) + [p[2] if len(p) > 2 else 0.0]
            for p in poly_epsg
        ]
        centroid_wgs84 = list(_to_wgs84_pair(centroid_epsg[0], centroid_epsg[1], transformer)) + [
            centroid_epsg[2] if len(centroid_epsg) > 2 else 0.0
        ]

        r["polygon_local_m"] = [[round(v, 4) for v in p] for p in poly_local]
        r["polygon_wgs84"] = [[round(v, 8) for v in p] for p in poly_wgs84]
        r["centroid_local_m"] = [round(centroid_local[0], 4), round(centroid_local[1], 4), round(centroid_local[2], 4)]
        r["centroid_wgs84"] = [round(centroid_wgs84[0], 8), round(centroid_wgs84[1], 8), round(centroid_wgs84[2], 4)]
        rooms_out.append(r)

    # 6. Bağımsız bölüm alanlarını hesapla
    sections_out = []
    for sec_id, room_ids in section_map.items():
        sec_rooms = [r for r in rooms_out if r.get("independent_section_id") == sec_id]
        sections_out.append({
            "id": sec_id,
            "rooms": list(set(room_ids)),
            "total_area_m2": round(sum(r["area_m2"] for r in sec_rooms), 2),
            "room_count": len(sec_rooms),
        })

    # 7. Bounding box (yerel metre)
    all_local_pts = [p for r in rooms_out for p in r["polygon_local_m"] if p]
    bbox = _bbox(all_local_pts) if all_local_pts else {"min_x": 0, "max_x": 0, "min_y": 0, "max_y": 0}

    result = {
        "source_file": path.name,
        "crs": crs_name,
        "epsg": epsg,
        "building_centroid_wgs84": [round(bldg_center_wgs84[0], 8), round(bldg_center_wgs84[1], 8)],
        "building_bbox_local": bbox,
        "rooms": rooms_out,
        "independent_sections": sections_out,
        "room_count": len(rooms_out),
        "section_count": len(sections_out),
    }
    logger.info(
        f"Parse tamamlandı: {len(rooms_out)} oda, {len(sections_out)} bağımsız bölüm "
        f"— merkez WGS84: {bldg_center_wgs84[0]:.6f}, {bldg_center_wgs84[1]:.6f}"
    )
    return result


# ─────────────────────────────────────────────────────────────────────────────
#  CRS Tespit
# ─────────────────────────────────────────────────────────────────────────────

def _detect_crs(root: etree._Element):
    """GML kökundan EPSG, CRS adı ve transformer döndür."""
    srs_name = ""

    # 1. Envelope > srsName
    for el in _iter_elements(root):
        tag = etree.QName(el.tag).localname if el.tag else ""
        if tag == "Envelope":
            srs_name = el.get("srsName", "")
            if srs_name:
                break

    # 2. Herhangi bir geometry elementinde
    if not srs_name:
        for el in _iter_elements(root):
            sn = el.get("srsName", "")
            if sn:
                srs_name = sn
                break

    epsg = epsg_from_srs_name(srs_name) if srs_name else None

    # 3. Koordinat büyüklüğünden tahmin (ilk posList'ten)
    if epsg is None:
        sample = _first_pos_list(root)
        if sample and len(sample) >= 2:
            epsg = epsg_from_coords(sample[0], sample[1])

    crs_name = EPSG_NAMES.get(epsg, f"EPSG:{epsg}") if epsg else "Bilinmeyen"
    transformer = make_transformer(epsg)
    logger.info(f"CRS: {crs_name} (EPSG:{epsg}) — srsName='{srs_name}'")
    return epsg, crs_name, transformer


def _first_pos_list(root: etree._Element) -> Optional[list[float]]:
    for el in _iter_elements(root):
        tag = etree.QName(el.tag).localname if el.tag else ""
        if tag == "posList" and el.text:
            nums = el.text.split()[:6]
            return [float(n) for n in nums if _is_num(n)]
    return None


# ─────────────────────────────────────────────────────────────────────────────
#  Bina Parse
# ─────────────────────────────────────────────────────────────────────────────

def _parse_building(bldg_el: etree._Element, epsg: Optional[int]) -> tuple[list, dict, list]:
    """Bina elementinden oda listesi + bağımsız bölüm haritası + EPSG koordinatları döndür."""
    rooms: list[dict] = []
    sections: dict[str, list[str]] = {}
    all_pts: list[tuple[float, float]] = []

    # Bağımsız bölüm referanslarını topla
    section_refs: dict[str, str] = _collect_section_refs(bldg_el)
    for rid, sid in section_refs.items():
        sections.setdefault(sid, [])
        if rid not in sections[sid]:
            sections[sid].append(rid)

    # Oda elementlerini bul (çeşitli CityGML versiyonları)
    room_els = _find_room_elements(bldg_el)
    logger.debug(f"Bina altında {len(room_els)} oda elementi")

    for rm_el in room_els:
        room, pts = _parse_room_element(rm_el, section_refs)
        if room:
            rooms.append(room)
            all_pts.extend(pts)

    return rooms, sections, all_pts


def _find_room_elements(bldg_el: etree._Element) -> list[etree._Element]:
    """Tüm oda/bölüm elementlerini bul (CityGML 2.0 ve 3.0)."""
    found = []
    tags_to_find = {
        "Room", "BuildingRoom", "IntBuildingInstallation",
        "BuildingSpace",  # CityGML 3.0
    }
    for el in _iter_elements(bldg_el):
        tag = etree.QName(el.tag).localname if el.tag else ""
        if tag in tags_to_find:
            found.append(el)
    return found


def _collect_section_refs(bldg_el: etree._Element) -> dict[str, str]:
    """
    room_id → section_id eşleştirmesi.

    İki CityGML örüntüsü desteklenir:
      A. Standart: <bldg:Room> içinde <bldg:independentSection xlink:href="#BB-001"/>
      B. MAKS/TAKBİS: <bldg:BuildingPart> içinde <gen:stringAttribute name="bagimsizbölüm_no">
         Bu durumda o BuildingPart'ın tüm Room çocukları o bölüme atanır.
    """
    refs: dict[str, str] = {}

    # Örüntü A: independentSection referansları
    for el in _iter_elements(bldg_el):
        tag = etree.QName(el.tag).localname if el.tag else ""
        if "independentSection" in tag or "IndependentSection" in tag:
            parent = el.getparent()
            if parent is not None:
                rid = parent.get("{http://www.opengis.net/gml}id", "")
                sid = el.get("{http://www.w3.org/1999/xlink}href", "").lstrip("#")
                if rid and sid:
                    refs[rid] = sid

    # Örüntü B: BuildingPart ile gen:stringAttribute bagimsizbölüm_no
    for part_el in _iter_elements(bldg_el):
        part_tag = etree.QName(part_el.tag).localname if part_el.tag else ""
        if part_tag != "BuildingPart":
            continue
        # bagimsizbölüm_no ara
        bb_no = ""
        for attr_el in _iter_elements(part_el):
            attr_tag = etree.QName(attr_el.tag).localname if attr_el.tag else ""
            if attr_tag == "stringAttribute":
                name_attr = attr_el.get("name", "")
                if "bağımsızbölüm" in name_attr.lower() or "bagimsizbölüm" in name_attr.lower() or name_attr == "bagimsizbölüm_no":
                    val_el = attr_el.find(".//{http://www.opengis.net/citygml/generics/2.0}value")
                    if val_el is not None and val_el.text:
                        bb_no = val_el.text.strip()
                        break
            # Bölüm no bulunamadıysa BuildingPart gml:id'sini kullan
        if not bb_no:
            bb_no = part_el.get("{http://www.opengis.net/gml}id", "")
        if not bb_no:
            continue
        # Bu BuildingPart içindeki tüm Room'ları bu bölüme ata
        for room_el in _iter_elements(part_el):
            room_tag = etree.QName(room_el.tag).localname if room_el.tag else ""
            if room_tag in ("Room", "BuildingRoom", "BuildingSpace"):
                rid = room_el.get("{http://www.opengis.net/gml}id", "")
                if rid and rid not in refs:
                    refs[rid] = bb_no

    return refs


# ─────────────────────────────────────────────────────────────────────────────
#  Oda Parse
# ─────────────────────────────────────────────────────────────────────────────

def _parse_room_element(el: etree._Element, section_refs: dict) -> tuple[Optional[dict], list]:
    room_id = el.get("{http://www.opengis.net/gml}id", "")
    name = _get_attr_str(el, ["name", "Name", "adi", "Ad"])
    usage = _get_usage(el)
    floor = _get_floor(el)

    if not name:
        name = usage or "Oda"

    # Taban poligonu EPSG koordinatları
    poly_epsg = _extract_floor_polygon(el)
    if not poly_epsg:
        poly_epsg = _extract_any_polygon(el)

    # Alan hesabı (metre²)
    area_m2 = 0.0
    centroid_epsg = [0.0, 0.0, 0.0]
    if poly_epsg and len(poly_epsg) >= 3:
        area_m2, centroid_epsg = _area_and_centroid(poly_epsg)

    # Alan < 0.1 m² → muhtemelen hatalı geometri, yine de ekle ama uyar
    if 0 < area_m2 < 0.1:
        logger.warning(f"Çok küçük alan ({area_m2:.4f} m²) oda: {name} ({room_id})")

    room = {
        "id": room_id,
        "name": name,
        "usage": usage,
        "floor": floor,
        "area_m2": round(area_m2, 3),
        "independent_section_id": section_refs.get(room_id),
        "_poly_epsg": poly_epsg or [],
        "_centroid_epsg": centroid_epsg,
    }

    all_pts = [(p[0], p[1]) for p in poly_epsg] if poly_epsg else []
    return room, all_pts


def _get_attr_str(el: etree._Element, keys: list[str]) -> str:
    """gml:name veya gen:stringAttribute'tan değer oku."""
    # gml:name
    for ns in ("gml", "gml32"):
        name_el = el.find(f"{ns}:name", NS)
        if name_el is not None and name_el is not None and (name_el.text or "").strip():
            return name_el.text.strip()

    # gen:stringAttribute
    for attr in el.findall("gen:stringAttribute", NS):
        if attr.get("name", "").lower() in [k.lower() for k in keys]:
            val = attr.find("gen:value", NS)
            if val is not None and (val.text or "").strip():
                return val.text.strip()

    return ""


def _get_usage(el: etree._Element) -> str:
    for tag in ("bldg:usage", "bldg:partUsage", "bldg:function"):
        u = el.find(tag, NS)
        if u is not None and u.text:
            code = u.text.strip()
            return PART_USAGE.get(code, code)

    for attr in el.findall("gen:stringAttribute", NS):
        if attr.get("name", "").lower() in ("partusage", "usage", "kullanim", "function"):
            val = attr.find("gen:value", NS)
            if val is not None and val.text:
                return PART_USAGE.get(val.text.strip(), val.text.strip())

    return ""


def _get_floor(el: etree._Element) -> int:
    for attr in el.findall("gen:intAttribute", NS):
        if attr.get("name", "").lower() in ("floor", "kat", "storey", "level"):
            val = attr.find("gen:value", NS)
            if val is not None and val.text:
                try:
                    return int(val.text)
                except ValueError:
                    pass

    for attr in el.findall("gen:stringAttribute", NS):
        if attr.get("name", "").lower() in ("floor", "kat", "storey", "level"):
            val = attr.find("gen:value", NS)
            if val is not None and val.text:
                try:
                    return int(val.text)
                except ValueError:
                    pass

    return 0


# ─────────────────────────────────────────────────────────────────────────────
#  Poligon çıkarma
# ─────────────────────────────────────────────────────────────────────────────

def _extract_floor_polygon(el: etree._Element) -> Optional[list]:
    """Taban/zemin yüzeyini tercih et."""
    floor_tags = {"FloorSurface", "GroundSurface", "FloorSurface"}
    for sub in el.iter():
        tag = etree.QName(sub.tag).localname if sub.tag else ""
        if tag in floor_tags:
            coords = _coords_from_element(sub)
            if coords:
                return coords
    return None


def _extract_any_polygon(el: etree._Element) -> Optional[list]:
    """İlk geçerli poligonu döndür."""
    for poly in el.iter():
        tag = etree.QName(poly.tag).localname if poly.tag else ""
        if tag == "Polygon":
            coords = _coords_from_element(poly)
            if coords and len(coords) >= 3:
                return coords
    return None


def _coords_from_element(el: etree._Element) -> Optional[list]:
    """GML element içinden koordinat listesi çıkar."""
    # posList
    for sub in el.iter():
        tag = etree.QName(sub.tag).localname if sub.tag else ""
        if tag == "posList" and sub.text:
            return _parse_pos_list(sub.text)

    # pos (tekil noktalar)
    pts = []
    for sub in el.iter():
        tag = etree.QName(sub.tag).localname if sub.tag else ""
        if tag == "pos" and sub.text:
            nums = [float(x) for x in sub.text.split() if _is_num(x)]
            if len(nums) >= 2:
                pts.append(nums[:3] if len(nums) >= 3 else nums + [0.0])
    if len(pts) >= 3:
        return pts

    # coordinates (eski GML format)
    for sub in el.iter():
        tag = etree.QName(sub.tag).localname if sub.tag else ""
        if tag == "coordinates" and sub.text:
            return _parse_coordinates(sub.text)

    return None


def _parse_pos_list(text: str) -> Optional[list]:
    nums = [float(x) for x in text.split() if _is_num(x)]
    if len(nums) < 9:  # en az 3 nokta × 3 koordinat
        return None
    # Boyut tespiti: GML srsDimension=3 yaygın
    dim = 3 if len(nums) % 3 == 0 else 2
    return [nums[i:i+dim] for i in range(0, len(nums) - dim + 1, dim)]


def _parse_coordinates(text: str) -> Optional[list]:
    """Eski GML coordinates formatı: 'x,y,z x,y,z ...'"""
    pts = []
    for tok in text.strip().split():
        parts = tok.split(",")
        if len(parts) >= 2:
            try:
                nums = [float(p) for p in parts]
                pts.append(nums[:3] if len(nums) >= 3 else nums + [0.0])
            except ValueError:
                pass
    return pts if len(pts) >= 3 else None


def _is_num(s: str) -> bool:
    try:
        float(s)
        return True
    except (ValueError, TypeError):
        return False


# ─────────────────────────────────────────────────────────────────────────────
#  Geometri hesapları
# ─────────────────────────────────────────────────────────────────────────────

def _area_and_centroid(coords: list) -> tuple[float, list]:
    """
    EPSG koordinatlarından (metre cinsinden projeksiyon) m² alan ve ağırlık merkezi.
    Z koordinatı alana dahil edilmez.
    """
    xy = [(c[0], c[1]) for c in coords]
    try:
        poly = Polygon(xy)
        if not poly.is_valid:
            poly = poly.buffer(0)
        area = poly.area
        cx, cy = poly.centroid.x, poly.centroid.y
        mean_z = sum(c[2] if len(c) > 2 else 0.0 for c in coords) / len(coords)
        return area, [cx, cy, mean_z]
    except Exception as e:
        logger.warning(f"Alan hesabı hatası: {e}")
        return 0.0, [coords[0][0] if coords else 0.0, coords[0][1] if coords else 0.0, 0.0]


def _centroid_of_points(pts: list[tuple[float, float]]) -> tuple[float, float]:
    if not pts:
        return 0.0, 0.0
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return sum(xs) / len(xs), sum(ys) / len(ys)


def _to_wgs84_pair(x: float, y: float, transformer) -> tuple[float, float]:
    """EPSG projektif → (lat, lng) WGS84."""
    if transformer is None:
        return y, x  # zaten WGS84 → lat=y, lng=x
    try:
        lng, lat = transformer.transform(x, y)
        return lat, lng
    except Exception:
        return y, x


def _to_local(poly_epsg: list, center_epsg: tuple[float, float]) -> list:
    """
    EPSG koordinatlarını bina merkezine göre yerel metre koordinatına çevir.
    Bu koordinatlar 3D modelde kullanılır.
    """
    cx, cy = center_epsg
    result = []
    for p in poly_epsg:
        x = p[0] - cx
        y = p[1] - cy
        z = p[2] if len(p) > 2 else 0.0
        result.append([round(x, 4), round(y, 4), round(z, 4)])
    return result


def _bbox(pts: list) -> dict:
    if not pts:
        return {"min_x": 0, "max_x": 0, "min_y": 0, "max_y": 0, "width_m": 0, "height_m": 0}
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return {
        "min_x": round(min(xs), 2), "max_x": round(max(xs), 2),
        "min_y": round(min(ys), 2), "max_y": round(max(ys), 2),
        "width_m": round(max(xs) - min(xs), 2),
        "height_m": round(max(ys) - min(ys), 2),
    }


if __name__ == "__main__":
    import sys, json
    if len(sys.argv) < 2:
        print("Kullanım: python parse.py <dosya.gml>")
        sys.exit(1)
    inv = parse_gml_file(sys.argv[1])
    print(json.dumps(inv, ensure_ascii=False, indent=2))
