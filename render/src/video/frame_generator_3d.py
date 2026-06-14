"""
İzometrik 3D Frame Üretici — Pillow tabanlı.

Emlakçı girdilerinden oluşturulan kat planını 3D izometrik görünümle render eder.

Animasyon fazları:
  0–20%:  Bina dış görünüm (çok katlı bina, hedef kat vurgulanır, kamera döner)
  20–85%: Daire iç tur (odalar arası geçiş, her oda vurgulanır)
  85–100%: Kapanış (zoom-out + ilan bilgileri overlay)

Her kare 1920×1080 PNG.
"""

from __future__ import annotations
import math
from pathlib import Path
from typing import Optional, Callable

from loguru import logger

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# ─── Sabitler ──────────────────────────────────────────────────────────────
W, H = 1920, 1080
FPS = 25

# Renk paleti
BG          = ( 12,  15,  30)
BG_GRADIENT = ( 18,  22,  42)
ACCENT      = ( 90, 110, 255)
ACCENT2     = (140, 100, 240)
WHITE       = (255, 255, 255)
GRAY        = (150, 155, 170)
LIGHTGRAY   = (200, 205, 220)
DARK        = ( 30,  35,  55)
GREEN       = ( 50, 210, 140)
FLOOR_COLOR = ( 45,  50,  75)  # kat zemin
WALL_BASE   = ( 55,  60,  85)  # duvar gölge

# Bina dış renkleri
BLDG_BODY    = ( 60,  65,  90)
BLDG_ACTIVE  = (100, 130, 255)
BLDG_WINDOW  = ( 80,  90, 120)
BLDG_ROOF    = ( 45,  50,  70)

# İzometrik projeksiyon
ISO_ANGLE = math.radians(30)
COS_ISO = math.cos(ISO_ANGLE)
SIN_ISO = math.sin(ISO_ANGLE)

WALL_HEIGHT_M = 2.8  # oda duvar yüksekliği (metre)


# ─── Font yardımcıları ─────────────────────────────────────────────────────

def _font(size: int):
    try:
        for path in [
            "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
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
        ]:
            if Path(path).exists():
                return ImageFont.truetype(path, size)
    except Exception:
        pass
    return _font(size)


# ─── İzometrik projeksiyon ─────────────────────────────────────────────────

def _iso(x: float, y: float, z: float, scale: float, ox: float, oy: float):
    """3D → 2D izometrik projeksiyon."""
    sx = (x - y) * COS_ISO * scale + ox
    sy = (x + y) * SIN_ISO * scale - z * scale + oy
    return int(sx), int(sy)


# ─── Ana sınıf ─────────────────────────────────────────────────────────────

class FrameGenerator3D:
    """Kat planından izometrik 3D animasyon kareleri üretir."""

    def __init__(self, floor_plan: dict, duration: int = 30, fps: int = FPS):
        if not HAS_PIL:
            raise RuntimeError("Pillow kurulu değil")

        self.plan = floor_plan
        self.rooms = floor_plan["rooms"]
        self.apt_w = floor_plan["apartment_width"]
        self.apt_d = floor_plan["apartment_depth"]
        self.duration = duration
        self.fps = fps
        self.total_frames = duration * fps
        self.title = floor_plan.get("title", "3D Emlak")
        self.current_floor = floor_plan.get("current_floor", 3)
        self.total_floors = floor_plan.get("total_floors", 8)

        # Tur sırasına göre odaları sırala
        from render.src.procedural.floor_plan import get_tour_order
        self.tour_rooms = get_tour_order(self.rooms)

        # Font önbelleği
        self._f_sm   = _font(18)
        self._f_md   = _font(24)
        self._f_lg   = _font(34)
        self._f_xl   = _font_bold(48)
        self._f_xxl  = _font_bold(64)
        self._f_tiny = _font(14)

    # ── Public API ─────────────────────────────────────────────────────────

    def render_frame(self, frame_idx: int) -> Image.Image:
        t = frame_idx / max(self.total_frames - 1, 1)  # 0..1

        if t < 0.20:
            return self._render_exterior(t / 0.20)
        elif t < 0.85:
            interior_t = (t - 0.20) / 0.65
            return self._render_interior(interior_t)
        else:
            closing_t = (t - 0.85) / 0.15
            return self._render_closing(closing_t)

    # ── Faz 1: Bina dış görünüm ───────────────────────────────────────────

    def _render_exterior(self, t: float) -> Image.Image:
        """Binanın dıştan izometrik görünümü, hedef kat vurgulanır."""
        img = Image.new("RGB", (W, H), BG)
        draw = ImageDraw.Draw(img, "RGBA")

        self._draw_bg_gradient(draw)
        self._draw_header(draw, "BINA DIŞ GÖRÜNÜM")

        # Bina parametreleri
        n_floors = self.total_floors
        floor_h_m = 3.0  # her kat 3m
        bldg_w = self.apt_w * 1.2
        bldg_d = self.apt_d * 0.8
        bldg_h = n_floors * floor_h_m

        # Ölçek ve konum
        scale = min(
            (W * 0.45) / (bldg_w + bldg_d),
            (H * 0.55) / bldg_h
        )
        ox = W * 0.50
        oy = H * 0.80

        # Animasyon: hafif yatay pan
        pan = math.sin(t * math.pi * 2) * 30
        ox += pan

        # Her katı çiz (alttan yukarı)
        for fl in range(n_floors):
            z_base = fl * floor_h_m
            is_active = (fl + 1 == self.current_floor)

            # Kat rengi
            if is_active:
                # Nabız efekti
                pulse = 0.7 + 0.3 * math.sin(t * math.pi * 6)
                body = tuple(int(c * pulse) for c in BLDG_ACTIVE)
                alpha = int(220 * pulse)
            else:
                body = BLDG_BODY
                alpha = 120

            self._draw_box(draw, 0, 0, z_base, bldg_w, bldg_d, floor_h_m,
                           body, scale, ox, oy, alpha)

            # Pencereler
            if not is_active:
                n_win_x = max(2, int(bldg_w / 3))
                n_win_y = max(1, int(bldg_d / 4))
                self._draw_windows(draw, 0, 0, z_base, bldg_w, bldg_d,
                                   floor_h_m, n_win_x, scale, ox, oy)

        # Çatı
        z_top = n_floors * floor_h_m
        self._draw_roof(draw, 0, 0, z_top, bldg_w, bldg_d, scale, ox, oy)

        # Hedef kat etiketi
        active_z = (self.current_floor - 1) * floor_h_m + floor_h_m / 2
        label_x, label_y = _iso(bldg_w + 1, bldg_d / 2, active_z, scale, ox, oy)
        draw.text((label_x + 15, label_y),
                  f"← {self.current_floor}. Kat (Sizin Daireniz)",
                  fill=BLDG_ACTIVE, font=self._f_md)

        # Bina bilgisi
        self._draw_exterior_info(draw, t)

        self._draw_footer(draw, t, "Bina Dış Görünüm")
        return img

    # ── Faz 2: Daire iç tur ───────────────────────────────────────────────

    def _render_interior(self, t: float) -> Image.Image:
        """Daire içi oda-oda tur — izometrik 3D kat planı."""
        img = Image.new("RGB", (W, H), BG)
        draw = ImageDraw.Draw(img, "RGBA")

        self._draw_bg_gradient(draw)
        self._draw_header(draw, "DAİRE İÇ TUR")

        n_rooms = len(self.tour_rooms)
        if n_rooms == 0:
            draw.text((W//2, H//2), "Oda bulunamadı",
                      fill=GRAY, font=self._f_lg, anchor="mm")
            return img

        # Hangi odadayız?
        progress = t * n_rooms
        room_idx = min(int(progress), n_rooms - 1)
        room_t = progress - int(progress)  # oda içi ilerleme
        current_room = self.tour_rooms[room_idx]

        # Ölçek ve konum (kat planını ekrana sığdır)
        plan_area_w = W * 0.55
        plan_area_h = H * 0.65
        scale = min(
            plan_area_w / (self.apt_w + self.apt_d),
            plan_area_h / (max(self.apt_d, WALL_HEIGHT_M * 2))
        )
        # Aktif odaya doğru pan
        cx = current_room["x"] + current_room["width"] / 2
        cy = current_room["y"] + current_room["depth"] / 2
        target_ox = W * 0.38 - (cx - cy) * COS_ISO * scale
        target_oy = H * 0.75 - (cx + cy) * SIN_ISO * scale

        ox = target_ox
        oy = target_oy

        # ── Tüm odaları çiz ────────────────────────────────────────────────
        for room in self.rooms:
            is_current = room is current_room
            self._draw_room_3d(draw, room, is_current, room_t, scale, ox, oy)

        # ── Sağ panel: oda kartı ────────────────────────────────────────────
        self._draw_room_info_panel(draw, current_room, room_idx, n_rooms)

        self._draw_footer(draw, 0.20 + t * 0.65,
                          f"Oda {room_idx + 1} / {n_rooms}")
        return img

    # ── Faz 3: Kapanış ────────────────────────────────────────────────────

    def _render_closing(self, t: float) -> Image.Image:
        """Kapanış: ilan özeti + CTA."""
        img = Image.new("RGB", (W, H), BG)
        draw = ImageDraw.Draw(img, "RGBA")

        self._draw_bg_gradient(draw)

        # Orta: başlık
        y_center = H * 0.35
        draw.text((W // 2, y_center), self.title,
                  fill=WHITE, font=self._f_xxl, anchor="mm")

        # Alt bilgiler
        info_items = [
            f"📐 {self.plan['room_type']}",
            f"📏 {self.plan['gross_area']:.0f} m² brüt",
            f"🏢 {self.current_floor}. kat / {self.total_floors} katlı",
            f"🧭 {self.plan['facade']} cephe",
            f"🏠 {len(self.rooms)} oda",
        ]

        y = y_center + 60
        for item in info_items:
            draw.text((W // 2, y), item,
                      fill=LIGHTGRAY, font=self._f_lg, anchor="mm")
            y += 48

        # CTA
        fade = min(1.0, t * 3)
        alpha = int(255 * fade)
        y += 30
        draw.rounded_rectangle(
            [(W//2 - 220, y), (W//2 + 220, y + 60)],
            radius=12,
            fill=(*GREEN, alpha),
        )
        draw.text((W // 2, y + 30), "İletişime Geçin",
                  fill=(*WHITE, alpha), font=self._f_xl, anchor="mm")

        # Footer
        draw.text((W // 2, H - 40), "★ Bu video otomatik olarak oluşturulmuştur",
                  fill=(*GRAY, 120), font=self._f_tiny, anchor="mm")

        return img

    # ── Yardımcı çizim fonksiyonları ───────────────────────────────────────

    def _draw_bg_gradient(self, draw: ImageDraw.ImageDraw):
        """Hafif gradient arka plan."""
        for y in range(0, H, 4):
            ratio = y / H
            r = int(BG[0] + (BG_GRADIENT[0] - BG[0]) * ratio)
            g = int(BG[1] + (BG_GRADIENT[1] - BG[1]) * ratio)
            b = int(BG[2] + (BG_GRADIENT[2] - BG[2]) * ratio)
            draw.line([(0, y), (W, y)], fill=(r, g, b), width=4)

    def _draw_header(self, draw: ImageDraw.ImageDraw, subtitle: str):
        """Üst başlık çubuğu."""
        # Gradient çizgi
        for x in range(W):
            ratio = x / W
            r = int(ACCENT[0] + ratio * (ACCENT2[0] - ACCENT[0]))
            g = int(ACCENT[1] + ratio * (ACCENT2[1] - ACCENT[1]))
            b = int(ACCENT[2] + ratio * (ACCENT2[2] - ACCENT[2]))
            draw.line([(x, 0), (x, 3)], fill=(r, g, b))

        # Logo
        draw.rounded_rectangle([(20, 14), (56, 50)], radius=8,
                               fill=ACCENT)
        draw.text((38, 32), "3D", fill=WHITE, font=self._f_sm, anchor="mm")

        # Başlık
        draw.text((68, 22), self.title, fill=WHITE, font=self._f_md)
        draw.text((68, 48), subtitle, fill=GRAY, font=self._f_tiny)

        # Sağ rozet
        badge = f"{self.plan['room_type']} · {self.plan['gross_area']:.0f}m²"
        draw.rounded_rectangle([(W-200, 16), (W-20, 48)], radius=8,
                               fill=(*GREEN, 40), outline=GREEN)
        draw.text((W-110, 32), badge, fill=GREEN, font=self._f_sm, anchor="mm")

        # Alt çizgi
        draw.line([(0, 64), (W, 64)], fill=DARK, width=1)

    def _draw_footer(self, draw: ImageDraw.ImageDraw, progress: float, label: str):
        """Alt ilerleme çubuğu."""
        fy = H - 50
        draw.rectangle([(0, fy), (W, H)], fill=(10, 12, 25))
        draw.line([(0, fy), (W, fy)], fill=DARK)

        # İlerleme çubuğu
        bar_x, bar_y, bar_w, bar_h = 20, fy + 14, W - 40, 6
        draw.rounded_rectangle([(bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h)],
                               radius=3, fill=DARK)
        filled = int(bar_w * progress)
        if filled > 0:
            for xi in range(filled):
                ratio = xi / bar_w
                r = int(ACCENT[0] + ratio * (ACCENT2[0] - ACCENT[0]))
                g = int(ACCENT[1] + ratio * (ACCENT2[1] - ACCENT[1]))
                b = ACCENT[2]
                draw.line([(bar_x + xi, bar_y), (bar_x + xi, bar_y + bar_h)],
                          fill=(r, g, b))

        draw.text((20, fy + 28), label, fill=GRAY, font=self._f_tiny)
        draw.text((W - 20, fy + 28),
                  "★ Bu video otomatik olarak oluşturulmuştur. Görseller temsilidir.",
                  fill=(70, 75, 95), font=self._f_tiny, anchor="ra")

    def _draw_box(self, draw, x, y, z, w, d, h, color, scale, ox, oy, alpha=200):
        """İzometrik kutu (bina katı) çiz."""
        # Üst yüzey
        top = [
            _iso(x, y, z + h, scale, ox, oy),
            _iso(x + w, y, z + h, scale, ox, oy),
            _iso(x + w, y + d, z + h, scale, ox, oy),
            _iso(x, y + d, z + h, scale, ox, oy),
        ]
        # Sol yüzey
        left = [
            _iso(x, y + d, z, scale, ox, oy),
            _iso(x, y + d, z + h, scale, ox, oy),
            _iso(x + w, y + d, z + h, scale, ox, oy),
            _iso(x + w, y + d, z, scale, ox, oy),
        ]
        # Sağ yüzey
        right = [
            _iso(x + w, y, z, scale, ox, oy),
            _iso(x + w, y, z + h, scale, ox, oy),
            _iso(x + w, y + d, z + h, scale, ox, oy),
            _iso(x + w, y + d, z, scale, ox, oy),
        ]

        # Renk varyasyonları (üst açık, yan koyu)
        cr, cg, cb = color
        top_c = (min(255, cr + 30), min(255, cg + 30), min(255, cb + 30), alpha)
        left_c = (max(0, cr - 15), max(0, cg - 15), max(0, cb - 15), alpha)
        right_c = (max(0, cr - 25), max(0, cg - 25), max(0, cb - 25), alpha)

        draw.polygon(left, fill=left_c)
        draw.polygon(right, fill=right_c)
        draw.polygon(top, fill=top_c)

        # Kenar çizgileri
        for pts in [top, left, right]:
            draw.line(pts + [pts[0]], fill=(*DARK, 100), width=1)

    def _draw_windows(self, draw, x, y, z, bw, bd, fh, n, scale, ox, oy):
        """Bina pencerelerini çiz (ön yüzey)."""
        win_w = bw / (n * 2 + 1)
        win_h = fh * 0.4
        win_y_off = fh * 0.3

        for i in range(n):
            wx = x + win_w * (2 * i + 1)
            wz = z + win_y_off

            pts = [
                _iso(wx, y + bd, wz, scale, ox, oy),
                _iso(wx + win_w, y + bd, wz, scale, ox, oy),
                _iso(wx + win_w, y + bd, wz + win_h, scale, ox, oy),
                _iso(wx, y + bd, wz + win_h, scale, ox, oy),
            ]
            draw.polygon(pts, fill=(*BLDG_WINDOW, 80))

    def _draw_roof(self, draw, x, y, z, w, d, scale, ox, oy):
        """Basit düz çatı."""
        roof_h = 1.0
        top = [
            _iso(x - 0.3, y - 0.3, z + roof_h, scale, ox, oy),
            _iso(x + w + 0.3, y - 0.3, z + roof_h, scale, ox, oy),
            _iso(x + w + 0.3, y + d + 0.3, z + roof_h, scale, ox, oy),
            _iso(x - 0.3, y + d + 0.3, z + roof_h, scale, ox, oy),
        ]
        draw.polygon(top, fill=(*BLDG_ROOF, 200))
        draw.line(top + [top[0]], fill=(*DARK, 120), width=1)

    def _draw_room_3d(self, draw, room, is_current, local_t, scale, ox, oy):
        """Bir odayı 3D izometrik olarak çiz: zemin + duvarlar."""
        x, y = room["x"], room["y"]
        w, d = room["width"], room["depth"]
        cr, cg, cb = room["color"]

        if is_current:
            pulse = 0.7 + 0.3 * math.sin(local_t * math.pi * 4)
            floor_alpha = int(200 * pulse)
            wall_alpha = int(160 * pulse)
            wall_h = WALL_HEIGHT_M
            cr = min(255, int(cr * 1.3))
            cg = min(255, int(cg * 1.3))
            cb = min(255, int(cb * 1.3))
        else:
            floor_alpha = 100
            wall_alpha = 60
            wall_h = WALL_HEIGHT_M * 0.7  # İnaktif odalar daha alçak

        # ── Zemin ──────────────────────────────────────────────────────────
        floor_pts = [
            _iso(x, y, 0, scale, ox, oy),
            _iso(x + w, y, 0, scale, ox, oy),
            _iso(x + w, y + d, 0, scale, ox, oy),
            _iso(x, y + d, 0, scale, ox, oy),
        ]
        draw.polygon(floor_pts, fill=(cr, cg, cb, floor_alpha))
        draw.line(floor_pts + [floor_pts[0]], fill=(cr, cg, cb, 180), width=1)

        # ── Arka duvarlar (sol ve üst) ─────────────────────────────────────
        # Sol duvar (x sabit, y değişir)
        left_wall = [
            _iso(x, y, 0, scale, ox, oy),
            _iso(x, y, wall_h, scale, ox, oy),
            _iso(x, y + d, wall_h, scale, ox, oy),
            _iso(x, y + d, 0, scale, ox, oy),
        ]
        draw.polygon(left_wall, fill=(max(0,cr-20), max(0,cg-20), max(0,cb-20), wall_alpha))
        draw.line(left_wall + [left_wall[0]], fill=(*DARK, 80), width=1)

        # Üst duvar (y sabit, x değişir)
        top_wall = [
            _iso(x, y, 0, scale, ox, oy),
            _iso(x, y, wall_h, scale, ox, oy),
            _iso(x + w, y, wall_h, scale, ox, oy),
            _iso(x + w, y, 0, scale, ox, oy),
        ]
        draw.polygon(top_wall, fill=(max(0,cr-30), max(0,cg-30), max(0,cb-30), wall_alpha))
        draw.line(top_wall + [top_wall[0]], fill=(*DARK, 80), width=1)

        # ── Oda etiketi (zemin ortasına) ───────────────────────────────────
        cx_m = x + w / 2
        cy_m = y + d / 2
        lx, ly = _iso(cx_m, cy_m, 0.1, scale, ox, oy)

        if is_current:
            # Etiket kutusu
            name = room["name"]
            area_txt = f"{room['area_m2']:.0f}m²"
            bbox = draw.textbbox((lx, ly), name, font=self._f_md, anchor="mm")
            pad = 6
            draw.rounded_rectangle(
                [(bbox[0]-pad, bbox[1]-pad-2), (bbox[2]+pad, bbox[3]+pad+16)],
                radius=6, fill=(0, 0, 0, 180)
            )
            draw.text((lx, ly - 4), name, fill=WHITE, font=self._f_md, anchor="mm")
            draw.text((lx, ly + 20), area_txt, fill=(cr, cg, cb), font=self._f_sm, anchor="mm")
        else:
            draw.text((lx, ly), room["name"], fill=(*GRAY, 160),
                      font=self._f_tiny, anchor="mm")

        # ── Basit mobilya (aktif oda) ──────────────────────────────────────
        if is_current and room.get("furniture"):
            self._draw_furniture(draw, room, scale, ox, oy)

    def _draw_furniture(self, draw, room, scale, ox, oy):
        """Odaya basit mobilya siluetleri çiz."""
        x, y = room["x"], room["y"]
        w, d = room["width"], room["depth"]
        rtype = room["type"]

        # Mobilya boyutları (oda boyutuna orantılı)
        if rtype == "salon":
            # Kanepe (ortada-solda)
            self._draw_furniture_box(draw, x + w*0.1, y + d*0.5, 0,
                                     w*0.35, d*0.15, 0.4,
                                     (80, 80, 120), scale, ox, oy)
            # Sehpa
            self._draw_furniture_box(draw, x + w*0.2, y + d*0.3, 0,
                                     w*0.15, d*0.1, 0.3,
                                     (100, 80, 60), scale, ox, oy)
        elif rtype == "yatak":
            # Yatak
            self._draw_furniture_box(draw, x + w*0.15, y + d*0.2, 0,
                                     w*0.5, d*0.6, 0.35,
                                     (160, 140, 120), scale, ox, oy)
            # Komodin
            self._draw_furniture_box(draw, x + w*0.7, y + d*0.2, 0,
                                     w*0.12, d*0.12, 0.35,
                                     (90, 75, 60), scale, ox, oy)
        elif rtype == "mutfak":
            # Tezgah (L şeklinde)
            self._draw_furniture_box(draw, x + w*0.05, y + d*0.05, 0,
                                     w*0.9, d*0.15, 0.6,
                                     (140, 140, 150), scale, ox, oy)
            # Buzdolabı
            self._draw_furniture_box(draw, x + w*0.78, y + d*0.25, 0,
                                     w*0.12, d*0.15, 1.2,
                                     (180, 185, 195), scale, ox, oy)
        elif rtype == "banyo":
            # Küvet/duş
            self._draw_furniture_box(draw, x + w*0.05, y + d*0.1, 0,
                                     w*0.4, d*0.7, 0.45,
                                     (200, 210, 220), scale, ox, oy)
        elif rtype == "balkon":
            # Sandalye
            self._draw_furniture_box(draw, x + w*0.3, y + d*0.3, 0,
                                     w*0.2, d*0.2, 0.45,
                                     (100, 90, 70), scale, ox, oy)

    def _draw_furniture_box(self, draw, x, y, z, w, d, h, color, scale, ox, oy):
        """Küçük izometrik kutu (mobilya)."""
        top = [
            _iso(x, y, z+h, scale, ox, oy),
            _iso(x+w, y, z+h, scale, ox, oy),
            _iso(x+w, y+d, z+h, scale, ox, oy),
            _iso(x, y+d, z+h, scale, ox, oy),
        ]
        left = [
            _iso(x, y+d, z, scale, ox, oy),
            _iso(x, y+d, z+h, scale, ox, oy),
            _iso(x+w, y+d, z+h, scale, ox, oy),
            _iso(x+w, y+d, z, scale, ox, oy),
        ]
        right = [
            _iso(x+w, y, z, scale, ox, oy),
            _iso(x+w, y, z+h, scale, ox, oy),
            _iso(x+w, y+d, z+h, scale, ox, oy),
            _iso(x+w, y+d, z, scale, ox, oy),
        ]
        cr, cg, cb = color
        draw.polygon(top, fill=(min(255,cr+20), min(255,cg+20), min(255,cb+20), 150))
        draw.polygon(left, fill=(cr, cg, cb, 120))
        draw.polygon(right, fill=(max(0,cr-20), max(0,cg-20), max(0,cb-20), 120))

    def _draw_room_info_panel(self, draw, room, room_idx, total):
        """Sağ panel: aktif oda bilgi kartı."""
        px = W * 0.68
        py = 90

        cr, cg, cb = room["color"]

        # Renk şeridi
        draw.rectangle([(px - 8, py), (px - 3, py + 180)], fill=(cr, cg, cb))

        # Oda adı
        draw.text((px, py + 5), room["name"], fill=WHITE, font=self._f_xxl)

        # Alan
        draw.text((px, py + 75), f"{room['area_m2']:.0f} m²",
                  fill=(cr, cg, cb), font=self._f_xl)

        # Tip
        type_labels = {
            "salon": "Yaşam Alanı", "yatak": "Yatak Odası", "mutfak": "Mutfak",
            "banyo": "Islak Hacim", "wc": "Tuvalet", "hol": "Giriş / Hol",
            "balkon": "Açık Alan", "kiler": "Depolama", "antre": "Antre",
        }
        draw.text((px, py + 130),
                  type_labels.get(room["type"], room["type"].title()),
                  fill=GRAY, font=self._f_md)

        # Ayırıcı
        draw.line([(px, py + 175), (W - 30, py + 175)], fill=DARK)

        # Tüm odalar listesi
        draw.text((px, py + 195), "TÜM ODALAR", fill=GRAY, font=self._f_tiny)
        from render.src.procedural.floor_plan import get_tour_order
        all_rooms = get_tour_order(self.rooms)
        y_list = py + 220
        for i, r in enumerate(all_rooms):
            if y_list > H - 120:
                draw.text((px, y_list), f"+{len(all_rooms) - i} oda daha",
                          fill=(70, 75, 95), font=self._f_tiny)
                break
            is_curr = (i == room_idx)
            rcr, rcg, rcb = r["color"]

            if is_curr:
                draw.rounded_rectangle(
                    [(px - 6, y_list - 3), (W - 28, y_list + 27)],
                    radius=5, fill=(30, 35, 60)
                )

            draw.ellipse([(px, y_list + 6), (px + 10, y_list + 16)],
                         fill=(rcr, rcg, rcb))
            draw.text((px + 18, y_list + 3), r["name"],
                      fill=WHITE if is_curr else GRAY,
                      font=self._f_sm if is_curr else self._f_tiny)
            draw.text((W - 35, y_list + 3), f"{r['area_m2']:.0f}",
                      fill=LIGHTGRAY if is_curr else (90, 95, 110),
                      font=self._f_tiny, anchor="ra")
            y_list += 32

    def _draw_exterior_info(self, draw, t: float):
        """Bina dış görünüm ekranında sağ panel bilgileri."""
        px = W * 0.72
        py = 100

        draw.text((px, py), "BİNA BİLGİLERİ", fill=GRAY, font=self._f_tiny)
        py += 25

        items = [
            ("🏢", "Toplam Kat", f"{self.total_floors}"),
            ("🏠", "Daire Tipi", self.plan["room_type"]),
            ("📐", "Brüt Alan", f"{self.plan['gross_area']:.0f} m²"),
            ("📏", "Net Alan", f"{self.plan['net_area']:.0f} m²"),
            ("🧭", "Cephe", self.plan["facade"]),
            ("🏗️", "Bina Yaşı", f"{self.plan.get('building_age', 0)} yıl"),
        ]

        for icon, label, value in items:
            draw.text((px, py), f"{icon}  {label}", fill=GRAY, font=self._f_sm)
            draw.text((px + 180, py), value, fill=WHITE, font=self._f_md)
            py += 40

        # Hedef kat bilgisi
        py += 20
        draw.rounded_rectangle(
            [(px - 5, py), (W - 25, py + 50)],
            radius=8, fill=(*BLDG_ACTIVE, 30), outline=(*BLDG_ACTIVE, 100)
        )
        draw.text((px + 10, py + 14),
                  f"📍 {self.current_floor}. Kat — Sizin Daireniz",
                  fill=BLDG_ACTIVE, font=self._f_md)


# ─── Batch render ───────────────────────────────────────────────────────────

def generate_frames_3d(
    floor_plan: dict,
    output_dir: str,
    duration_seconds: int = 30,
    fps: int = FPS,
    progress_callback: Optional[Callable] = None,
) -> list[str]:
    """
    Tüm kare dizisini üret.
    Döndürür: PNG dosya yollarının listesi.
    """
    if not HAS_PIL:
        raise RuntimeError("Pillow kurulu değil: pip install Pillow")

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    gen = FrameGenerator3D(floor_plan, duration_seconds, fps)
    total = gen.total_frames
    paths = []

    logger.info(f"3D kare üretimi: {total} kare ({duration_seconds}s @ {fps}fps)")

    for i in range(total):
        frame_img = gen.render_frame(i)
        fpath = str(out / f"frame_{i:05d}.png")
        frame_img.save(fpath, "PNG", optimize=False)
        paths.append(fpath)

        if i % fps == 0 or i == total - 1:
            pct = int((i + 1) / total * 100)
            if progress_callback:
                progress_callback(pct, i + 1, total)

    logger.info(f"3D kare üretimi tamamlandı: {len(paths)} dosya → {out}")
    return paths
