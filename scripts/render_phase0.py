#!/usr/bin/env python3
"""
Faz 0 örnek video üreticisi.

Kullanım:
  python scripts/render_phase0.py <gml_dosyası> [seçenekler]

Örnekler:
  python scripts/render_phase0.py sample_data/M-12345.gml
  python scripts/render_phase0.py sample_data/M-12345.gml --duration 60 --output out/video
  python scripts/render_phase0.py sample_data/M-12345.gml --tts silent --fps 25

API anahtarı gerekmez. Gereksinimler:
  pip install -r render/requirements.txt
"""

from __future__ import annotations
import argparse
import json
import os
import sys
import time
from pathlib import Path

# Proje kökünü Python yoluna ekle
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from loguru import logger


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Faz 0: GML → MP4 anahtarsız video üretici",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("gml", help="CityGML dosya yolu (.gml)")
    p.add_argument(
        "--output", "-o",
        default=None,
        help="Çıktı klasörü (varsayılan: output/<gml_adı>_<timestamp>)",
    )
    p.add_argument(
        "--duration", "-d",
        type=int, default=30,
        help="Video süresi saniye (varsayılan: 30)",
    )
    p.add_argument(
        "--fps",
        type=int, default=25,
        help="Kare hızı (varsayılan: 25)",
    )
    p.add_argument(
        "--tts",
        default="auto",
        choices=["auto", "gtts", "pyttsx3", "silent"],
        help="TTS sağlayıcı (varsayılan: auto — gtts→pyttsx3→silent)",
    )
    p.add_argument(
        "--title",
        default=None,
        help="Anlatıda kullanılacak ilan başlığı",
    )
    p.add_argument(
        "--keep-frames",
        action="store_true",
        help="MP4 sonrası PNG karelerini sil (varsayılan: sil)",
    )
    p.add_argument(
        "--verbose", "-v",
        action="store_true",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()

    if not args.verbose:
        logger.remove()
        logger.add(sys.stderr, level="INFO",
                   format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")

    gml_path = Path(args.gml)
    if not gml_path.exists():
        logger.error(f"GML dosyası bulunamadı: {gml_path}")
        return 1

    import datetime
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    if args.output:
        out_dir = Path(args.output)
    else:
        out_dir = ROOT / "output" / f"{gml_path.stem}_{ts}"

    out_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"GML: {gml_path.name}")
    logger.info(f"Çıktı: {out_dir}")
    logger.info(f"Süre: {args.duration}s @ {args.fps}fps, TTS: {args.tts}")

    listing_info = None
    if args.title:
        listing_info = {"title": args.title}

    t0 = time.time()
    try:
        from render.src.pipeline_phase0 import run_phase0

        result = run_phase0(
            gml_path=str(gml_path),
            output_dir=str(out_dir),
            duration=args.duration,
            fps=args.fps,
            listing_info=listing_info,
            tts_provider=args.tts,
        )
    except Exception as e:
        logger.exception(f"Pipeline hatası: {e}")
        return 2

    elapsed = time.time() - t0

    # Kareler temizlensin mi?
    if not args.keep_frames:
        import shutil
        frames_dir = result.get("frames_dir", "")
        if frames_dir and Path(frames_dir).exists():
            shutil.rmtree(frames_dir)
            logger.info("PNG kareler temizlendi")

    # Özet
    mp4 = result.get("mp4_path", "")
    print("\n" + "=" * 60)
    print("  FAZ 0 TAMAMLANDI")
    print("=" * 60)
    print(f"  MP4       : {mp4}")
    print(f"  Boyut     : {result.get('file_size_mb', '?')} MB")
    print(f"  Oda sayısı: {result.get('room_count', '?')}")
    print(f"  CRS       : {result.get('crs', '?')} (EPSG:{result.get('epsg', '?')})")
    print(f"  Süre      : {elapsed:.1f}s")
    print("=" * 60)

    # Manifest yaz
    manifest_path = out_dir / "manifest.json"
    result["render_elapsed_seconds"] = round(elapsed, 2)
    result["gml_source"] = str(gml_path.resolve())
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    logger.info(f"Manifest: {manifest_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
