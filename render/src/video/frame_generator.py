"""
PIL tabanlı frame üretici — anahtarsız (keyless) yol.
GML oda envanterinden 1920×1080 PNG kareler üretir.

Düzen:
  ┌──────────────────────────────────────────────────────┐
  │  [Logo]   [Bina Başlık]                 [Kaynak]    │
  ├──────────────────────┬───────────────────────────────┤
  │  KAT PLANI           │  MEVCUT ODA KARTI            │
  │  (Renkli poligonlar) │  Oda Adı (büyük)             │
  │  Aktif oda vurgulu   │  XX.X m²  · Kat N            │
  │                      │  ─────────────────────        │
  │                      │  Diğer Odalar (liste)         │
  ├──────────────────────┴───────────────────────────────┤
  │  ████████░░░░░░  Oda 3/8          [Temsilîdir]      │
  └──────────────────────────────────────────────────────┘
"""

from __future__ import annotations
import math
from pathlib import Path
from typing import Optional

import numpy as np
from loguru import logger

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    logger.warning("Pillow yüklü değil: pip install Pillow")

# ─── Sabitler ──────────────────────────────────────────────────────────────
W, H = 1920, 1080
FPS = 25
PLAN_W = 900   # sol panel genişliği (kat planı)
CARD_X = PLAN_W + 20
HEADER_H = 80
FOOTER_H = 60
PLAN_H = H - HEADER_H - FOOTER_H

# Renkler (BGR yerine RGB)
BG         = (15,  18,  35)       # koyu lacivert
BG2        = (22,  26,  50)       # yan panel
ACCENT     = (59, 130, 246)       # mavi vurgu
ACCENT2    = (139, 92, 246)       # mor
WHITE      = (255, 255, 255)
GRAY       = (160, 160, 175)
LIGHTGRAY  = (210, 215, 230)
GREEN      = (34, 197, 94)
ROOM_COLORS = {
    "Salon":       (149,  99, 226),
    "Yatak Odası": ( 59, 130, 246),
    "Çocuk Odası": (249, 115,  22),
    "Mutfak":      ( 34, 197,  94),
    "Banyo":       ( 20, 184, 166),
    "WC":          (  6, 182, 212),
    "Hol":         (107, 114, 128),
    "Koridor":     (107, 114, 128),
    "Balkon":      ( 74, 222, 128),
    "Teras":       ( 74, 222, 128),
    "Kiler":       (161, 123,  77),
    "Merdiven":    (148, 163, 184),
    "Garaj":       (100, 116, 139),
    "Depo":        (113, 113, 122),
    "Isı Merkezi": (239,  68,  68),
}
DEFAULT_ROOM_COLOR = (99, 102, 241)

# Tur önceliği
TOUR_PRIORITY = {
    "Hol": 0, "Koridor": 1, "Salon": 2, "Mutfak": 3, "Kiler": 4,
    "Oda": 5, "Yatak Odası": 5, "Çocuk Odası": 5,
    "Balkon": 6, "Teras": 6, "Banyo": 7, "WC": 8,
    "Merdiven": 9, "Garaj": 10, "Depo": 11, "Isı Merkezi": 12,
}


# ─── Font yardımcıları ─────────────────────────────────────────────────────

def _font(size: int):
    """TrueType yoksa PIL default kullan."""
    try:
        # Windows sistem fontları
        for path in [
            "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ]:
            if Path(path).exists():
                return ImageFont.truetype(path, size)
    except Exception:
        pass
    return ImageFont.load_default()


def _font_bold(size: int):
    try:
        for path in [
            "C:/Windows/Fonts/segoeuib.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ]:
            if Path(path).exists():
                return ImageFont.truetype(path, size)
    except Exception:
        pass
    return _font(size)


# ─── Ana generator ──────────────────────────────────────────────────────────

class FrameGenerator:
    """GML oda envanterinden animasyonlu PNG kare dizisi üretir."""

    def __init__(self, inventory: dict, duration_seconds: int = 30, fps: int = FPS):
        if not HAS_PIL:
            raise RuntimeError("Pillow kurulu değil: pip install Pillow")

        self.inv = inventory
        self.duration = duration_seconds
        self.fps = fps
        self.total_frames = duration_seconds * fps

        self.rooms = self._sorted_rooms()
        self.bbox = inventory.get("building_bbox_local", {})
        self._plan_transform = self._compute_plan_transform()

        # Font önbelleği
        self._f_sm   = _font(18)
        self._f_md   = _font(24)
        self._f_lg   = _font(36)
        self._f_xl   = _font_bold(52)
        self._f_xxl  = _font_bold(72)
        self._f_tiny = _font(14)

    def _sorted_rooms(self) -> list[dict]:
        rooms = self.inv.get("rooms", [])
        return sorted(rooms, key=lambda r: (
            TOUR_PRIORITY.get(r.get("usage", ""), TOUR_PRIORITY.get(r.get("name", ""), 5)),
            r.get("floor", 0)
        ))

    def _compute_plan_transform(self) -> dict:
        """Yerel metre koordinatlarını plan paneline ölçekler."""
        bb = self.bbox
        pad = 30
        plan_area_w = PLAN_W - 2 * pad
        plan_area_h = PLAN_H - 2 * pad

        w_m = bb.get("width_m", 1) or 1
        h_m = bb.get("height_m", 1) or 1
        scale = min(plan_area_w / w_m, plan_area_h / h_m)

        center_plan_x = PLAN_W / 2
        center_plan_y = HEADER_H + PLAN_H / 2
        cx_m = (bb.get("min_x", 0) + bb.get("max_x", 0)) / 2
        cy_m = (bb.get("min_y", 0) + bb.get("max_y", 0)) / 2

        return {
            "scale": scale,
            "cx_m": cx_m,
            "cy_m": cy_m,
            "cx_px": center_plan_x,
            "cy_px": center_plan_y,
        }

    def _to_plan_px(self, x_m: float, y_m: float) -> tuple[int, int]:
        t = self._plan_transform
        px = t["cx_px"] + (x_m - t["cx_m"]) * t["scale"]
        py = t["cy_px"] - (y_m - t["cy_m"]) * t["scale"]  # Y eksenini ters çevir
        return int(px), int(py)

    # ── Frame üretimi ──────────────────────────────────────────────────────

    def render_frame(self, frame_idx: int) -> Image.Image:
        t = frame_idx / max(self.total_frames - 1, 1)
        room_count = len(self.rooms)

        if room_count == 0:
            return self._empty_frame()

        # Hangi odadayız?
        progress = t * room_count
        room_idx = min(int(progress), room_count - 1)
        room_local_t = progress - int(progress)  # oda içi ilerleme 0..1

        current_room = self.rooms[room_idx]

        img = Image.new("RGB", (W, H), BG)
        draw = ImageDraw.Draw(img, "RGBA")

        self._draw_background(draw)
        self._draw_header(draw, frame_idx)
        self._draw_floor_plan(draw, current_room, room_local_t)
        self._draw_room_card(draw, current_room, room_idx, room_local_t)
        self._draw_footer(draw, room_idx, room_count, t)

        return img

    def _empty_frame(self) -> Image.Image:
        img = Image.new("RGB", (W, H), BG)
        draw = ImageDraw.Draw(img)
        draw.text((W//2, H//2), "GML verisi işleniyor...", fill=GRAY, font=self._f_lg, anchor="mm")
        return img

    def _draw_background(self, draw: ImageDraw.ImageDraw) -> None:
        # Sağ panel farklı ton
        draw.rectangle([(PLAN_W, HEADER_H), (W, H - FOOTER_H)], fill=BG2)
        # Dikey ayırıcı çizgi
        for i in range(3):
            alpha = 180 - i * 60
            draw.line([(PLAN_W + i, HEADER_H), (PLAN_W + i, H - FOOTER_H)],
                      fill=(59, 130, 246, alpha), width=1)

    def _draw_header(self, draw: ImageDraw.ImageDraw, frame: int) -> None:
        # Üst çizgi (gradient efekti)
        for x in range(W):
            ratio = x / W
            r = int(59 + ratio * (139 - 59))
            g = int(130 + ratio * (92 - 130))
            b = int(246 + ratio * (246 - 246))
            draw.line([(x, 0), (x, 3)], fill=(r, g, b))

        # Logo kutusu
        draw.rectangle([(20, 18), (60, 58)], fill=ACCENT, outline=None)
        draw.text((40, 38), "3D", fill=WHITE, font=self._f_md, anchor="mm")

        # Bina başlığı
        source_file = self.inv.get("source_file", "")
        name = source_file.replace(".gml", "").replace("M-", "Bina ") if source_file else "GML Bina"
        crs = self.inv.get("crs", "")
        subtitle = f"Kaynak: CityGML LoD4  ·  {crs}  ·  {self.inv.get('room_count', 0)} oda"

        draw.text((80, 30), name, fill=WHITE, font=self._f_lg)
        draw.text((80, 58), subtitle, fill=GRAY, font=self._f_sm)

        # Sağ üst: GML rozeti
        badge_txt = "GML 3D TUR"
        draw.rounded_rectangle([(W - 160, 20), (W - 20, 58)], radius=8,
                                fill=(34, 197, 94, 40), outline=GREEN)
        draw.text((W - 90, 39), badge_txt, fill=GREEN, font=self._f_sm, anchor="mm")

        # Alt çizgi
        draw.line([(0, HEADER_H - 1), (W, HEADER_H - 1)], fill=(40, 45, 80), width=1)

    def _draw_floor_plan(self, draw: ImageDraw.ImageDraw, current_room: dict,
                          room_local_t: float) -> None:
        """Sol panel: kat planı."""
        all_rooms = self.rooms

        # Arka plan dolgusu
        draw.rectangle([(0, HEADER_H), (PLAN_W, H - FOOTER_H)], fill=BG)

        # "KAT PLANI" başlığı
        draw.text((PLAN_W // 2, HEADER_H + 16), "KAT PLANI",
                  fill=GRAY, font=self._f_tiny, anchor="mm")

        # Kat gruplarını çiz
        floors_drawn = set()
        for room in all_rooms:
            fl = room.get("floor", 0)
            if fl not in floors_drawn:
                floors_drawn.add(fl)

        # Tüm odaları çiz
        for room in all_rooms:
            is_current = room["id"] == current_room["id"]
            self._draw_room_polygon(draw, room, is_current, room_local_t)

        # Aktif oda etiket
        self._draw_room_label(draw, current_room)

    def _draw_room_polygon(self, draw: ImageDraw.ImageDraw, room: dict,
                            is_current: bool, local_t: float) -> None:
        poly = room.get("polygon_local_m", [])
        if not poly or len(poly) < 3:
            # Fallback: merkezden kutu
            self._draw_room_box_fallback(draw, room, is_current, local_t)
            return

        pts = [self._to_plan_px(p[0], p[1]) for p in poly]
        name = room.get("name", "Oda")
        usage = room.get("usage", name)
        base_color = ROOM_COLORS.get(usage, ROOM_COLORS.get(name, DEFAULT_ROOM_COLOR))

        if is_current:
            # Vurgulu + nabız efekti
            pulse = 0.6 + 0.4 * math.sin(local_t * math.pi * 4)
            alpha_fill = int(180 * pulse)
            alpha_outline = 255
            r, g, b = [min(255, int(c * 1.3)) for c in base_color]
            outline_color = WHITE
            outline_w = 3
        else:
            alpha_fill = 60
            alpha_outline = 100
            r, g, b = base_color
            outline_color = (r, g, b, 120)
            outline_w = 1

        try:
            draw.polygon(pts, fill=(*base_color, alpha_fill))
            draw.line(pts + [pts[0]], fill=(*outline_color[:3], alpha_outline), width=outline_w)
        except Exception:
            pass

    def _draw_room_box_fallback(self, draw: ImageDraw.ImageDraw, room: dict,
                                  is_current: bool, local_t: float) -> None:
        """Poligon yokken oda merkezinden kutu çiz."""
        c = room.get("centroid_local_m", [0, 0, 0])
        cx, cy = self._to_plan_px(c[0], c[1])
        area = room.get("area_m2", 9)
        side = max(15, int((area ** 0.5) * self._plan_transform["scale"] * 0.5))
        name = room.get("name", "Oda")
        usage = room.get("usage", name)
        color = ROOM_COLORS.get(usage, ROOM_COLORS.get(name, DEFAULT_ROOM_COLOR))

        alpha = 180 if is_current else 60
        draw.rectangle([(cx - side, cy - side), (cx + side, cy + side)],
                        fill=(*color, alpha), outline=(*color, 200) if is_current else None)

    def _draw_room_label(self, draw: ImageDraw.ImageDraw, room: dict) -> None:
        """Aktif odanın üzerine isim etiketi yaz."""
        poly = room.get("polygon_local_m", [])
        if poly:
            cx_m = sum(p[0] for p in poly) / len(poly)
            cy_m = sum(p[1] for p in poly) / len(poly)
        else:
            c = room.get("centroid_local_m", [0, 0, 0])
            cx_m, cy_m = c[0], c[1]

        px, py = self._to_plan_px(cx_m, cy_m)
        name = room.get("name", "Oda")
        area = room.get("area_m2", 0)

        # Etiket kutusu
        label = f"{name}"
        sub = f"{area:.1f} m²"
        bbox = draw.textbbox((px, py), label, font=self._f_sm, anchor="mm")
        pad = 4
        draw.rounded_rectangle(
            [(bbox[0]-pad, bbox[1]-pad), (bbox[2]+pad, bbox[3]+pad)],
            radius=4, fill=(0, 0, 0, 180)
        )
        draw.text((px, py), label, fill=WHITE, font=self._f_sm, anchor="mm")
        draw.text((px, py + 20), sub, fill=GRAY, font=self._f_tiny, anchor="mm")

    def _draw_room_card(self, draw: ImageDraw.ImageDraw, room: dict,
                         room_idx: int, local_t: float) -> None:
        """Sağ panel: mevcut oda kartı."""
        card_x = PLAN_W + 40
        card_y = HEADER_H + 40

        name = room.get("name", "Oda")
        usage = room.get("usage", name)
        area = room.get("area_m2", 0)
        floor = room.get("floor", 0)
        sec_id = room.get("independent_section_id", "")

        color = ROOM_COLORS.get(usage, ROOM_COLORS.get(name, DEFAULT_ROOM_COLOR))

        # Renk şeridi
        draw.rectangle([(card_x - 10, card_y), (card_x - 4, card_y + 200)],
                        fill=color)

        # Oda adı
        draw.text((card_x, card_y + 10), name,
                  fill=WHITE, font=self._f_xxl)

        # Alan + kat
        draw.text((card_x, card_y + 100),
                  f"{area:.1f} m²",
                  fill=color, font=self._f_xl)
        draw.text((card_x, card_y + 160),
                  f"Kat {floor}",
                  fill=GRAY, font=self._f_lg)

        if sec_id:
            draw.text((card_x, card_y + 205),
                      f"Bağımsız Bölüm: {sec_id[-8:]}",
                      fill=(100, 120, 150), font=self._f_sm)

        # Ayırıcı
        ay = card_y + 240
        draw.line([(card_x, ay), (W - 40, ay)], fill=(40, 45, 80), width=1)

        # Diğer odalar listesi
        self._draw_room_list(draw, card_x, ay + 20, room_idx)

        # Binanın özeti (en alta)
        self._draw_building_summary(draw, card_x, H - FOOTER_H - 120)

    def _draw_room_list(self, draw: ImageDraw.ImageDraw, x: int, y: int,
                         current_idx: int) -> None:
        """Tüm odaların kompakt listesi."""
        draw.text((x, y), "ODALAR", fill=GRAY, font=self._f_tiny)
        y += 22
        max_show = min(10, len(self.rooms))
        item_h = 32

        for i, room in enumerate(self.rooms[:max_show]):
            name = room.get("name", "Oda")
            usage = room.get("usage", name)
            area = room.get("area_m2", 0)
            color = ROOM_COLORS.get(usage, ROOM_COLORS.get(name, DEFAULT_ROOM_COLOR))
            is_curr = (i == current_idx)

            row_y = y + i * item_h
            if row_y > H - FOOTER_H - 150:
                break

            if is_curr:
                draw.rounded_rectangle([(x - 8, row_y - 4), (W - 44, row_y + item_h - 8)],
                                        radius=6, fill=(30, 35, 65))

            # Renk noktası
            draw.ellipse([(x, row_y + 6), (x + 12, row_y + 18)], fill=color)

            # İsim
            draw.text((x + 20, row_y + 4), name,
                      fill=WHITE if is_curr else GRAY,
                      font=self._f_sm if is_curr else self._f_tiny)

            # Alan (sağa hizalı)
            draw.text((W - 50, row_y + 4), f"{area:.1f}",
                      fill=LIGHTGRAY if is_curr else (100, 105, 120),
                      font=self._f_tiny, anchor="ra")

        if len(self.rooms) > max_show:
            draw.text((x, y + max_show * item_h + 4),
                      f"+{len(self.rooms) - max_show} oda daha",
                      fill=(80, 85, 100), font=self._f_tiny)

    def _draw_building_summary(self, draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
        """Alt kısım: bina özeti."""
        draw.line([(x, y), (W - 40, y)], fill=(40, 45, 80), width=1)
        sections = self.inv.get("independent_sections", [])
        total_area = sum(r.get("area_m2", 0) for r in self.rooms)
        crs = self.inv.get("crs", "?")
        epsg = self.inv.get("epsg")

        items = [
            (f"{len(self.rooms)} oda", "Toplam"),
            (f"{len(sections)} bağımsız bölüm", ""),
            (f"{total_area:.0f} m²", "Toplam Alan"),
            (f"{crs}", f"EPSG:{epsg}" if epsg else ""),
        ]
        col_w = (W - x - 40) // len(items)
        for i, (val, label) in enumerate(items):
            cx = x + i * col_w + col_w // 2
            draw.text((cx, y + 18), val, fill=WHITE, font=self._f_sm, anchor="mm")
            if label:
                draw.text((cx, y + 36), label, fill=GRAY, font=self._f_tiny, anchor="mm")

    def _draw_footer(self, draw: ImageDraw.ImageDraw, room_idx: int,
                      room_count: int, progress: float) -> None:
        """Alt çubuk: ilerleme + temsilîdir."""
        fy = H - FOOTER_H

        draw.line([(0, fy), (W, fy)], fill=(40, 45, 80), width=1)
        draw.rectangle([(0, fy), (W, H)], fill=(10, 12, 25))

        # İlerleme çubuğu
        bar_x, bar_y = 20, fy + 18
        bar_w, bar_h = PLAN_W - 40, 8
        draw.rounded_rectangle([(bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h)],
                                radius=4, fill=(30, 35, 60))
        filled = int(bar_w * progress)
        if filled > 0:
            for xi in range(filled):
                ratio = xi / bar_w
                r = int(59 + ratio * 80)
                g = int(130 + ratio * (92 - 130))
                b = 246
                draw.line([(bar_x + xi, bar_y), (bar_x + xi, bar_y + bar_h)],
                           fill=(r, g, b))

        # Oda sayacı
        draw.text((bar_x, fy + 34),
                  f"Oda {room_idx + 1} / {room_count}",
                  fill=GRAY, font=self._f_tiny)

        # Temsilîdir notu
        note = "★  Geometri ve alan resmî CityGML (LoD4) verisinden üretilmiştir. Kaplama ve mobilya temsilîdir."
        draw.text((PLAN_W + 20, fy + 22), note, fill=(80, 90, 110), font=self._f_tiny)


# ─── Batch render ───────────────────────────────────────────────────────────

def generate_frames(
    inventory: dict,
    output_dir: str,
    duration_seconds: int = 30,
    fps: int = FPS,
    progress_callback=None,
) -> list[str]:
    """
    Tüm kare dizisini üret ve dosyalara yaz.
    Döndürür: PNG dosya yollarının listesi.
    """
    if not HAS_PIL:
        raise RuntimeError("Pillow kurulu değil: pip install Pillow")

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    gen = FrameGenerator(inventory, duration_seconds, fps)
    total = gen.total_frames
    paths = []

    logger.info(f"Kare üretimi başlıyor: {total} kare ({duration_seconds}s @ {fps}fps)")

    for i in range(total):
        frame_img = gen.render_frame(i)
        fpath = str(out / f"frame_{i:05d}.png")
        frame_img.save(fpath, "PNG", optimize=False)
        paths.append(fpath)

        if i % fps == 0 or i == total - 1:
            pct = int((i + 1) / total * 100)
            logger.info(f"  {pct}% ({i+1}/{total})")
            if progress_callback:
                progress_callback(pct, i + 1, total)

    logger.info(f"Kare üretimi tamamlandı: {len(paths)} dosya → {out}")
    return paths
