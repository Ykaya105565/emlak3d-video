"""
TTS (Text-to-Speech) modülü — çok sağlayıcılı, anahtarsız yol öncelikli.

Sağlayıcı zinciri:
  1. ElevenLabs (en iyi kalite, ELEVENLABS_API_KEY gerekli)
  2. gTTS (Google TTS, ücretsiz, anahtar gerekmez, internet gerekli)
  3. pyttsx3 (yerel TTS, tamamen çevrimdışı, kalite düşük)
  4. Sessizlik (1s sessiz audio, son çare)
"""

from __future__ import annotations
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Optional

from loguru import logger

TURKISH_SCENARIO_TEMPLATE = """\
{title} için sanal tur başlıyor. \
Bu yapı, resmî CityGML LoD4 verisiyle modellenmiştir. \
Bina toplam {room_count} odadan oluşmakta olup, kullanılabilir alan yaklaşık {total_area:.0f} metrekaredir. \
{section_info}
Tur sırasıyla {tour_rooms} odalarını kapsayacaktır. \
Görseller ve iç mekân düzenlemeleri temsilîdir; gerçek yapıyla bazı farklılıklar görülebilir. \
Mülk hakkında daha fazla bilgi için satış temsilcinizle iletişime geçiniz.
"""

TOUR_PRIORITY = {
    "Hol": 0, "Koridor": 1, "Salon": 2, "Mutfak": 3, "Kiler": 4,
    "Oda": 5, "Yatak Odası": 5, "Çocuk Odası": 5,
    "Balkon": 6, "Teras": 6, "Banyo": 7, "WC": 8,
    "Merdiven": 9, "Garaj": 10, "Depo": 11, "Isı Merkezi": 12,
}


def build_scenario(inventory: dict, listing_info: Optional[dict] = None) -> str:
    """GML envanterinden Türkçe tur anlatı metni üret."""
    rooms = inventory.get("rooms", [])
    sections = inventory.get("independent_sections", [])
    total_area = sum(r.get("area_m2", 0) for r in rooms)
    source = inventory.get("source_file", "Bina")
    title = (listing_info or {}).get("title", source.replace(".gml", ""))

    if sections:
        section_info = f"Yapı {len(sections)} bağımsız bölüm içermektedir."
    else:
        section_info = ""

    sorted_rooms = sorted(rooms, key=lambda r: (
        TOUR_PRIORITY.get(r.get("usage", ""), TOUR_PRIORITY.get(r.get("name", ""), 5)),
        r.get("floor", 0)
    ))
    tour_rooms_list = [r.get("name", "oda") for r in sorted_rooms[:5]]
    tour_rooms = ", ".join(tour_rooms_list)
    if len(sorted_rooms) > 5:
        tour_rooms += f" ve diğer {len(sorted_rooms) - 5} mekan"

    return TURKISH_SCENARIO_TEMPLATE.format(
        title=title,
        room_count=len(rooms),
        total_area=total_area,
        section_info=section_info,
        tour_rooms=tour_rooms,
    ).strip()


def synthesize_speech(
    text: str,
    output_path: str,
    provider: str = "auto",
    language: str = "tr",
) -> str:
    """
    Metni sese çevir, output_path'e yaz.
    provider: "auto" | "gtts" | "pyttsx3" | "elevenlabs" | "silent"
    Döndürür: yazılan dosya yolu.
    """
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    providers = _resolve_provider_chain(provider)
    for prov in providers:
        try:
            fn = _PROVIDERS[prov]
            result = fn(text, str(out), language)
            if result and Path(result).exists() and Path(result).stat().st_size > 100:
                logger.info(f"TTS başarılı ({prov}): {result}")
                return result
        except Exception as e:
            logger.warning(f"TTS provider '{prov}' başarısız: {e}")

    logger.error("Tüm TTS sağlayıcıları başarısız oldu — sessiz audio oluşturuluyor")
    return _silent_audio(str(out), duration=5)


def _resolve_provider_chain(provider: str) -> list[str]:
    if provider != "auto":
        return [provider, "silent"]
    chain = []
    if os.environ.get("ELEVENLABS_API_KEY"):
        chain.append("elevenlabs")
    chain.extend(["gtts", "pyttsx3", "silent"])
    return chain


# ── Sağlayıcı fonksiyonları ─────────────────────────────────────────────────

def _tts_gtts(text: str, output_path: str, language: str = "tr") -> str:
    """gTTS — ücretsiz, internet gerekli, kalite orta-iyi."""
    from gtts import gTTS  # pip install gtts
    mp3_path = output_path.rsplit(".", 1)[0] + ".mp3"
    tts = gTTS(text=text, lang=language, slow=False)
    tts.save(mp3_path)
    if output_path.endswith(".wav"):
        _mp3_to_wav(mp3_path, output_path)
        return output_path
    if mp3_path != output_path:
        import shutil
        shutil.move(mp3_path, output_path)
    return output_path


def _tts_pyttsx3(text: str, output_path: str, language: str = "tr") -> str:
    """pyttsx3 — tamamen yerel, kalite düşük."""
    import pyttsx3  # pip install pyttsx3
    engine = pyttsx3.init()
    voices = engine.getProperty("voices")
    for v in voices:
        if v.languages and "tr" in (v.languages[0] or "").lower():
            engine.setProperty("voice", v.id)
            break
    engine.setProperty("rate", 160)
    wav_path = output_path if output_path.endswith(".wav") else output_path + ".wav"
    engine.save_to_file(text, wav_path)
    engine.runAndWait()
    if wav_path != output_path:
        import shutil
        shutil.move(wav_path, output_path)
    return output_path


def _tts_elevenlabs(text: str, output_path: str, language: str = "tr") -> str:
    """ElevenLabs — en yüksek kalite, API anahtarı gerekli."""
    import requests
    api_key = os.environ["ELEVENLABS_API_KEY"]
    voice_id = os.environ.get("ELEVENLABS_VOICE_ID", "pNInz6obpgDQGcFmaJgB")
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {"xi-api-key": api_key, "Content-Type": "application/json"}
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
    }
    resp = requests.post(url, json=payload, headers=headers, timeout=60)
    resp.raise_for_status()
    mp3_path = output_path.rsplit(".", 1)[0] + ".mp3"
    with open(mp3_path, "wb") as f:
        f.write(resp.content)
    if output_path.endswith(".wav"):
        _mp3_to_wav(mp3_path, output_path)
        return output_path
    import shutil
    shutil.move(mp3_path, output_path)
    return output_path


def _silent_audio(output_path: str, duration: int = 5) -> str:
    """Belirtilen sürede sessiz audio oluştur (son çare)."""
    try:
        cmd = [
            "ffmpeg", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
            "-t", str(duration), "-q:a", "9", "-acodec", "libmp3lame",
            "-y", output_path
        ]
        subprocess.run(cmd, capture_output=True, check=True)
        return output_path
    except Exception:
        pass

    try:
        import wave
        wav_path = (output_path.rsplit(".", 1)[0] + ".wav"
                    if output_path.endswith(".mp3") else output_path)
        samples = b"\x00\x00" * 44100 * duration
        with wave.open(wav_path, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(44100)
            wf.writeframes(samples)
        return wav_path
    except Exception as e:
        logger.error(f"Sessiz audio oluşturulamadı: {e}")
        return output_path


def _mp3_to_wav(mp3_path: str, wav_path: str) -> None:
    """MP3 → WAV (ffmpeg veya pydub)."""
    try:
        subprocess.run(
            ["ffmpeg", "-i", mp3_path, "-acodec", "pcm_s16le",
             "-ar", "44100", "-y", wav_path],
            capture_output=True, check=True
        )
        return
    except Exception:
        pass
    try:
        from pydub import AudioSegment
        AudioSegment.from_mp3(mp3_path).export(wav_path, format="wav")
    except Exception as e:
        logger.warning(f"MP3→WAV çevrimi başarısız: {e} — MP3 olarak devam ediliyor")


_PROVIDERS = {
    "gtts": _tts_gtts,
    "pyttsx3": _tts_pyttsx3,
    "elevenlabs": _tts_elevenlabs,
    "silent": lambda t, p, l: _silent_audio(p),
}


# ── Müzik karıştırma ────────────────────────────────────────────────────────

def mix_audio(
    speech_path: str,
    music_path: Optional[str],
    output_path: str,
    duration: int,
    music_volume: float = 0.15,
) -> str:
    """
    Anlatı + arka plan müziği → karışık MP3.
    Müzik yoksa yalnızca anlatıyı kopyala.
    """
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    if not music_path or not Path(music_path).exists():
        logger.info("Arka plan müziği yok — yalnızca anlatı kullanılıyor")
        if not Path(speech_path).exists():
            logger.warning(f"Anlatı dosyası bulunamadı: {speech_path} — boş audio")
            return speech_path  # pipeline kendi yolunu kullanır
        import shutil
        shutil.copy2(speech_path, output_path)
        return output_path

    try:
        cmd = [
            "ffmpeg",
            "-i", speech_path,
            "-i", music_path,
            "-filter_complex",
            f"[1:a]volume={music_volume},aloop=loop=-1:size=2e+09[music];"
            f"[0:a][music]amix=inputs=2:duration=first:dropout_transition=2[out]",
            "-map", "[out]",
            "-t", str(duration),
            "-c:a", "libmp3lame", "-q:a", "3",
            "-y", str(out),
        ]
        subprocess.run(cmd, capture_output=True, check=True)
        logger.info(f"Ses karıştırıldı: {out}")
        return str(out)
    except Exception as e:
        logger.warning(f"Ses karıştırma başarısız ({e}) — yalnızca anlatı kullanılıyor")
        import shutil
        shutil.copy2(speech_path, output_path)
        return output_path
