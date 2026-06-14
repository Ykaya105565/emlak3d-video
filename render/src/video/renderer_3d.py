"""
3D Perspektif Sahne Oluşturucu — Faz 0

CityGML oda envanterindeki 2D poligonları extrude ederek
gerçek perspektif kamera ile 3D iç mekân turu üretir.

Pipeline:
  GML oda poligonları → duvar/zemin geometrisi → kamera yolu →
  painter's algorithm render → PIL PNG kareler

Gereksinim: numpy, Pillow
Yeni bağımlılık gerekmez.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Callable, Optional

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# ── Sabitler ───────────────────────────────────────────────────────────────────

W, H = 1920, 1080
FOV_RAD = math.radians(72)
ASPECT = W / H

TOUR_PRIORITY: dict[str, int] = {
    "hol": 0, "antre": 0, "koridor": 1, "salon": 2, "oturma": 2,
    "mutfak": 3, "yemek": 4, "yatak": 5, "çocuk": 6, "bebek": 7,
    "banyo": 8, "wc": 9, "tuvalet": 9, "balkon": 10,
    "depo": 11, "kiler": 11, "ısı": 12,
}

# (R,G,B) taban renkleri — oda tipine göre
_ROOM_COLORS: dict[str, tuple[int, int, int]] = {
    "salon":   (62, 84, 124),
    "oturma":  (62, 84, 124),
    "hol":     (90, 80, 68),
    "antre":   (90, 80, 68),
    "mutfak":  (68, 102, 80),
    "yemek":   (72, 110, 82),
    "yatak":   (90, 64, 92),
    "çocuk":   (96, 72, 112),
    "bebek":   (96, 72, 112),
    "banyo":   (54, 90, 112),
    "wc":      (54, 90, 112),
    "tuvalet": (54, 90, 112),
    "koridor": (78, 78, 90),
    "balkon":  (60, 112, 60),
    "depo":    (84, 84, 84),
    "kiler":   (84, 84, 84),
}
_DEFAULT_COLOR = (80, 84, 100)

LIGHT_DIR = np.array([0.55, -0.75, 1.25])          # anahtar ışık
LIGHT_DIR = LIGHT_DIR / np.linalg.norm(LIGHT_DIR)
FILL_DIR  = np.array([-0.4, 0.6, 0.7])             # dolgu ışığı
FILL_DIR  = FILL_DIR / np.linalg.norm(FILL_DIR)
FOG_COLOR = (18, 22, 40)
FOG_START, FOG_END = 2.5, 30.0


# ── Yardımcılar ────────────────────────────────────────────────────────────────

def _normalize(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v))
    return v / n if n > 1e-9 else v


def _smoothstep(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def _lerp(a: np.ndarray, b: np.ndarray, t: float) -> np.ndarray:
    return a + (b - a) * _smoothstep(t)


def _room_base_color(name: str) -> tuple[int, int, int]:
    n = name.lower()
    for k, v in _ROOM_COLORS.items():
        if k in n:
            return v
    return _DEFAULT_COLOR


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    for fp in [
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]:
        if Path(fp).exists():
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                pass
    return ImageFont.load_default()


# ── 3D Geometri ────────────────────────────────────────────────────────────────

def build_geometry(rooms: list) -> list[dict]:
    """
    Oda listesinden 3D yüz listesi üret.

    Her yüz:
      verts   : (N,3) float64 array
      normal  : (3,)  float64 array
      color   : (R,G,B) int tuple
      label   : str | None
      centroid: (3,)  float64
    """
    faces: list[dict] = []

    for room in rooms:
        poly = room.get("polygon_local_m", [])
        if len(poly) < 3:
            continue

        floor_idx = float(room.get("floor", 0))
        floor_z   = floor_idx * 3.25          # kat yüksekliği
        ceil_h    = float(room.get("ceiling_height") or 2.8)
        ceil_z    = floor_z + ceil_h

        br, bg, bb = _room_base_color(room.get("name", ""))
        name = room.get("name", "Oda")
        pts  = [(float(p[0]), float(p[1])) for p in poly]
        n    = len(pts)
        cx   = sum(p[0] for p in pts) / n
        cy   = sum(p[1] for p in pts) / n

        # — Zemin —
        floor_verts = np.array([[x, y, floor_z] for x, y in pts], dtype=np.float64)
        faces.append({
            "verts":    floor_verts,
            "normal":   np.array([0., 0., 1.], dtype=np.float64),
            "color":    (int(br * 0.48), int(bg * 0.48), int(bb * 0.48)),
            "label":    name,
            "centroid": np.array([cx, cy, floor_z + 0.02], dtype=np.float64),
        })

        # — Tavan (içten görülen → ters normal) —
        # Görsel olarak tavan ekranı kapatmasın diye yarı saydam; sadece yüksek açıdan bakarken görünür
        ceil_verts = np.array([[x, y, ceil_z] for x, y in reversed(pts)], dtype=np.float64)
        faces.append({
            "verts":    ceil_verts,
            "normal":   np.array([0., 0., -1.], dtype=np.float64),
            "color":    (int(br * 0.28), int(bg * 0.28), int(bb * 0.28)),
            "label":    None,
            "centroid": np.array([cx, cy, ceil_z - 0.02], dtype=np.float64),
        })

        # — Duvarlar —
        for i in range(n):
            x1, y1 = pts[i]
            x2, y2 = pts[(i + 1) % n]
            dx, dy = x2 - x1, y2 - y1
            length = math.hypot(dx, dy)
            if length < 1e-6:
                continue

            # İç duvar normali (sol tarafa bakan)
            nx, ny = -dy / length, dx / length

            # x-yönlü duvarlar daha parlak (yön bazlı şading)
            shading = 0.62 + 0.38 * abs(nx)
            wc = (
                min(255, int(br * shading * 1.18)),
                min(255, int(bg * shading * 1.18)),
                min(255, int(bb * shading * 1.18)),
            )
            wall_verts = np.array([
                [x1, y1, floor_z],
                [x2, y2, floor_z],
                [x2, y2, ceil_z],
                [x1, y1, ceil_z],
            ], dtype=np.float64)
            faces.append({
                "verts":    wall_verts,
                "normal":   np.array([nx, ny, 0.], dtype=np.float64),
                "color":    wc,
                "label":    None,
                "centroid": np.mean(wall_verts, axis=0),
            })

    return faces


# ── Kamera ─────────────────────────────────────────────────────────────────────

def _camera_basis(eye: np.ndarray, target: np.ndarray):
    """Kamera eksenleri → (fwd, right, up)."""
    fwd = _normalize(target - eye)
    world_up = np.array([0., 0., 1.], dtype=np.float64)
    if abs(float(np.dot(fwd, world_up))) > 0.98:
        world_up = np.array([0., 1., 0.], dtype=np.float64)
    right = _normalize(np.cross(fwd, world_up))
    up    = np.cross(right, fwd)
    return fwd, right, up


def _project(v: np.ndarray, eye: np.ndarray, fwd, right, up):
    """3D nokta → 2D ekran. None = kameranın arkasında."""
    d     = v - eye
    depth = float(np.dot(d, fwd))
    if depth < 0.10:
        return None
    x  = float(np.dot(d, right))
    y  = float(np.dot(d, up))
    th = math.tan(FOV_RAD / 2)
    sx = (x / (depth * th * ASPECT)) * W / 2 + W / 2
    sy = -(y / (depth * th))         * H / 2 + H / 2
    return sx, sy, depth


# ── Kamera yolu ────────────────────────────────────────────────────────────────

def make_camera_path(rooms: list, n_frames: int) -> list[tuple]:
    """
    Animasyon kamera yolu: aeryal tanıtım → her odada 360° tur.

    Döndürür: [(eye, target, room_name), ...] uzunluğu = n_frames
    """
    valid = [r for r in rooms if len(r.get("polygon_local_m", [])) >= 3]
    if not valid:
        eye = np.array([0., -20., 15.], dtype=np.float64)
        return [(eye, np.zeros(3, dtype=np.float64), "")] * n_frames

    # Bina merkezi & boyutu
    all_pts = np.array([
        [float(p[0]), float(p[1])]
        for r in valid for p in r["polygon_local_m"]
    ], dtype=np.float64)
    bx, by = float(np.mean(all_pts[:, 0])), float(np.mean(all_pts[:, 1]))
    radius = max(8.0, float(np.max(np.linalg.norm(all_pts - [bx, by], axis=1))))

    # Oda sıralama
    def _priority(r):
        n = r.get("name", "").lower()
        for k, v in TOUR_PRIORITY.items():
            if k in n:
                return v
        return 99

    sorted_rooms = sorted(valid, key=_priority)

    # ── Faz 1: Aeryal (%18) ───────────────────────────────────────────────────
    aerial_n = max(25, int(n_frames * 0.18))
    cam_r    = radius * 1.9

    path: list[tuple] = []
    for i in range(aerial_n):
        t     = i / max(aerial_n - 1, 1)
        angle = -math.pi / 2 + t * math.pi * 1.6      # 288° yay
        h     = radius * 1.15 - t * radius * 0.55
        eye   = np.array([
            bx + cam_r * math.cos(angle),
            by + cam_r * math.sin(angle),
            h,
        ], dtype=np.float64)
        path.append((eye, np.array([bx, by, 1.5], dtype=np.float64), ""))

    # ── Faz 2: Oda turu ───────────────────────────────────────────────────────
    room_n          = n_frames - aerial_n
    frames_per_room = room_n // max(len(sorted_rooms), 1)
    TRANS_FRAC      = 0.22   # geçiş süresi oranı

    prev_eye = path[-1][0].copy()

    for ri, room in enumerate(sorted_rooms):
        pts     = [(float(p[0]), float(p[1])) for p in room["polygon_local_m"]]
        n_pts   = len(pts)
        cx      = sum(p[0] for p in pts) / n_pts
        cy      = sum(p[1] for p in pts) / n_pts
        floor_z = float(room.get("floor", 0)) * 3.25
        eye_z   = floor_z + 1.58          # göz yüksekliği

        pts_arr  = np.array(pts, dtype=np.float64)
        r_radius = max(1.6, float(
            np.max(np.linalg.norm(pts_arr - [cx, cy], axis=1))
        ) * 0.72)

        room_eye  = np.array([cx, cy, eye_z], dtype=np.float64)
        name      = room.get("name", "Oda")

        # Son oda kalan karelerin tümünü alsın
        total_room_frames = (
            n_frames - len(path)
            if ri == len(sorted_rooms) - 1
            else frames_per_room
        )

        trans_n = max(6, int(total_room_frames * TRANS_FRAC))
        look_n  = total_room_frames - trans_n

        # — Geçiş —
        for j in range(trans_n):
            t   = j / max(trans_n - 1, 1)
            eye = _lerp(prev_eye, room_eye, t)
            # Odanın sağ tarafına bak (giriş hissi)
            ang = math.pi * 0.25 + t * math.pi * 0.25
            tgt = np.array([
                cx + r_radius * math.cos(ang),
                cy + r_radius * math.sin(ang),
                eye_z - 0.12,
            ], dtype=np.float64)
            path.append((eye, tgt, name))

        # — Odada 360° dönüş —
        start_angle = math.pi * 0.5
        sweep       = math.pi * 1.82    # ~328°

        for j in range(look_n):
            t     = j / max(look_n - 1, 1)
            angle = start_angle + t * sweep
            # Hafif dikey sallanma (daha canlı görünüm)
            dip = 0.18 * math.sin(t * math.pi)
            tgt = np.array([
                cx + r_radius * math.cos(angle),
                cy + r_radius * math.sin(angle),
                eye_z - dip,
            ], dtype=np.float64)
            path.append((room_eye.copy(), tgt, name))

        prev_eye = room_eye.copy()

    # Eksik → son pozisyonu tekrar et
    last = path[-1] if path else (np.zeros(3), np.array([0., 1., 0.]), "")
    while len(path) < n_frames:
        path.append(last)

    return path[:n_frames]


# ── Tek kare render ────────────────────────────────────────────────────────────

def render_frame(
    faces:   list[dict],
    eye:     np.ndarray,
    target:  np.ndarray,
    hud:     dict,
) -> Image.Image:
    """
    Sahneyi tek PIL karesi olarak render et.
    hud: {frame_idx, total_frames, room_name, title, crs, n_rooms}
    """
    img  = Image.new("RGB", (W, H), FOG_COLOR)
    draw = ImageDraw.Draw(img, "RGBA")

    # ── Arka plan degrade ─────────────────────────────────────────────────────
    for row in range(H):
        t  = row / H
        rc = (int(FOG_COLOR[0] + t * 6),
              int(FOG_COLOR[1] + t * 10),
              int(FOG_COLOR[2] + t * 18))
        draw.line([(0, row), (W, row)], fill=rc)

    # ── Kamera eksenleri ──────────────────────────────────────────────────────
    fwd, right, up = _camera_basis(eye, target)

    # ── Yüz derinlik sıralaması (painter: uzaktan yakına) ─────────────────────
    depth_idx: list[tuple[float, int]] = []
    for i, face in enumerate(faces):
        d = float(np.dot(face["centroid"] - eye, fwd))
        depth_idx.append((d, i))
    depth_idx.sort(key=lambda x: -x[0])   # büyükten küçüğe → en uzak önce

    # ── Yüz çizimi ────────────────────────────────────────────────────────────
    for depth_val, idx in depth_idx:
        if depth_val < 0.08:
            continue            # kameranın arkası

        face   = faces[idx]
        verts  = face["verts"]

        # — Vertex projeksiyonu —
        pts2d : list[tuple[int, int]] = []
        ddepths: list[float] = []
        ok    = True
        for v in verts:
            p = _project(v, eye, fwd, right, up)
            if p is None:
                ok = False
                break
            pts2d.append((int(p[0]), int(p[1])))
            ddepths.append(p[2])
        if not ok or len(pts2d) < 3:
            continue

        # Tamamen ekran dışı → atla
        if all(
            px < -300 or px > W + 300 or py < -300 or py > H + 300
            for px, py in pts2d
        ):
            continue

        # — Aydınlatma —
        norm     = face["normal"]
        diffuse  = max(0.0, float(np.dot(norm, LIGHT_DIR)))
        fill_dif = max(0.0, float(np.dot(norm, FILL_DIR))) * 0.3
        light    = 0.22 + diffuse * 0.62 + fill_dif

        # — Sis —
        avg_d = sum(ddepths) / len(ddepths)
        fog_t = max(0.0, min(0.88, (avg_d - FOG_START) / (FOG_END - FOG_START)))

        def _c(base: int, fog: int) -> int:
            lit = min(255, int(base * light))
            return int(lit * (1 - fog_t) + fog * fog_t)

        r, g, b = face["color"]
        fr = _c(r, FOG_COLOR[0])
        fg = _c(g, FOG_COLOR[1])
        fb = _c(b, FOG_COLOR[2])

        draw.polygon(pts2d, fill=(fr, fg, fb, 252))

        # İnce kenar çizgisi
        edge = (min(255, fr + 14), min(255, fg + 14), min(255, fb + 14), 55)
        draw.line(pts2d + [pts2d[0]], fill=edge, width=1)

    # ── HUD ───────────────────────────────────────────────────────────────────
    _draw_hud(draw, hud)
    return img


def _draw_hud(draw: ImageDraw.ImageDraw, hud: dict) -> None:
    """Üst başlık, oda adı bandı, ilerleme çubuğu, rozet."""
    f32 = _load_font(32)
    f20 = _load_font(20)
    f16 = _load_font(16)
    f56 = _load_font(56)

    # — Üst şerit —
    draw.rectangle([(0, 0), (W, 70)], fill=(0, 0, 0, 175))
    title = hud.get("title", "")
    draw.text((28, 18), title,
              fill=(240, 245, 255, 230), font=f32)
    crs_txt = f"CRS: {hud.get('crs', '?')}  ·  {hud.get('n_rooms', '?')} oda"
    draw.text((W - 20, 24), crs_txt,
              fill=(140, 175, 220, 200), font=f20, anchor="rm")

    # — Oda adı bandı (ekran ortasında) —
    room_name = hud.get("room_name", "")
    if room_name:
        lbl_y = H // 2 - 190
        # Yarı saydam arka plan
        bbox_w = len(room_name) * 28 + 60
        draw.rounded_rectangle(
            [(W // 2 - bbox_w // 2, lbl_y - 20),
             (W // 2 + bbox_w // 2, lbl_y + 52)],
            radius=10, fill=(0, 0, 0, 140),
        )
        # Gölge + metin
        draw.text((W // 2 + 2, lbl_y + 2), room_name,
                  fill=(0, 0, 0, 110), font=f56, anchor="mt")
        draw.text((W // 2, lbl_y), room_name,
                  fill=(255, 255, 255, 230), font=f56, anchor="mt")

    # — Alt şerit —
    draw.rectangle([(0, H - 56), (W, H)], fill=(0, 0, 0, 175))

    # İlerleme çubuğu
    total = max(hud.get("total_frames", 1), 1)
    pct   = hud["frame_idx"] / total
    bar_x0, bar_x1 = 120, W - 120
    bar_y0, bar_y1 = H - 38, H - 22
    draw.rounded_rectangle([(bar_x0, bar_y0), (bar_x1, bar_y1)],
                           radius=4, fill=(38, 42, 62, 220))
    fill_w = int((bar_x1 - bar_x0) * pct)
    if fill_w > 0:
        draw.rounded_rectangle(
            [(bar_x0, bar_y0), (bar_x0 + fill_w, bar_y1)],
            radius=4, fill=(72, 140, 228, 215),
        )

    # "3D GML" rozeti
    draw.rounded_rectangle([(18, H - 46), (110, H - 14)],
                           radius=5, fill=(42, 88, 150, 210))
    draw.text((64, H - 30), "3D · GML",
              fill=(180, 222, 255, 240), font=f16, anchor="mm")

    # Temsilîdir
    draw.text((W - 20, H - 28), "Temsilîdir",
              fill=(110, 115, 130, 170), font=f16, anchor="rm")


# ── Ana üretim fonksiyonu ──────────────────────────────────────────────────────

def generate_3d_frames(
    inventory:         dict,
    output_dir:        str,
    duration_seconds:  int = 30,
    fps:               int = 25,
    progress_callback: Optional[Callable] = None,
) -> list[str]:
    """
    GML envanterinden 3D perspektif kare dizisi üret.

    Döndürür: PNG dosya yolları listesi (frame_00000.png, ...)
    """
    from loguru import logger

    rooms = inventory.get("rooms", [])
    valid_rooms = [r for r in rooms if len(r.get("polygon_local_m", [])) >= 3]
    if not valid_rooms:
        raise ValueError(f"3D render için polygon_local_m verisi bulunan oda yok (toplam {len(rooms)} oda)")

    out      = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    n_frames = duration_seconds * fps
    title    = inventory.get("source_file", "Bina").replace(".gml", "")
    crs      = inventory.get("crs", "?")
    n_rooms  = len(valid_rooms)

    logger.info(f"3D render: {n_rooms} oda, {n_frames} kare @ {fps}fps")

    faces    = build_geometry(valid_rooms)
    cam_path = make_camera_path(valid_rooms, n_frames)
    paths    = []

    report_every = max(1, fps)   # her saniyede bir callback

    for i, (eye, target, room_name) in enumerate(cam_path):
        hud = {
            "frame_idx":   i,
            "total_frames": n_frames,
            "room_name":   room_name,
            "title":       title,
            "crs":         crs,
            "n_rooms":     n_rooms,
        }
        img   = render_frame(faces, eye, target, hud)
        fpath = str(out / f"frame_{i:05d}.png")
        img.save(fpath, "PNG", optimize=False)
        paths.append(fpath)

        if i % report_every == 0:
            pct = int(i / n_frames * 100)
            logger.debug(f"  3D kare {i+1}/{n_frames} ({pct}%) — {room_name}")
            if progress_callback:
                progress_callback(pct, i + 1, n_frames)

    logger.info(f"3D render tamamlandı: {len(paths)} kare → {out}")
    return paths
