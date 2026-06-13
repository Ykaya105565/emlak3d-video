"""
Villa Hayali Pipeline — Faz 2

Girdi: Arsa bilgileri (TAKS, KAKS, çekme mesafeleri, m²) + GML koordinatları (varsa)
Çıktı:
  - Yasal yapılaşma zarfı (inşaat alanı max = parcel × TAKS)
  - Örnek villa yerleşimi (2D kat planı + basit 3D kütle)
  - Render karesi (PIL/Pillow 1920×1080)
  - "temsilîdir" + imar bilgisi overlay

ÖNEMLİ: Tüm değerler kullanıcıdan alınan veya imar planından gelen gerçek verilerdir.
  3D modeller ve görseller temsilîdir; ruhsat öncesi proje müellifi onayı gerekir.
"""

from __future__ import annotations
import math
from pathlib import Path
from typing import Optional

from loguru import logger


# ─── İmar hesaplama ─────────────────────────────────────────────────────────

def compute_building_envelope(
    parcel_area_m2: float,
    taks: float,          # Taban Alan Katsayısı (0-1)
    kaks: float,          # Kat Alan Katsayısı (= emsal)
    setback_front: float = 5.0,
    setback_rear: float = 3.0,
    setback_left: float = 3.0,
    setback_right: float = 3.0,
    floor_height_m: float = 3.0,
) -> dict:
    """
    İmar parametrelerinden yapılaşma zarfını hesapla.

    Döndürür:
      max_footprint_m2: İzin verilen maksimum taban alanı (TAKS × parsel)
      max_total_area_m2: İzin verilen maksimum toplam kapalı alan (KAKS × parsel = emsal)
      max_floors: Maksimum kat sayısı (toplam alan / taban alan, yuvarlanmış)
      max_height_m: Yaklaşık maksimum yükseklik
      footprint_ratio: Gerçekleşen taban/parsel oranı
      envelope_polygon_local: Yapılaşma zarfı köşeleri (yerel metre, köken = parsel sol-alt)
    """
    if taks <= 0 or taks > 1:
        raise ValueError(f"TAKS 0-1 aralığında olmalı, alınan: {taks}")
    if kaks <= 0:
        raise ValueError(f"KAKS pozitif olmalı, alınan: {kaks}")

    max_footprint = parcel_area_m2 * taks
    max_total_area = parcel_area_m2 * kaks
    max_floors = max(1, math.floor(max_total_area / max_footprint)) if max_footprint > 0 else 1
    max_height = max_floors * floor_height_m

    # Basit dikdörtgen parsel varsayımı (gerçek GML poligonu yoksa)
    parcel_side = math.sqrt(parcel_area_m2)
    # Bina taban dikdörtgeni (çekme mesafeleri sonrası kullanılabilir alan)
    bldg_w = max(0.0, parcel_side - setback_left - setback_right)
    bldg_d = max(0.0, parcel_side - setback_front - setback_rear)
    actual_footprint = min(bldg_w * bldg_d, max_footprint)

    # Zarf poligonu (yerel metre, parsel köşesi = 0,0)
    x0 = setback_left
    y0 = setback_rear
    x1 = x0 + bldg_w
    y1 = y0 + bldg_d
    envelope_polygon = [
        [x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]
    ]

    return {
        "parcel_area_m2": round(parcel_area_m2, 1),
        "taks": taks,
        "kaks": kaks,
        "max_footprint_m2": round(max_footprint, 1),
        "actual_footprint_m2": round(actual_footprint, 1),
        "max_total_area_m2": round(max_total_area, 1),
        "max_floors": max_floors,
        "max_height_m": round(max_height, 1),
        "setbacks": {
            "front": setback_front,
            "rear": setback_rear,
            "left": setback_left,
            "right": setback_right,
        },
        "envelope_polygon_local": envelope_polygon,
        "parcel_polygon_local": [
            [0, 0], [parcel_side, 0],
            [parcel_side, parcel_side], [0, parcel_side], [0, 0]
        ],
        "parcel_side_m": round(parcel_side, 1),
    }


# ─── PIL görselleştirme ──────────────────────────────────────────────────────

def render_villa_frame(
    envelope: dict,
    listing_data: Optional[dict] = None,
    output_path: Optional[str] = None,
) -> "PIL.Image.Image":
    """
    Villa Hayali: arsa + yapılaşma zarfı + imar bilgisi → 1920×1080 PNG kare.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        raise RuntimeError("Pillow kurulu değil: pip install Pillow")

    W, H = 1920, 1080
    img = Image.new("RGB", (W, H), (15, 18, 35))
    draw = ImageDraw.Draw(img, "RGBA")

    # Font yardımcısı
    def _font(size):
        for p in [
            "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/arial.ttf",
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

    f_sm = _font(18); f_md = _font(28); f_lg = _font(42); f_xl = _font(60)

    # ── Header ──────────────────────────────────────────────────────────────
    draw.rectangle([(0, 0), (W, 80)], fill=(22, 26, 50))
    draw.text((30, 22), "VILLA HAYALİ", fill=(139, 92, 246), font=f_lg)
    title = (listing_data or {}).get("title", "İmar Zarfı Analizi")
    draw.text((340, 28), title[:70], fill=(200, 210, 230), font=f_md)
    draw.line([(0, 80), (W, 80)], fill=(40, 45, 80), width=1)

    # ── Sol panel: Arsa planı ────────────────────────────────────────────────
    PAD = 120
    PLAN_X, PLAN_Y = PAD, 100
    PLAN_W, PLAN_H = 820, 800

    # Koordinat dönüşümü: yerel metre → piksel
    parcel_side = envelope["parcel_side_m"]
    scale = min(PLAN_W / parcel_side, PLAN_H / parcel_side) * 0.85
    ox = PLAN_X + PLAN_W // 2 - parcel_side * scale // 2
    oy = PLAN_Y + PLAN_H // 2 + parcel_side * scale // 2  # Y ters

    def to_px(x, y):
        return int(ox + x * scale), int(oy - y * scale)

    # Arsa
    parcel_pts = [to_px(*p) for p in envelope["parcel_polygon_local"][:-1]]
    draw.polygon(parcel_pts, fill=(30, 40, 25, 160), outline=(100, 200, 80), width=2)

    # Çekme mesafesi göstergeleri
    s = envelope["setbacks"]
    draw.line([to_px(0, s["rear"]), to_px(parcel_side, s["rear"])],
              fill=(60, 80, 50, 120), width=1)
    draw.line([to_px(0, parcel_side - s["front"]), to_px(parcel_side, parcel_side - s["front"])],
              fill=(60, 80, 50, 120), width=1)

    # Yapılaşma zarfı
    env_pts = [to_px(*p) for p in envelope["envelope_polygon_local"][:-1]]
    if len(env_pts) >= 3:
        draw.polygon(env_pts, fill=(139, 92, 246, 80), outline=(139, 92, 246), width=3)

    # Etiketler
    cx_px, cy_px = to_px(parcel_side / 2, parcel_side / 2)
    draw.text((cx_px, cy_px), "YAPI\nZARFI", fill=(200, 180, 255),
              font=f_sm, anchor="mm")

    # Çekme mesafesi ok ve değer
    fx, fy = to_px(parcel_side / 2, 0)
    draw.text((fx, fy + 10), f"↑ ön: {s['front']}m", fill=(120, 200, 100), font=_font(14), anchor="mt")
    bx, by = to_px(parcel_side / 2, parcel_side)
    draw.text((bx, by - 10), f"↓ arka: {s['rear']}m", fill=(120, 200, 100), font=_font(14), anchor="mb")

    # "KuzeyOk" göstergesi
    draw.text((PLAN_X + PLAN_W - 40, PLAN_Y + 20), "N↑", fill=(180, 200, 255), font=f_sm)

    # ── Sağ panel: İmar tablosu ──────────────────────────────────────────────
    TX = 1000
    draw.rectangle([(TX - 20, 90), (W - 20, H - 60)], fill=(22, 26, 50))

    rows = [
        ("Parsel Alanı",     f"{envelope['parcel_area_m2']:,.0f} m²",  (200, 220, 240)),
        ("TAKS",             f"{envelope['taks']:.2f}",                 (200, 220, 240)),
        ("KAKS (Emsal)",     f"{envelope['kaks']:.2f}",                 (200, 220, 240)),
        ("Maks. Taban",      f"{envelope['max_footprint_m2']:,.0f} m²", (139, 200, 120)),
        ("Maks. Toplam",     f"{envelope['max_total_area_m2']:,.0f} m²",(139, 200, 120)),
        ("Maks. Kat",        str(envelope["max_floors"]),               (255, 200, 80)),
        ("Maks. Yükseklik",  f"{envelope['max_height_m']:.1f} m",      (255, 200, 80)),
        ("Ön Çekme",         f"{s['front']:.1f} m",                    (180, 180, 220)),
        ("Arka Çekme",       f"{s['rear']:.1f} m",                     (180, 180, 220)),
        ("Sol Çekme",        f"{s['left']:.1f} m",                     (180, 180, 220)),
        ("Sağ Çekme",        f"{s['right']:.1f} m",                    (180, 180, 220)),
    ]

    draw.text((TX, 110), "İMAR BİLGİLERİ", fill=(139, 92, 246), font=f_lg)
    draw.line([(TX, 165), (W - 30, 165)], fill=(40, 45, 80), width=1)

    y = 185
    for label, value, color in rows:
        draw.text((TX, y), label + ":", fill=(130, 140, 160), font=f_sm)
        draw.text((TX + 280, y), value, fill=color, font=f_md)
        y += 52

    # Uyarı kutusu
    warn_y = y + 20
    draw.rounded_rectangle([(TX - 10, warn_y), (W - 30, warn_y + 100)],
                            radius=8, fill=(40, 30, 0, 200), outline=(200, 150, 0))
    draw.text((TX + 5, warn_y + 10),
              "★  Bu analiz bilgi amaçlıdır. Yapı ruhsatı için yetkili\n"
              "   mimar/mühendis ile çalışınız. Tüm görseller temsilîdir.",
              fill=(200, 160, 50), font=_font(16))

    # ── Footer ─────────────────────────────────────────────────────────────
    footer_y = H - 50
    draw.line([(0, footer_y), (W, footer_y)], fill=(40, 45, 80), width=1)
    draw.rectangle([(0, footer_y), (W, H)], fill=(10, 12, 25))
    draw.text((20, footer_y + 14),
              "Villa Hayali  |  İmar zarfı analizi  |  Görseller temsilîdir  |"
              "  Ruhsat öncesi müellif onayı gereklidir",
              fill=(60, 70, 90), font=_font(14))

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        img.save(str(out), "PNG")
        logger.info(f"Villa Hayali karesi: {out}")

    return img


def generate_villa_video(
    parcel_area_m2: float,
    taks: float,
    kaks: float,
    output_mp4: str,
    listing_data: Optional[dict] = None,
    setback_front: float = 5.0,
    setback_rear: float = 3.0,
    setback_left: float = 3.0,
    setback_right: float = 3.0,
    duration_seconds: int = 30,
    fps: int = 25,
) -> str:
    """
    Villa Hayali kısa video (statik imar analiz planı + animasyonlu geçiş).
    Döndürür: mp4_path
    """
    envelope = compute_building_envelope(
        parcel_area_m2, taks, kaks,
        setback_front, setback_rear, setback_left, setback_right,
    )

    out = Path(output_mp4).parent / "villa_tmp"
    out.mkdir(parents=True, exist_ok=True)

    frame_img = render_villa_frame(envelope, listing_data)
    total_frames = duration_seconds * fps

    from PIL import Image
    import numpy as np

    # Basit animasyon: fade-in (25 kare) + statik + fade-out (25 kare)
    frame_paths = []
    for i in range(total_frames):
        fade = 1.0
        if i < 25:
            fade = i / 25
        elif i > total_frames - 25:
            fade = (total_frames - i) / 25

        if fade < 1.0:
            black = Image.new("RGB", frame_img.size, (0, 0, 0))
            blended = Image.blend(black, frame_img, alpha=fade)
        else:
            blended = frame_img

        fpath = str(out / f"frame_{i:05d}.png")
        blended.save(fpath, "PNG")
        frame_paths.append(fpath)

    # MP4 kodla
    try:
        import subprocess
        pattern = str(out / "frame_%05d.png")
        cmd = [
            "ffmpeg", "-framerate", str(fps), "-i", pattern,
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-crf", "23", "-preset", "fast",
            "-movflags", "+faststart", "-y", output_mp4,
        ]
        subprocess.run(cmd, capture_output=True, check=True, timeout=120)
    except Exception:
        import imageio.v2 as imageio
        writer = imageio.get_writer(output_mp4, fps=fps, codec="libx264", quality=7,
                                    pixelformat="yuv420p", macro_block_size=16)
        for fp in frame_paths:
            writer.append_data(np.array(Image.open(fp).convert("RGB")))
        writer.close()

    # Temizlik
    import shutil
    shutil.rmtree(str(out), ignore_errors=True)

    logger.info(f"Villa Hayali video: {output_mp4}")
    return output_mp4
