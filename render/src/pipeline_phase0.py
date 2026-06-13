"""
Faz 0 — Anahtarsız tam boru hattı.

GML dosyası → oda envanteri → PNG kare dizisi → TTS anlatısı → MP4

Hiçbir API anahtarı gerekmez:
  - GML ayrıştırma: lxml + pyproj + shapely
  - Kare üretimi: Pillow
  - TTS: gTTS (internet) → pyttsx3 (yerel) → sessizlik
  - MP4 kodlama: imageio[ffmpeg]
"""

from __future__ import annotations
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from loguru import logger

# Proje köküne sys.path ekle (doğrudan çalıştırma için)
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

FPS = 25
DEFAULT_DURATION = 30  # saniye


def run_phase0(
    gml_path: str,
    output_dir: str,
    duration: int = DEFAULT_DURATION,
    fps: int = FPS,
    listing_info: Optional[dict] = None,
    tts_provider: str = "auto",
    progress_cb: Optional[Callable[[str, int], None]] = None,
) -> dict:
    """
    Tam Faz 0 boru hattını çalıştır.

    Döndürür:
    {
      "mp4_path": "...",
      "inventory_path": "...",
      "frames_dir": "...",
      "audio_path": "...",
      "duration": int,
      "room_count": int,
      "epsg": int|None,
      "crs": str,
    }
    """

    def _progress(stage: str, pct: int):
        logger.info(f"[{pct:3d}%] {stage}")
        if progress_cb:
            progress_cb(stage, pct)

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # ── 1. GML ayrıştır ────────────────────────────────────────────────────
    _progress("GML ayrıştırılıyor", 5)
    from render.src.gml.parse import parse_gml_file
    inventory = parse_gml_file(gml_path)

    inv_path = str(out / "inventory.json")
    with open(inv_path, "w", encoding="utf-8") as f:
        json.dump(inventory, f, ensure_ascii=False, indent=2)

    room_count = inventory.get("room_count", 0)
    crs = inventory.get("crs", "Bilinmeyen")
    epsg = inventory.get("epsg")
    _progress(f"GML ayrıştırıldı: {room_count} oda, CRS={crs}", 15)

    # ── 2. PNG kare dizisi üret ─────────────────────────────────────────────
    _progress("Kare dizisi üretiliyor (PIL)", 20)
    frames_dir = str(out / "frames")
    from render.src.video.frame_generator import generate_frames

    def _frame_cb(pct: int, cur: int, total: int):
        # 20–65 arası aralığa dönüştür
        mapped = 20 + int(pct * 0.45)
        _progress(f"Kare {cur}/{total}", mapped)

    frame_paths = generate_frames(
        inventory=inventory,
        output_dir=frames_dir,
        duration_seconds=duration,
        fps=fps,
        progress_callback=_frame_cb,
    )
    _progress(f"{len(frame_paths)} kare üretildi", 65)

    # ── 3. TTS anlatı ───────────────────────────────────────────────────────
    _progress("TTS anlatısı oluşturuluyor", 68)
    from render.src.audio.tts import build_scenario, synthesize_speech, mix_audio

    scenario = build_scenario(inventory, listing_info)
    _progress(f"Senaryo: {scenario[:80]}...", 70)

    speech_path = synthesize_speech(scenario, str(out / "speech.mp3"), provider=tts_provider)

    # Müzik karıştırma (varsa)
    music_path = os.environ.get("BACKGROUND_MUSIC_PATH") or _find_local_music()
    audio_path = str(out / "audio_final.mp3")
    actual_audio = mix_audio(speech_path, music_path, audio_path, duration)
    if actual_audio:
        audio_path = actual_audio
    _progress("Ses hazır", 78)

    # ── 4. MP4 kodla ────────────────────────────────────────────────────────
    _progress("MP4 kodlanıyor", 80)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    mp4_path = str(out / f"tour_{timestamp}.mp4")

    audio_for_encode = audio_path if Path(audio_path).exists() else None
    _encode_mp4(frame_paths, audio_for_encode, mp4_path, fps, _progress)
    _progress("MP4 hazır", 98)

    # ── 5. Temizlik ─────────────────────────────────────────────────────────
    size_mb = Path(mp4_path).stat().st_size / (1024 * 1024)
    _progress(f"Tamamlandı: {mp4_path} ({size_mb:.1f} MB)", 100)

    return {
        "mp4_path": mp4_path,
        "inventory_path": inv_path,
        "frames_dir": frames_dir,
        "audio_path": audio_path,
        "duration": duration,
        "room_count": room_count,
        "epsg": epsg,
        "crs": crs,
        "file_size_mb": round(size_mb, 2),
    }


def _encode_mp4(
    frame_paths: list[str],
    audio_path: str,
    output_path: str,
    fps: int,
    progress_cb: Callable,
) -> None:
    """
    PNG kare dizisi + ses → MP4.
    Önce ffmpeg (sistem), sonra imageio[ffmpeg] dene.
    """
    # Yöntem 1: sistem ffmpeg
    try:
        _encode_with_ffmpeg_cli(frame_paths, audio_path, output_path, fps)
        return
    except Exception as e:
        logger.warning(f"Sistem ffmpeg başarısız: {e} — imageio[ffmpeg] deneniyor")

    # Yöntem 2: imageio[ffmpeg]
    try:
        _encode_with_imageio(frame_paths, audio_path, output_path, fps, progress_cb)
        return
    except Exception as e:
        logger.error(f"imageio ffmpeg başarısız: {e}")
        raise RuntimeError("MP4 kodlama başarısız — ffmpeg veya imageio[ffmpeg] kurulu değil")


def _encode_with_ffmpeg_cli(
    frame_paths: list[str],
    audio_path: str,
    output_path: str,
    fps: int,
) -> None:
    """Sistem ffmpeg ile kare dizisinden MP4 üret."""
    import subprocess
    frames_dir = str(Path(frame_paths[0]).parent)
    pattern = str(Path(frames_dir) / "frame_%05d.png")

    cmd = [
        "ffmpeg",
        "-framerate", str(fps),
        "-i", pattern,
    ]
    if audio_path and Path(audio_path).exists():
        cmd += ["-i", audio_path, "-c:a", "aac", "-shortest"]

    cmd += [
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-crf", "23",
        "-preset", "fast",
        "-movflags", "+faststart",
        "-y", output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg hata: {result.stderr[-500:]}")
    logger.info(f"ffmpeg CLI başarılı: {output_path}")


def _encode_with_imageio(
    frame_paths: list[str],
    audio_path: str,
    output_path: str,
    fps: int,
    progress_cb: Callable,
) -> None:
    """imageio[ffmpeg] ile kare dizisinden MP4 üret (ses desteği sınırlı)."""
    import imageio.v2 as imageio
    import numpy as np
    from PIL import Image

    total = len(frame_paths)
    writer = imageio.get_writer(
        output_path,
        fps=fps,
        codec="libx264",
        quality=7,
        pixelformat="yuv420p",
        macro_block_size=16,
        ffmpeg_params=["-movflags", "+faststart"],
    )
    try:
        for i, fp in enumerate(frame_paths):
            img = np.array(Image.open(fp).convert("RGB"))
            writer.append_data(img)
            if i % (fps * 2) == 0:
                pct = 80 + int((i / total) * 15)
                progress_cb(f"MP4 kodlanıyor {i}/{total}", pct)
    finally:
        writer.close()

    # Ses ekle (ayrı ffmpeg çağrısı)
    if Path(audio_path).exists():
        _mux_audio(output_path, audio_path)


def _mux_audio(video_path: str, audio_path: str) -> None:
    """Video dosyasına ses ekle (yerinde)."""
    import subprocess
    tmp = video_path + ".tmp.mp4"
    cmd = [
        "ffmpeg", "-i", video_path, "-i", audio_path,
        "-c:v", "copy", "-c:a", "aac", "-shortest",
        "-movflags", "+faststart", "-y", tmp,
    ]
    try:
        subprocess.run(cmd, capture_output=True, check=True, timeout=120)
        shutil.move(tmp, video_path)
        logger.info("Ses eklendi")
    except Exception as e:
        logger.warning(f"Ses ekleme başarısız: {e} — video sessiz kalacak")
        if Path(tmp).exists():
            os.unlink(tmp)


def _find_local_music() -> Optional[str]:
    """Proje içindeki telifsiz müzik dosyasını bul."""
    candidates = [
        _ROOT / "render" / "assets" / "music" / "background.mp3",
        _ROOT / "render" / "assets" / "music" / "background.ogg",
        _ROOT / "assets" / "music" / "background.mp3",
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    return None


# ── CLI girişi ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Faz 0 Anahtarsız Pipeline")
    parser.add_argument("gml", help="GML dosya yolu")
    parser.add_argument("output", help="Çıktı klasörü")
    parser.add_argument("--duration", type=int, default=DEFAULT_DURATION, help="Video süresi (saniye)")
    parser.add_argument("--fps", type=int, default=FPS)
    parser.add_argument("--tts", default="auto", choices=["auto", "gtts", "pyttsx3", "silent"])
    args = parser.parse_args()

    result = run_phase0(
        gml_path=args.gml,
        output_dir=args.output,
        duration=args.duration,
        fps=args.fps,
        tts_provider=args.tts,
    )
    print("\n=== SONUÇ ===")
    for k, v in result.items():
        print(f"  {k}: {v}")
