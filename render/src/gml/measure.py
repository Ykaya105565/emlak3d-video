"""
Oda envanterinden istatistikler türet.
Bağımsız bölüm net alanı, kat planı özeti, anlatım metni için veri hazırlığı.
"""
from __future__ import annotations
from typing import Optional


def summarize_inventory(inventory: dict) -> dict:
    rooms = inventory.get("rooms", [])
    sections = inventory.get("independent_sections", [])

    floor_map: dict[int, list[dict]] = {}
    for r in rooms:
        fl = r.get("floor", 0)
        floor_map.setdefault(fl, []).append(r)

    total_area = sum(r.get("area_m2", 0) for r in rooms)
    avg_room = total_area / len(rooms) if rooms else 0

    floor_summaries = []
    for fl in sorted(floor_map.keys()):
        fl_rooms = floor_map[fl]
        fl_area = sum(r.get("area_m2", 0) for r in fl_rooms)
        floor_summaries.append({
            "floor": fl,
            "room_count": len(fl_rooms),
            "total_area_m2": round(fl_area, 2),
            "room_names": [r["name"] for r in fl_rooms],
        })

    section_summaries = []
    for sec in sections:
        sec_rooms = [r for r in rooms if r.get("independent_section_id") == sec["id"]]
        usage_list = [r["name"] for r in sec_rooms]
        section_summaries.append({
            "id": sec["id"],
            "total_area_m2": sec["total_area_m2"],
            "room_count": len(sec_rooms),
            "room_names": usage_list,
        })

    return {
        "total_area_m2": round(total_area, 2),
        "avg_room_area_m2": round(avg_room, 2),
        "floor_count": len(floor_map),
        "total_room_count": len(rooms),
        "section_count": len(sections),
        "floors": floor_summaries,
        "sections": section_summaries,
    }


def build_narration_data(inventory: dict, listing_data: Optional[dict] = None) -> dict:
    """
    Senaryo üretimi için Claude'a gönderilecek yapılandırılmış veriyi hazırla.
    """
    summary = summarize_inventory(inventory)
    rooms = inventory.get("rooms", [])

    # Oda türü sayımı
    usage_counts: dict[str, int] = {}
    for r in rooms:
        usage = r.get("usage") or r.get("name", "Oda")
        usage_counts[usage] = usage_counts.get(usage, 0) + 1

    # Otomatik tur sırası: giriş önce, yaşam alanları ortada, banyolar sonda
    PRIORITY = {
        "Hol": 0, "Koridor": 1, "Salon": 2,
        "Mutfak": 3, "Kiler": 4,
        "Oda": 5, "Yatak Odası": 5, "Çocuk Odası": 5,
        "Balkon": 6, "Teras": 6,
        "Banyo": 7, "WC": 8,
        "Merdiven": 9, "Depo": 10,
    }
    sorted_rooms = sorted(rooms, key=lambda r: PRIORITY.get(r.get("usage") or r.get("name", ""), 5))

    return {
        "summary": summary,
        "usage_counts": usage_counts,
        "tour_order": [{"id": r["id"], "name": r["name"], "area_m2": r["area_m2"]} for r in sorted_rooms],
        "listing_data": listing_data or {},
    }
