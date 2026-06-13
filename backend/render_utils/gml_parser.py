"""
Backend Celery worker'dan GML parse için köprü.
render/ klasöründeki asıl parse.py'ye delege eder.
"""
import sys
from pathlib import Path

# render/src'yi path'e ekle (docker içinde /app/render mount'lu)
_render_src = Path("/app/../render/src")
if _render_src.exists():
    sys.path.insert(0, str(_render_src.parent))
else:
    # Geliştirme ortamı
    _dev = Path(__file__).parent.parent.parent / "render"
    if _dev.exists():
        sys.path.insert(0, str(_dev))

try:
    from src.gml.parse import parse_gml_file as _parse
    def parse_gml_file(gml_path: str) -> dict:
        return _parse(gml_path)
except ImportError:
    def parse_gml_file(gml_path: str) -> dict:
        # Fallback: temel lxml parse (bağımlılıklar render container'da)
        from lxml import etree
        tree = etree.parse(gml_path)
        return {
            "rooms": [],
            "independent_sections": [],
            "crs": "EPSG:5254",
            "source_file": gml_path,
            "room_count": 0,
            "section_count": 0,
            "_error": "render bağımlılıkları yüklü değil; render worker'a delege edin",
        }
