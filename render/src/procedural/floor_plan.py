"""
Prosedürel Kat Planı Üretici.

Emlakçı girdilerinden (oda tipi, alan, kat sayısı vb.) gerçekçi kat planı oluşturur.

Çıktı formatı:
{
    "apartment_width": float,   # metre
    "apartment_depth": float,   # metre
    "rooms": [
        {
            "name": "Salon",
            "type": "salon",
            "area_m2": 28.0,
            "x": 0.0, "y": 0.0,     # sol-üst köşe (metre)
            "width": 7.0,            # metre
            "depth": 4.0,            # metre
            "color": (r, g, b),
            "furniture": ["kanepe", "tv_ünitesi"]
        }, ...
    ],
    "room_type": "3+1",
    "gross_area": 120,
    "net_area": 102,
    "current_floor": 5,
    "total_floors": 8,
    "has_balcony": True,
    "facade": "Güney-Batı",
    "title": "Deniz Manzaralı 3+1"
}
"""

from __future__ import annotations
import math
import random
from typing import Optional

# ── Renk paleti (oda tipine göre) ───────────────────────────────────────────
ROOM_COLORS = {
    "salon":       (100, 140, 230),
    "yatak":       (130, 110, 200),
    "mutfak":      ( 80, 190, 120),
    "banyo":       ( 60, 190, 190),
    "wc":          ( 50, 170, 200),
    "hol":         (140, 145, 160),
    "koridor":     (130, 135, 155),
    "balkon":      (100, 210, 140),
    "kiler":       (170, 145, 110),
    "antre":       (150, 150, 165),
}

# ── Mobilya listesi (oda tipine göre) ───────────────────────────────────────
ROOM_FURNITURE = {
    "salon":   ["kanepe", "tv_ünitesi", "sehpa", "koltuk"],
    "yatak":   ["yatak", "komodin", "dolap"],
    "mutfak":  ["tezgah", "ocak", "buzdolabı", "masa"],
    "banyo":   ["küvet", "lavabo", "klozet"],
    "wc":      ["klozet", "lavabo"],
    "hol":     ["ayakkabılık", "portmanto"],
    "balkon":  ["sandalye", "saksı"],
    "kiler":   ["raf"],
    "antre":   ["ayakkabılık"],
}


def parse_room_type(room_type: str) -> tuple[int, int]:
    """
    '3+1' → (3 yatak, 1 salon)
    'Stüdyo' → (0 yatak, 1 salon/açık alan)
    """
    rt = room_type.strip().lower()
    if rt in ("stüdyo", "studio"):
        return (0, 1)

    parts = rt.replace(" ", "").split("+")
    if len(parts) == 2:
        try:
            return (int(parts[0]), int(parts[1]))
        except ValueError:
            pass
    return (2, 1)  # fallback


def generate_floor_plan(
    room_type: str = "3+1",
    gross_area: float = 120.0,
    net_area: Optional[float] = None,
    current_floor: int = 3,
    total_floors: int = 8,
    bathrooms: int = 1,
    has_balcony: bool = True,
    facade: str = "Güney",
    building_age: int = 0,
    title: str = "",
) -> dict:
    """Emlakçı girdilerinden prosedürel kat planı üret."""

    bedrooms, salons = parse_room_type(room_type)
    if net_area is None or net_area <= 0:
        net_area = gross_area * 0.85

    # ── Oda alanlarını belirle ──────────────────────────────────────────────
    room_specs = _allocate_rooms(bedrooms, salons, bathrooms, has_balcony, net_area)

    # ── Daire boyutlarını belirle ───────────────────────────────────────────
    aspect = 1.35  # genişlik/derinlik oranı
    apt_depth = math.sqrt(net_area / aspect)
    apt_width = net_area / apt_depth

    # ── Odaları yerleştir ───────────────────────────────────────────────────
    rooms = _position_rooms(room_specs, apt_width, apt_depth)

    return {
        "apartment_width": round(apt_width, 2),
        "apartment_depth": round(apt_depth, 2),
        "rooms": rooms,
        "room_type": room_type,
        "gross_area": gross_area,
        "net_area": round(net_area, 1),
        "current_floor": current_floor,
        "total_floors": total_floors,
        "bathrooms": bathrooms,
        "has_balcony": has_balcony,
        "facade": facade,
        "building_age": building_age,
        "title": title or f"{room_type} Daire",
    }


def _allocate_rooms(
    bedrooms: int, salons: int, bathrooms: int, has_balcony: bool, net_area: float
) -> list[dict]:
    """Oda tiplerini ve hedef alanlarını belirle."""
    specs = []

    # Antre / Hol (giriş)
    specs.append({"name": "Antre", "type": "antre", "pct": 0.04})

    # Hol / Koridor
    specs.append({"name": "Hol", "type": "hol", "pct": 0.07})

    # Salon(lar)
    salon_pct = 0.24 if salons >= 1 else 0.0
    if salons >= 1:
        specs.append({"name": "Salon", "type": "salon", "pct": salon_pct})
    if salons >= 2:
        specs.append({"name": "Oturma Odası", "type": "salon", "pct": 0.15})

    # Mutfak
    specs.append({"name": "Mutfak", "type": "mutfak", "pct": 0.11})

    # Yatak odaları
    if bedrooms == 0:
        # Stüdyo — salon zaten büyük
        pass
    else:
        bedroom_pcts = _bedroom_pcts(bedrooms)
        for i, pct in enumerate(bedroom_pcts):
            name = "Yatak Odası" if i == 0 else f"Yatak Odası {i+1}"
            if bedrooms > 2 and i == bedrooms - 1:
                name = "Çocuk Odası"
            specs.append({"name": name, "type": "yatak", "pct": pct})

    # Banyo(lar)
    for i in range(max(1, bathrooms)):
        bname = "Banyo" if i == 0 else f"Banyo {i+1}"
        specs.append({"name": bname, "type": "banyo", "pct": 0.045})

    # WC (2+ yatak odası varsa)
    if bedrooms >= 2:
        specs.append({"name": "WC", "type": "wc", "pct": 0.025})

    # Balkon
    if has_balcony:
        specs.append({"name": "Balkon", "type": "balkon", "pct": 0.04})

    # Oranları normalize et → gerçek alan
    total_pct = sum(s["pct"] for s in specs)
    for s in specs:
        s["area_m2"] = round((s["pct"] / total_pct) * net_area, 1)
        # Minimum alan kontrolleri
        if s["type"] == "wc":
            s["area_m2"] = max(s["area_m2"], 2.5)
        elif s["type"] == "banyo":
            s["area_m2"] = max(s["area_m2"], 4.0)
        elif s["type"] == "antre":
            s["area_m2"] = max(s["area_m2"], 3.0)

    return specs


def _bedroom_pcts(n: int) -> list[float]:
    """n yatak odası için yüzde dağılımı."""
    if n == 1:
        return [0.14]
    elif n == 2:
        return [0.14, 0.11]
    elif n == 3:
        return [0.14, 0.11, 0.10]
    elif n == 4:
        return [0.13, 0.11, 0.10, 0.09]
    else:
        base = [0.12, 0.11, 0.10, 0.09]
        extra = [0.08] * (n - 4)
        return base + extra


def _position_rooms(specs: list[dict], apt_w: float, apt_d: float) -> list[dict]:
    """
    Odaları dikdörtgen grid'e yerleştir.

    Strateji:
      Satır 1 (üst):    Salon + Balkon
      Satır 2 (orta):   Mutfak + Hol + Yatak-1
      Satır 3 (alt):    Banyo/WC + Antre + diğer yatak odaları

    Her oda (x, y, width, depth) alır — sol-üst köşeden.
    """
    rooms = []

    # Odaları tipine göre grupla
    by_type = {}
    for s in specs:
        by_type.setdefault(s["type"], []).append(s)

    salons = by_type.get("salon", [])
    yataks = by_type.get("yatak", [])
    mutfak = by_type.get("mutfak", [{}])[0]
    banyos = by_type.get("banyo", [])
    wcs = by_type.get("wc", [])
    hol = by_type.get("hol", [{}])[0]
    antre = by_type.get("antre", [{}])[0]
    balkon = by_type.get("balkon", [])
    kiler = by_type.get("kiler", [])

    # ── 3 satır yükseklikleri ───────────────────────────────────────────────
    total_bedrooms = len(yataks)

    if total_bedrooms <= 1:
        row_heights = [apt_d * 0.45, apt_d * 0.30, apt_d * 0.25]
    elif total_bedrooms <= 3:
        row_heights = [apt_d * 0.38, apt_d * 0.32, apt_d * 0.30]
    else:
        row_heights = [apt_d * 0.33, apt_d * 0.34, apt_d * 0.33]

    y_offsets = [0.0, row_heights[0], row_heights[0] + row_heights[1]]

    # ── Satır 1: Salon + Balkon ─────────────────────────────────────────────
    y1, h1 = y_offsets[0], row_heights[0]

    if salons:
        salon_w = apt_w * 0.72 if balkon else apt_w
        rooms.append(_make_room(
            salons[0], x=0, y=y1, width=salon_w, depth=h1
        ))
        if balkon:
            rooms.append(_make_room(
                balkon[0], x=salon_w, y=y1, width=apt_w - salon_w, depth=h1
            ))
    elif not salons and balkon:
        # Stüdyo + balkon
        rooms.append(_make_room(
            {"name": "Yaşam Alanı", "type": "salon", "area_m2": h1 * apt_w * 0.72},
            x=0, y=y1, width=apt_w * 0.72, depth=h1
        ))
        rooms.append(_make_room(
            balkon[0], x=apt_w * 0.72, y=y1, width=apt_w * 0.28, depth=h1
        ))

    if len(salons) > 1:
        # 2. salon (oturma odası) — satır 1'in geri kalanına
        pass  # Salon 2 aşağıda ele alınır

    # ── Satır 2: Mutfak + Hol + Yatak-1 ────────────────────────────────────
    y2, h2 = y_offsets[1], row_heights[1]

    col2_widths = _split_row(apt_w, 3, [0.30, 0.25, 0.45])

    if mutfak.get("name"):
        rooms.append(_make_room(
            mutfak, x=0, y=y2, width=col2_widths[0], depth=h2
        ))

    if hol.get("name"):
        rooms.append(_make_room(
            hol, x=col2_widths[0], y=y2, width=col2_widths[1], depth=h2
        ))

    if yataks:
        rooms.append(_make_room(
            yataks[0], x=col2_widths[0] + col2_widths[1], y=y2,
            width=col2_widths[2], depth=h2
        ))

    # ── Satır 3: Servis + diğer yatak odaları ──────────────────────────────
    y3, h3 = y_offsets[2], row_heights[2]

    service_rooms = []
    if antre.get("name"):
        service_rooms.append(antre)
    service_rooms.extend(banyos)
    service_rooms.extend(wcs)
    service_rooms.extend(kiler)

    remaining_bedrooms = yataks[1:] if len(yataks) > 1 else []

    # 2. salon varsa ekle
    if len(salons) > 1:
        remaining_bedrooms.insert(0, salons[1])

    all_row3 = service_rooms + remaining_bedrooms
    n_cols = max(len(all_row3), 1)

    # Servis odaları küçük, yatak odaları büyük
    weights = []
    for r in all_row3:
        if r.get("type") in ("wc", "antre"):
            weights.append(0.6)
        elif r.get("type") in ("banyo", "kiler"):
            weights.append(0.8)
        else:
            weights.append(1.2)

    total_w = sum(weights)
    col3_widths = [(w / total_w) * apt_w for w in weights]

    x_offset = 0.0
    for i, r in enumerate(all_row3):
        rooms.append(_make_room(
            r, x=x_offset, y=y3, width=col3_widths[i], depth=h3
        ))
        x_offset += col3_widths[i]

    return rooms


def _make_room(spec: dict, x: float, y: float, width: float, depth: float) -> dict:
    """Oda dict'i oluştur."""
    rtype = spec.get("type", "hol")
    name = spec.get("name", "Oda")
    area = round(width * depth, 1)  # gerçek yerleşim alanı

    return {
        "name": name,
        "type": rtype,
        "area_m2": area,
        "x": round(x, 2),
        "y": round(y, 2),
        "width": round(width, 2),
        "depth": round(depth, 2),
        "color": ROOM_COLORS.get(rtype, (140, 140, 160)),
        "furniture": ROOM_FURNITURE.get(rtype, []),
    }


def _split_row(total: float, n: int, ratios: list[float]) -> list[float]:
    """Bir satırı oranlarla böl."""
    s = sum(ratios[:n])
    return [(r / s) * total for r in ratios[:n]]


# ── Tur sırası ──────────────────────────────────────────────────────────────
TOUR_ORDER = {
    "antre": 0, "hol": 1, "koridor": 2, "salon": 3, "mutfak": 4,
    "yatak": 5, "banyo": 6, "wc": 7, "balkon": 8, "kiler": 9,
}

def get_tour_order(rooms: list[dict]) -> list[dict]:
    """Tur sırasına göre odaları sırala."""
    return sorted(rooms, key=lambda r: (
        TOUR_ORDER.get(r["type"], 5),
        r.get("y", 0),
        r.get("x", 0),
    ))
