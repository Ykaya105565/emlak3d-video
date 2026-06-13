import anthropic
from typing import Optional
from app.core.config import settings
from loguru import logger


async def generate_scenario(
    listing_data: dict,
    room_inventory: Optional[dict],
    duration_seconds: int,
    interior_source: str,
) -> str:
    """
    Claude API ile veri-güdümlü seslendirme metni üretir.
    İç mekân yoksa uydurulmaz — sadece mevcut veri anlatılır.
    """
    client = anthropic.Anthropic(api_key=settings.claude_api_key)

    rooms_text = ""
    if room_inventory and interior_source == "gml_3d":
        rooms = room_inventory.get("rooms", [])
        rooms_text = f"\nGerçek iç mekân verileri (CityGML LoD4):\n"
        for r in rooms:
            rooms_text += f"  - {r.get('name', 'Oda')}: {r.get('area_m2', '?'):.1f} m² (Kat {r.get('floor', '?')})\n"
        sections = room_inventory.get("independent_sections", [])
        if sections:
            rooms_text += f"  Bağımsız bölümler: {len(sections)} daire\n"

    prompt = f"""Bir emlak videosu için {duration_seconds} saniyelik Türkçe seslendirme metni yaz.

Taşınmaz bilgileri:
- Tip: {listing_data.get('listing_type', 'Konut')}
- Konum: {listing_data.get('address_text', '')}, {listing_data.get('city', '')}
- Alan: {listing_data.get('gross_area', '?')} m² brüt / {listing_data.get('net_area', '?')} m² net
- Oda: {listing_data.get('room_count', '?')} oda
- Kat: {listing_data.get('floor', '?')} / {listing_data.get('total_floors', '?')}
- Fiyat: {listing_data.get('price', '?')} {listing_data.get('currency', 'TRY')}
{rooms_text}
İç mekân kaynağı: {interior_source}

Kurallar:
1. Sadece yukarıdaki gerçek verileri kullan, uydurma yapma
2. GML verisi varsa oda adlarını ve alanlarını doğal bir şekilde anlatımına ekle
3. Profesyonel, sıcak, akıcı Türkçe
4. {duration_seconds} saniyede okunabilecek uzunlukta yaz (~{duration_seconds * 3} kelime)
5. Paragraf yerine konuşma diline uygun cümleler kullan

Sadece seslendirme metnini yaz, başka açıklama ekleme."""

    try:
        message = client.messages.create(
            model=settings.claude_model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text
    except Exception as e:
        logger.error(f"Claude API senaryo hatası: {e}")
        return _fallback_scenario(listing_data, duration_seconds)


def _fallback_scenario(listing_data: dict, duration: int) -> str:
    city = listing_data.get("city", "")
    area = listing_data.get("gross_area", "")
    listing_type = listing_data.get("listing_type", "taşınmaz")
    return (
        f"{city} {'konumunda' if city else ''} "
        f"{'%.0f m² ' % area if area else ''}"
        f"{listing_type} satılıktır. "
        f"Detaylı bilgi için lütfen iletişime geçin."
    )
