"""
2D Dış Mekân Fallback — Cesium 3D Tiles yoksa.

Girdi: GML envanterinden elde edilen WGS84 koordinatları
Çıktı: Animasyonlu 2D harita turu (PIL) veya Leaflet/OpenLayers karesi

Cesium yoksa: bina poligonu üzerinde düzgün "drone circling" animasyonu simüle eder.
Gerçek uydu fotoğrafı için: CESIUM_ION_TOKEN .env'de tanımlı olmalı.
"""

from __future__ import annotations
import math
from pathlib import Path
from typing import Optional

from loguru import logger


def generate_exterior_frames(
    inventory: dict,
    output_dir: str,
    duration_seconds: int = 15,
    fps: int = 25,
    progress_callback=None,
) -> list[str]:
    """
    GML bina merkezinden 2D dış mekân animasyon karesi dizisi üret.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        raise RuntimeError("Pillow kurulu değil: pip install Pillow")

    centroid = inventory.get("building_centroid_wgs84", [39.9, 32.8])
    lat, lng = centroid[0], centroid[1]
    crs = inventory.get("crs", "?")
    epsg = inventory.get("epsg")
    rooms = inventory.get("rooms", [])
    source = inventory.get("source_file", "Bina")

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    total_frames = duration_seconds * fps
    W, H = 1920, 1080
    paths = []

    # Font
    def _font(size):
        for p in [
            "C:/Windows/Fonts/segoeui.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]:
            if Path(p).exists():
                try:
                    from PIL import ImageFont as IFont
                    return IFont.truetype(p, size)
                except Exception:
                    pass
        from PIL import ImageFont as IFont
        return IFont.load_default()

    f_sm = _font(18); f_md = _font(28); f_lg = _font(42)

    for i in range(total_frames):
        t = i / max(total_frames - 1, 1)

        img = Image.new("RGB", (W, H), (15, 22, 35))
        draw = ImageDraw.Draw(img, "RGBA")

        # Drone yörünge animasyonu: dairesel dönüş
        angle = t * 2 * math.pi  # 0 → 2π
        zoom = 0.3 + 0.7 * (1 - abs(t - 0.5) * 2)  # ortada yakın, başta/sonda uzak

        # Harita arka planı (karanlık zemin + ızgara)
        grid_size = int(60 + zoom * 40)
        for gx in range(0, W, grid_size):
            alpha = int(30 * zoom)
            draw.line([(gx, 0), (gx, H)], fill=(50, 60, 80, alpha), width=1)
        for gy in range(0, H, grid_size):
            alpha = int(30 * zoom)
            draw.line([(0, gy), (W, gy)], fill=(50, 60, 80, alpha), width=1)

        # Bina konumu göstergesi (merkez)
        cx, cy = W // 2, H // 2
        bldg_r = int(40 * zoom)

        # Çevresindeki halkalar (konumsuzluk efekti)
        for ring_r in [bldg_r * 2, bldg_r * 3, bldg_r * 4]:
            draw.ellipse(
                [(cx - ring_r, cy - ring_r), (cx + ring_r, cy + ring_r)],
                outline=(59, 130, 246, 40), width=1
            )

        # Bina simgesi
        draw.ellipse(
            [(cx - bldg_r, cy - bldg_r), (cx + bldg_r, cy + bldg_r)],
            fill=(59, 130, 246, 180), outline=(139, 200, 255), width=3
        )

        # Drone konumu (dairesel orbit)
        orbit_r = int(120 * zoom)
        drone_x = cx + int(orbit_r * math.cos(angle))
        drone_y = cy + int(orbit_r * math.sin(angle) * 0.6)  # perspektif
        draw.ellipse(
            [(drone_x - 8, drone_y - 8), (drone_x + 8, drone_y + 8)],
            fill=(255, 200, 0), outline=(255, 150, 0), width=2
        )
        # Bağlantı çizgisi
        draw.line([(cx, cy), (drone_x, drone_y)], fill=(255, 200, 0, 80), width=1)

        # Koordinat bilgisi
        draw.text((W//2, cy - bldg_r - 30),
                  f"★  {lat:.6f}°N / {lng:.6f}°E",
                  fill=(200, 220, 255), font=f_md, anchor="mb")

        # Bilgi paneli
        panel_x, panel_y = 40, 100
        info_lines = [
            ("Kaynak", crs + (f" (EPSG:{epsg})" if epsg else " (bilinmiyor)")),
            ("Bina",   source.replace(".gml", "")),
            ("Oda",    f"{len(rooms)} oda"),
            ("Konum",  f"{lat:.4f}°N  {lng:.4f}°E"),
        ]
        draw.rectangle([(panel_x - 10, panel_y - 10), (panel_x + 400, panel_y + 170)],
                        fill=(10, 15, 30, 200))
        draw.text((panel_x, panel_y - 5), "DIŞ MEKÂN GÖRÜNÜMÜ",
                  fill=(139, 92, 246), font=f_sm)
        for j, (label, value) in enumerate(info_lines):
            draw.text((panel_x, panel_y + 25 + j * 38), label + ":",
                      fill=(100, 120, 150), font=f_sm)
            draw.text((panel_x + 110, panel_y + 25 + j * 38), value,
                      fill=(200, 215, 240), font=f_sm)

        # Uyarı: Cesium yoksa harita gerçek değil
        draw.rounded_rectangle([(W - 520, 100), (W - 20, 160)],
                                radius=6, fill=(40, 30, 10, 200), outline=(180, 140, 20))
        draw.text((W - 540//2 - 20, 130),
                  "⚠  Gerçek uydu için CESIUM_ION_TOKEN gerekli",
                  fill=(200, 160, 50), font=f_sm, anchor="mm")

        # Footer
        draw.rectangle([(0, H - 50), (W, H)], fill=(10, 12, 25))
        draw.line([(0, H - 50), (W, H - 50)], fill=(40, 45, 80), width=1)
        draw.text((20, H - 30), "Dış mekân simülasyonu  |  Temsilîdir — gerçek uydu görüntüsü değildir",
                  fill=(60, 70, 90), font=_font(14))

        fpath = str(out / f"ext_frame_{i:05d}.png")
        img.save(fpath, "PNG")
        paths.append(fpath)

        if i % fps == 0 and progress_callback:
            progress_callback(int(t * 100), i + 1, total_frames)

    logger.info(f"Dış mekân karesi: {len(paths)} → {out}")
    return paths
