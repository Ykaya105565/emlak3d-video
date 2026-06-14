"""
Demo Sunucu — Faz 0 web arayüzü için lokal FastAPI backend.
Port: 8080   (prod backend 8000'de; bu sunucu ayrı ve bağımsız)

Başlatma:
  .venv/Scripts/python demo_server.py
  veya
  uvicorn demo_server:app --port 8080 --reload
"""

from __future__ import annotations
import os
import sys
import tempfile
import threading
import uuid
from pathlib import Path
from typing import Optional

# Proje kökünü Python yoluna ekle
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from loguru import logger

app = FastAPI(title="Emlak Demo Sunucu", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Job durumu — in-memory (demo amaçlı)
JOBS: dict[str, dict] = {}

STAGE_ORDER = ["hazırlanıyor", "render ediliyor", "ses oluşturuluyor", "mp4 hazırlanıyor", "tamamlandı"]


def _pct_to_stage(pct: int) -> str:
    if pct < 18:
        return "hazırlanıyor"
    elif pct < 65:
        return "render ediliyor"
    elif pct < 78:
        return "ses oluşturuluyor"
    elif pct < 98:
        return "mp4 hazırlanıyor"
    return "tamamlandı"


def _run_render(
    job_id: str,
    gml_path: str,
    output_dir: str,
    duration: int,
    fps: int,
    tts: str,
    listing_info: Optional[dict],
):
    """Arka plan thread: pipeline_phase0.run_phase0 çalıştır."""
    JOBS[job_id]["status"] = "running"
    JOBS[job_id]["stage"] = "hazırlanıyor"
    JOBS[job_id]["pct"] = 0

    def _progress(stage_detail: str, pct: int):
        named_stage = _pct_to_stage(pct)
        JOBS[job_id]["stage"] = named_stage
        JOBS[job_id]["pct"] = pct
        JOBS[job_id]["detail"] = stage_detail

    try:
        from render.src.pipeline_phase0 import run_phase0
        result = run_phase0(
            gml_path=gml_path,
            output_dir=output_dir,
            duration=duration,
            fps=fps,
            listing_info=listing_info,
            tts_provider=tts,
            progress_cb=_progress,
        )
        JOBS[job_id].update({
            "status": "done",
            "stage": "tamamlandı",
            "pct": 100,
            "mp4_path": result.get("mp4_path"),
            "room_count": result.get("room_count"),
            "crs": result.get("crs"),
            "epsg": result.get("epsg"),
            "file_size_mb": result.get("file_size_mb"),
        })
        logger.success(f"[{job_id[:8]}] MP4 hazır: {result.get('mp4_path')}")
    except Exception as e:
        logger.error(f"[{job_id[:8]}] Render hatası: {e}")
        JOBS[job_id]["status"] = "error"
        JOBS[job_id]["error"] = str(e)
    finally:
        try:
            Path(gml_path).unlink(missing_ok=True)
        except Exception:
            pass


@app.get("/demo/health")
def health():
    return {"status": "ok", "jobs": len(JOBS)}


@app.post("/demo/render")
async def start_render(
    gml: UploadFile = File(...),
    duration: int = Form(30),
    fps: int = Form(25),
    tts: str = Form("gtts"),
    title: str = Form(""),
    taks: float = Form(0.0),
    kaks: float = Form(0.0),
    max_kat: int = Form(0),
):
    """GML yükle → render başlat → job_id döndür."""
    # GML'i geçici dosyaya kaydet
    suffix = Path(gml.filename or "upload.gml").suffix or ".gml"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir=str(ROOT / "output"))
    content = await gml.read()
    tmp.write(content)
    tmp.close()

    job_id = str(uuid.uuid4())
    output_dir = str(ROOT / "output" / f"demo_{job_id[:8]}_{duration}s")
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # listing_info — TAKS/KAKS/başlık TTS senaryosuna geçer
    listing_info: dict = {}
    if title:
        listing_info["title"] = title
    if taks:
        listing_info["taks"] = taks
    if kaks:
        listing_info["kaks"] = kaks
    if max_kat:
        listing_info["max_kat"] = max_kat

    JOBS[job_id] = {
        "status": "starting",
        "stage": "hazırlanıyor",
        "pct": 0,
        "detail": "",
        "mp4_path": None,
        "error": None,
        "room_count": None,
        "crs": None,
        "epsg": None,
        "file_size_mb": None,
        "gml_name": gml.filename or "upload.gml",
        "output_dir": output_dir,
    }

    thread = threading.Thread(
        target=_run_render,
        args=(job_id, tmp.name, output_dir, duration, fps, tts, listing_info or None),
        daemon=True,
    )
    thread.start()
    logger.info(f"[{job_id[:8]}] Render başlatıldı: {gml.filename}, {duration}s, TTS={tts}")
    return {"job_id": job_id}


@app.get("/demo/status/{job_id}")
def get_status(job_id: str):
    """Render durumunu döndür (polling endpoint)."""
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="İş bulunamadı")
    return {
        "status": job["status"],            # starting | running | done | error
        "stage": job["stage"],              # hazırlanıyor | render ediliyor | ...
        "pct": job["pct"],
        "detail": job.get("detail", ""),
        "has_mp4": job["mp4_path"] is not None,
        "error": job.get("error"),
        "room_count": job.get("room_count"),
        "crs": job.get("crs"),
        "epsg": job.get("epsg"),
        "file_size_mb": job.get("file_size_mb"),
        "gml_name": job.get("gml_name"),
    }


@app.get("/demo/download/{job_id}")
def download_mp4(job_id: str):
    """Tamamlanan render'ın MP4 dosyasını indir."""
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="İş bulunamadı")
    mp4 = job.get("mp4_path")
    if not mp4 or not Path(mp4).exists():
        raise HTTPException(status_code=404, detail="MP4 henüz hazır değil")
    return FileResponse(
        mp4,
        media_type="video/mp4",
        filename=Path(mp4).name,
        headers={"Content-Disposition": f'attachment; filename="{Path(mp4).name}"'},
    )


if __name__ == "__main__":
    import uvicorn
    # output/ klasörünü hazırla
    (ROOT / "output").mkdir(exist_ok=True)
    logger.info("Demo sunucu başlatılıyor: http://localhost:8080")
    logger.info("Demo arayüzü: http://localhost:5173/demo")
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")
