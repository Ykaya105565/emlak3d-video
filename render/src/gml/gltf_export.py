"""
CityGML oda envanteri → glTF 2.0 (.glb) dışa aktarımı.

Koordinatlar: local_m (bina merkezi = 0,0 — metre cinsinden).
Her oda ayrı mesh + isimlendirilmiş node.
Kaplama basit temsili renkler (gerçek doku değil).
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Optional

import numpy as np
from loguru import logger
from shapely.geometry import Polygon, MultiPolygon
from shapely.validation import make_valid

CEILING_H = 2.80  # m

# Oda tipine göre RGB (0-1 float)
ROOM_COLORS: dict[str, tuple[float, float, float]] = {
    "Salon":        (0.95, 0.90, 0.75),
    "Yatak Odası":  (0.80, 0.85, 0.95),
    "Çocuk Odası":  (0.95, 0.88, 0.78),
    "Mutfak":       (0.88, 0.95, 0.82),
    "Banyo":        (0.78, 0.92, 0.95),
    "WC":           (0.82, 0.95, 0.90),
    "Hol":          (0.88, 0.88, 0.88),
    "Koridor":      (0.84, 0.84, 0.84),
    "Balkon":       (0.84, 0.95, 0.80),
    "Teras":        (0.82, 0.95, 0.78),
    "Kiler":        (0.88, 0.82, 0.75),
    "Merdiven":     (0.82, 0.82, 0.88),
    "Garaj":        (0.75, 0.80, 0.80),
    "Depo":         (0.78, 0.78, 0.78),
    "Isı Merkezi":  (0.80, 0.75, 0.75),
}
DEFAULT_COLOR = (0.85, 0.85, 0.85)


def export_gltf(inventory: dict, output_path: str) -> str:
    """
    Oda envanterini glTF binary (.glb) dosyasına yazar.
    Döndürür: yazılan dosya yolu.
    """
    try:
        import trimesh
        from trimesh.transformations import translation_matrix
    except ImportError:
        raise RuntimeError(
            "trimesh kurulu değil. Kurulum: pip install trimesh"
        )

    rooms = inventory.get("rooms", [])
    if not rooms:
        raise ValueError("Oda envanteri boş — glTF üretilemez")

    scene = trimesh.Scene()
    floor_z_offsets: dict[int, float] = {}  # kat → Z başlangıcı

    for room in rooms:
        fl = room.get("floor", 0)
        # Kat Z ofseti: kat * (tavan_yüksekliği + döşeme)
        z_base = fl * (CEILING_H + 0.2)
        floor_z_offsets[fl] = z_base

        mesh = _room_to_mesh(room, z_base, trimesh)
        if mesh is not None:
            node_name = f"{room['name']}_{room['id'][-8:]}"
            scene.add_geometry(mesh, node_name=node_name, geom_name=room["id"])

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    scene.export(str(out))
    size_kb = out.stat().st_size / 1024
    logger.info(f"glTF dışa aktarıldı: {out} ({size_kb:.1f} KB, {len(rooms)} oda)")
    return str(out)


def _room_to_mesh(room: dict, z_base: float, trimesh):
    """Oda → 3D mesh (extruded polygon veya box fallback)."""
    name = room.get("name", "Oda")
    usage = room.get("usage", name)
    r, g, b = ROOM_COLORS.get(usage, ROOM_COLORS.get(name, DEFAULT_COLOR))
    color = [int(r * 255), int(g * 255), int(b * 255), 255]

    poly_local = room.get("polygon_local_m", [])
    if poly_local and len(poly_local) >= 3:
        mesh = _extrude_polygon(poly_local, z_base, trimesh)
        if mesh is not None:
            mesh.visual = trimesh.visual.color.ColorVisuals(
                vertex_colors=np.tile(color, (len(mesh.vertices), 1))
            )
            return mesh

    # Fallback: alandan hesaplanan kutu
    return _box_from_area(room.get("area_m2", 12.0), z_base, color, trimesh)


def _extrude_polygon(poly_local: list, z_base: float, trimesh):
    """
    Yerel koordinat taban poligonunu yukarı extrude eder.
    poly_local: [[x, y, z], ...] (z alana dahil değil)
    """
    try:
        xy = [(p[0], p[1]) for p in poly_local]
        shapely_poly = Polygon(xy)
        if not shapely_poly.is_valid:
            shapely_poly = make_valid(shapely_poly)
        if shapely_poly.is_empty or shapely_poly.area < 0.01:
            return None

        # Taban + tavan + duvarlar
        mesh = trimesh.creation.extrude_polygon(shapely_poly, CEILING_H)

        # Z ofseti uygula
        mat = np.eye(4)
        mat[2, 3] = z_base
        mesh.apply_transform(mat)
        return mesh
    except Exception as e:
        logger.debug(f"Polygon extrude hatası: {e}")
        return None


def _box_from_area(area_m2: float, z_base: float, color: list, trimesh):
    """Alandan kare kutu mesh oluştur."""
    try:
        side = max(1.0, area_m2 ** 0.5)
        box = trimesh.creation.box(extents=[side, side, CEILING_H])
        mat = np.eye(4)
        mat[2, 3] = z_base + CEILING_H / 2
        box.apply_transform(mat)
        box.visual = trimesh.visual.color.ColorVisuals(
            vertex_colors=np.tile(color, (len(box.vertices), 1))
        )
        return box
    except Exception as e:
        logger.warning(f"Box fallback hatası: {e}")
        return None


def export_room_centroids_json(inventory: dict, output_path: str) -> str:
    """
    Three.js / Remotion kamera animasyonu için oda merkezi koordinatları.
    Sıralama: tur önceliğine göre.
    """
    from .measure import build_narration_data
    narration = build_narration_data(inventory)
    tour = narration["tour_order"]

    centroids = []
    room_by_id = {r["id"]: r for r in inventory.get("rooms", [])}
    for t in tour:
        r = room_by_id.get(t["id"])
        if r:
            c = r.get("centroid_local_m", [0, 0, 0])
            fl = r.get("floor", 0)
            centroids.append({
                "id": r["id"],
                "name": r["name"],
                "area_m2": r["area_m2"],
                "floor": fl,
                "local_m": c,
                "wgs84": r.get("centroid_wgs84", [0, 0, 0]),
            })

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(centroids, f, ensure_ascii=False, indent=2)
    logger.info(f"Oda merkezi listesi: {out} ({len(centroids)} nokta)")
    return str(out)


if __name__ == "__main__":
    import sys, json as _json
    if len(sys.argv) < 3:
        print("Kullanım: python gltf_export.py <inventory.json> <output.glb>")
        sys.exit(1)
    with open(sys.argv[1]) as f:
        inv = _json.load(f)
    export_gltf(inv, sys.argv[2])
