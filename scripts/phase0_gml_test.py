#!/usr/bin/env python3
"""
Faz 0 GML Test Scripti
======================
Gerçek .gml dosyasından oda envanteri çıkarır ve sonuçları raporlar.

Kullanım:
  python scripts/phase0_gml_test.py data/sample/M-94777652-A.gml
  python scripts/phase0_gml_test.py data/sample/M-94777652-A.gml --export-gltf output/model.glb

Gereksinimler (pip install):
  lxml pyproj shapely trimesh loguru
"""
import sys
import json
import argparse
from pathlib import Path

# render/src'yi Python path'e ekle
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "render"))


def main():
    parser = argparse.ArgumentParser(description="Faz 0 GML Test")
    parser.add_argument("gml", help=".gml dosya yolu")
    parser.add_argument("--export-gltf", help="glTF çıktı yolu (opsiyonel)")
    parser.add_argument("--json", action="store_true", help="Ham JSON çıktısı")
    args = parser.parse_args()

    gml_path = Path(args.gml)
    if not gml_path.exists():
        print(f"HATA: Dosya bulunamadı: {gml_path}")
        print("\nNot: Örnek .gml dosyanızı data/sample/ klasörüne koyun:")
        print(f"  mkdir -p {ROOT / 'data' / 'sample'}")
        print(f"  cp <M-94777652-A.gml> {ROOT / 'data' / 'sample'}/")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"FAZ 0 — GML PARSE TESTİ")
    print(f"{'='*60}")
    print(f"Dosya: {gml_path.name} ({gml_path.stat().st_size / 1024:.1f} KB)")
    print()

    # GML Parse
    print("1. GML PARSE...")
    from src.gml.parse import parse_gml_file
    inventory = parse_gml_file(str(gml_path))

    if args.json:
        print(json.dumps(inventory, ensure_ascii=False, indent=2))
        return

    # Rapor
    print(f"\n{'─'*60}")
    print(f"SONUÇLAR")
    print(f"{'─'*60}")
    print(f"Koordinat sistemi  : {inventory['crs']}")
    print(f"Toplam oda sayısı  : {inventory['room_count']}")
    print(f"Bağımsız bölüm     : {inventory['section_count']}")

    print(f"\nODA ENVANTERİ:")
    print(f"{'Ad':<25} {'Kullanım':<20} {'Alan (m²)':<12} {'Kat':<5}")
    print(f"{'─'*62}")
    for room in inventory["rooms"]:
        print(f"{room['name']:<25} {(room.get('usage') or ''):<20} {room['area_m2']:<12.2f} {room['floor']:<5}")

    if inventory["independent_sections"]:
        print(f"\nBAĞIMSIZ BÖLÜMLER:")
        for sec in inventory["independent_sections"]:
            print(f"  {sec['id']}: {sec['room_count']} oda, {sec['total_area_m2']:.1f} m²")

    # Özet istatistikler
    print(f"\n2. ÖZET İSTATİSTİKLER...")
    from src.gml.measure import summarize_inventory, build_narration_data
    summary = summarize_inventory(inventory)

    print(f"Toplam alan        : {summary['total_area_m2']:.2f} m²")
    print(f"Ortalama oda alanı : {summary['avg_room_area_m2']:.2f} m²")
    print(f"Kat sayısı         : {summary['floor_count']}")

    print(f"\nKAT PLANI:")
    for fl in summary["floors"]:
        print(f"  Kat {fl['floor']}: {fl['room_count']} oda, {fl['total_area_m2']:.1f} m² — {', '.join(fl['room_names'][:5])}")

    # Tur sırası
    narration = build_narration_data(inventory)
    print(f"\nTUR SIRASI ({len(narration['tour_order'])} adım):")
    for i, r in enumerate(narration["tour_order"][:10]):
        print(f"  {i+1}. {r['name']} ({r['area_m2']:.1f} m²)")
    if len(narration["tour_order"]) > 10:
        print(f"  ... ve {len(narration['tour_order']) - 10} oda daha")

    # glTF export (opsiyonel)
    if args.export_gltf:
        print(f"\n3. GLTF EXPORT...")
        try:
            from src.gml.gltf_export import export_gltf
            out = export_gltf(inventory, args.export_gltf)
            size = Path(out).stat().st_size / 1024
            print(f"glTF dosyası: {out} ({size:.1f} KB)")
        except ImportError as e:
            print(f"UYARI: glTF export için trimesh kurulu değil: {e}")
            print("  pip install trimesh pygltflib")
        except Exception as e:
            print(f"HATA: glTF export başarısız: {e}")

    # JSON çıktısını kaydet
    output_json = ROOT / "data" / "sample" / f"{gml_path.stem}_inventory.json"
    output_json.parent.mkdir(parents=True, exist_ok=True)
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(inventory, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"BAŞARILI!")
    print(f"Oda envanteri kaydedildi: {output_json}")
    print(f"{'='*60}\n")
    print("Sıradaki adım:")
    print("  1. three.js turu için: node render/src/threejs/interior_walk.js \\")
    print(f"       --inventory {output_json} --fps 25 --duration 30 --output /tmp/frames")
    print("  2. Remotion render için: docker-compose up render-worker")
    print()


if __name__ == "__main__":
    main()
