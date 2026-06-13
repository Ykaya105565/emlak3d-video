"""
Ana render pipeline orkestratörü.
HTTP API olarak da çalışır (FastAPI, port 8001).
Celery worker'dan tetiklenir.
"""
from __future__ import annotations
import asyncio
import json
import os
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Optional

import boto3
from botocore.client import Config
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from loguru import logger

from src.gml.parse import parse_gml_file
from src.gml.measure import build_narration_data
from src.gml.gltf_export import export_gltf
from src.audio.tts import synthesize_speech, mix_audio

app = FastAPI(title="Emlak Render Worker")

MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS = os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET = os.environ.get("MINIO_SECRET_KEY", "minioadmin123")
BUCKET_GML = os.environ.get("MINIO_BUCKET_GML", "gml-files")
BUCKET_VIDEOS = os.environ.get("MINIO_BUCKET_VIDEOS", "rendered-videos")
TMP_BASE = os.environ.get("RENDER_OUTPUT_DIR", "/tmp/renders")


class RenderRequest(BaseModel):
    job_id: str
    listing_id: str
    duration_seconds: int = 30
    resolution: str = "1080p"
    orientation: str = "16:9"
    is_watermarked: bool = True
    interior_source: str = "listing_data"
    gml_file_key: Optional[str] = None
    room_inventory: Optional[dict] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    listing_data: Optional[dict] = None
    photo_keys: Optional[list[str]] = None


class RenderResponse(BaseModel):
    job_id: str
    output_key: str
    scenario_text: str
    status: str = "done"


class VillaRequest(BaseModel):
    job_id: str
    listing_id: str
    parcel_area_m2: float
    taks: float
    kaks: float
    setback_front: float = 5.0
    setback_rear: float = 3.0
    setback_left: float = 3.0
    setback_right: float = 3.0
    duration_seconds: int = 30
    is_watermarked: bool = True
    listing_data: Optional[dict] = None


@app.post("/render/villa")
async def render_villa(req: VillaRequest):
    """Villa Hayali: imar zarfı analiz videosu."""
    from src.villa.villa_pipeline import generate_villa_video
    work_dir = Path(TMP_BASE) / req.job_id
    work_dir.mkdir(parents=True, exist_ok=True)

    mp4_path = str(work_dir / "villa.mp4")
    try:
        generate_villa_video(
            parcel_area_m2=req.parcel_area_m2,
            taks=req.taks,
            kaks=req.kaks,
            output_mp4=mp4_path,
            listing_data=req.listing_data,
            setback_front=req.setback_front,
            setback_rear=req.setback_rear,
            setback_left=req.setback_left,
            setback_right=req.setback_right,
            duration_seconds=req.duration_seconds,
        )
        key = f"videos/{req.listing_id}/{req.job_id}_villa.mp4"
        _upload_to_minio(mp4_path, BUCKET_VIDEOS, key)
        return {"job_id": req.job_id, "output_key": key, "status": "done"}
    except Exception as e:
        logger.error(f"Villa render hatası: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    return {"status": "ok", "worker": "render"}


@app.post("/render", response_model=RenderResponse)
async def render_video(req: RenderRequest):
    logger.info(f"Render başlıyor: job={req.job_id} interior={req.interior_source}")

    work_dir = Path(TMP_BASE) / req.job_id
    work_dir.mkdir(parents=True, exist_ok=True)

    try:
        # 1. GML parse (gerekirse)
        inventory = req.room_inventory
        if req.interior_source == "gml_3d" and req.gml_file_key and not inventory:
            gml_path = work_dir / "input.gml"
            _download_from_minio(req.gml_file_key, BUCKET_GML, str(gml_path))
            inventory = parse_gml_file(str(gml_path))

        # 2. Senaryo üret
        scenario_text = await _generate_scenario(req, inventory)

        # 3. TTS
        speech_path = str(work_dir / "speech.mp3")
        synthesize_speech(scenario_text, speech_path, os.environ.get("TTS_PROVIDER", "google"))

        # 4. Ses mix
        audio_path = str(work_dir / "audio.mp3")
        mix_audio(speech_path, _find_music(), audio_path, req.duration_seconds)

        # 5. Render (Remotion)
        output_path = str(work_dir / "output.mp4")
        await _remotion_render(req, inventory, audio_path, output_path, work_dir)

        # 6. Watermark
        if req.is_watermarked:
            wm_path = str(work_dir / "watermarked.mp4")
            _add_watermark(output_path, wm_path)
            final_path = wm_path
        else:
            final_path = output_path

        # 7. MinIO'ya yükle
        key = f"videos/{req.listing_id}/{req.job_id}.mp4"
        _upload_to_minio(final_path, BUCKET_VIDEOS, key)

        logger.info(f"Render tamamlandı: {key}")
        return RenderResponse(job_id=req.job_id, output_key=key, scenario_text=scenario_text)

    except Exception as e:
        logger.error(f"Render hatası: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _generate_scenario(req: RenderRequest, inventory: Optional[dict]) -> str:
    """Claude API veya fallback ile senaryo üretir."""
    import anthropic
    api_key = os.environ.get("CLAUDE_API_KEY", "")
    if not api_key:
        return _fallback_scenario(req.listing_data or {})

    narration = build_narration_data(inventory, req.listing_data) if inventory else {"listing_data": req.listing_data}

    rooms_text = ""
    if inventory and req.interior_source == "gml_3d":
        rooms = inventory.get("rooms", [])[:8]
        rooms_text = "\nGML oda verileri (CityGML LoD4 — resmî):\n"
        for r in rooms:
            rooms_text += f"  - {r['name']}: {r['area_m2']:.1f} m² (Kat {r['floor']})\n"
        sections = inventory.get("independent_sections", [])
        if sections:
            rooms_text += f"  Toplam {len(sections)} bağımsız bölüm\n"

    data = req.listing_data or {}
    prompt = f"""Bir emlak videosu için {req.duration_seconds} saniyelik Türkçe seslendirme metni yaz.

Taşınmaz bilgileri:
- Başlık: {data.get('title', '')}
- Tip: {data.get('listing_type', 'Konut')}
- Konum: {data.get('address_text', '')}, {data.get('city', '')}
- Alan: {data.get('gross_area', '?')} m² brüt, {data.get('net_area', '?')} m² net
- Oda: {data.get('room_count', '?')} oda, {data.get('floor', '?')}. kat / {data.get('total_floors', '?')} kat
- Fiyat: {data.get('price', '?')} {data.get('currency', 'TRY')}
{rooms_text}
İç mekân kaynağı: {req.interior_source}

Kurallar:
1. Sadece verilen gerçek bilgileri kullan, asla uydurma yapma
2. GML verisi varsa oda adlarını ve alanlarını doğal anlatımına ekle
3. Profesyonel, samimi, akıcı Türkçe — reklam dili değil, bilgilendirici
4. ~{req.duration_seconds * 3} kelime
5. Sadece seslendirme metnini yaz"""

    try:
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model=os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6"),
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text
    except Exception as e:
        logger.error(f"Claude API hatası: {e}")
        return _fallback_scenario(data)


def _fallback_scenario(data: dict) -> str:
    parts = []
    if data.get("title"):
        parts.append(data["title"])
    if data.get("city"):
        parts.append(f"{data['city']} konumunda")
    if data.get("gross_area"):
        parts.append(f"{data['gross_area']} metrekare")
    if data.get("room_count"):
        parts.append(f"{data['room_count']} odalı")
    parts.append("taşınmaz satılıktır. Detay için iletişime geçin.")
    return " ".join(parts)


async def _remotion_render(
    req: RenderRequest,
    inventory: Optional[dict],
    audio_path: str,
    output_path: str,
    work_dir: Path,
) -> None:
    """Remotion CLI ile video render et."""
    composition = {
        "gml_3d": "InteriorGML",
        "photos": "InteriorPhoto",
        "listing_data": "InteriorData",
    }.get(req.interior_source, "InteriorData")

    props = {
        "listingData": json.dumps(req.listing_data or {}),
        "audioPath": audio_path,
        "isWatermarked": req.is_watermarked,
    }

    if req.interior_source == "gml_3d" and inventory:
        # glTF üret
        gltf_path = str(work_dir / "model.glb")
        try:
            export_gltf(inventory, gltf_path)
        except Exception as e:
            logger.warning(f"glTF üretim hatası, fallback kullanılıyor: {e}")
        props["inventoryJson"] = json.dumps(inventory)
        props["gltfPath"] = gltf_path

    props_path = work_dir / "props.json"
    props_path.write_text(json.dumps(props))

    w, h = ("3840", "2160") if req.resolution == "4k" else ("1920", "1080")
    if req.orientation == "9:16":
        w, h = h, w

    cmd = [
        "npx", "remotion", "render",
        "src/remotion/index.tsx",
        composition,
        output_path,
        "--props", str(props_path),
        "--width", w,
        "--height", h,
        "--fps", "25",
        "--log", "warn",
    ]

    logger.info(f"Remotion render: {composition} {w}x{h}")
    result = subprocess.run(cmd, cwd=str(Path(__file__).parent.parent), capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        logger.warning(f"Remotion başarısız (kod {result.returncode}), PIL pipeline_phase0 fallback'e geçiliyor")
        # Fallback 1: PIL tabanlı anahtarsız yol (pipeline_phase0)
        if inventory:
            _pipeline_phase0_fallback(req, inventory, audio_path, output_path, work_dir)
        else:
            # Fallback 2: ffmpeg drawtext
            _generate_fallback_video(req, audio_path, output_path, w, h)


def _pipeline_phase0_fallback(req: RenderRequest, inventory: dict, audio_path: str,
                               output_path: str, work_dir: Path) -> None:
    """pipeline_phase0 ile PIL tabanlı video üret (Remotion olmadan)."""
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
        from render.src.video.frame_generator import generate_frames
        from render.src.pipeline_phase0 import _encode_mp4

        frames_dir = str(work_dir / "frames_fallback")
        frame_paths = generate_frames(inventory, frames_dir, req.duration_seconds, fps=25)
        _encode_mp4(frame_paths, audio_path if Path(audio_path).exists() else None,
                    output_path, 25, lambda s, p: None)
        logger.info(f"PIL fallback video: {output_path}")
    except Exception as e:
        logger.error(f"PIL fallback başarısız: {e}")
        _generate_fallback_video(req, audio_path, output_path, "1920", "1080")


def _generate_fallback_video(req: RenderRequest, audio_path: str, output_path: str, w: str, h: str) -> None:
    data = req.listing_data or {}
    title = data.get("title", "Satılık Taşınmaz")[:60]
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", f"-i", f"color=c=0x1a1a2e:s={w}x{h}:r=25",
        "-i", audio_path,
        "-vf", f"drawtext=text='{title}':fontcolor=white:fontsize=48:x=(w-text_w)/2:y=(h-text_h)/2",
        "-t", str(req.duration_seconds),
        "-c:v", "libx264", "-c:a", "aac",
        output_path,
    ]
    subprocess.run(cmd, capture_output=True, timeout=120)


def _add_watermark(input_path: str, output_path: str) -> None:
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-vf", "drawtext=text='ÖNIZLEME':fontcolor=white@0.7:fontsize=28:x=20:y=20:borderw=2:bordercolor=black@0.5",
        "-c:a", "copy",
        output_path,
    ]
    subprocess.run(cmd, capture_output=True, timeout=300)


def _find_music() -> Optional[str]:
    music_dir = Path("/app/assets/music")
    if music_dir.exists():
        mp3s = list(music_dir.glob("*.mp3"))
        if mp3s:
            return str(mp3s[0])
    return None


def _download_from_minio(key: str, bucket: str, dest: str) -> None:
    s3 = boto3.client(
        "s3",
        endpoint_url=f"http://{MINIO_ENDPOINT}",
        aws_access_key_id=MINIO_ACCESS,
        aws_secret_access_key=MINIO_SECRET,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )
    with open(dest, "wb") as f:
        s3.download_fileobj(bucket, key, f)


def _upload_to_minio(src: str, bucket: str, key: str) -> None:
    s3 = boto3.client(
        "s3",
        endpoint_url=f"http://{MINIO_ENDPOINT}",
        aws_access_key_id=MINIO_ACCESS,
        aws_secret_access_key=MINIO_SECRET,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )
    with open(src, "rb") as f:
        s3.put_object(Bucket=bucket, Key=key, Body=f, ContentType="video/mp4")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
