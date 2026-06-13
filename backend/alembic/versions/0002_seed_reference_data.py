"""seed reference data

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-13

Referans verileri:
  - part_usage_types: GML partUsageCode → Türkçe oda tipi + tur önceliği
  - credit_rate_config: süre × çözünürlük × iç mekân tipi → kredi tablosu (§9)
  - music_tracks: telifsiz müzik kaydı şablonları
  - zoning_defaults: imar türü → TAKS/KAKS/çekme mesafesi varsayılanları
"""

from alembic import op
import sqlalchemy as sa


revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── part_usage_types tablosu ─────────────────────────────────────────────
    op.create_table(
        "part_usage_types",
        sa.Column("code", sa.String(50), primary_key=True),
        sa.Column("name_tr", sa.String(100), nullable=False),
        sa.Column("tour_priority", sa.Integer, nullable=False, server_default="5"),
        sa.Column("is_living_space", sa.Boolean, nullable=False, server_default="true"),
    )

    op.bulk_insert(
        sa.table(
            "part_usage_types",
            sa.column("code"), sa.column("name_tr"),
            sa.column("tour_priority"), sa.column("is_living_space"),
        ),
        [
            # TAKBİS sayısal kodlar
            {"code": "1000", "name_tr": "Oda",          "tour_priority": 5,  "is_living_space": True},
            {"code": "1010", "name_tr": "Salon",         "tour_priority": 2,  "is_living_space": True},
            {"code": "1020", "name_tr": "Yatak Odası",   "tour_priority": 5,  "is_living_space": True},
            {"code": "1030", "name_tr": "Çocuk Odası",   "tour_priority": 5,  "is_living_space": True},
            {"code": "1040", "name_tr": "Banyo",          "tour_priority": 7,  "is_living_space": True},
            {"code": "1050", "name_tr": "WC",             "tour_priority": 8,  "is_living_space": True},
            {"code": "1060", "name_tr": "Hol",            "tour_priority": 0,  "is_living_space": True},
            {"code": "1070", "name_tr": "Koridor",        "tour_priority": 1,  "is_living_space": True},
            {"code": "1080", "name_tr": "Mutfak",         "tour_priority": 3,  "is_living_space": True},
            {"code": "1090", "name_tr": "Kiler",          "tour_priority": 4,  "is_living_space": True},
            {"code": "1100", "name_tr": "Balkon",         "tour_priority": 6,  "is_living_space": True},
            {"code": "1110", "name_tr": "Teras",          "tour_priority": 6,  "is_living_space": True},
            {"code": "1120", "name_tr": "Merdiven",       "tour_priority": 9,  "is_living_space": False},
            {"code": "1130", "name_tr": "Garaj",          "tour_priority": 10, "is_living_space": False},
            {"code": "1140", "name_tr": "Isı Merkezi",   "tour_priority": 12, "is_living_space": False},
            {"code": "1150", "name_tr": "Depo",           "tour_priority": 11, "is_living_space": False},
            {"code": "1160", "name_tr": "Ortak Alan",    "tour_priority": 13, "is_living_space": False},
            {"code": "1170", "name_tr": "Ofis",           "tour_priority": 5,  "is_living_space": True},
            {"code": "1180", "name_tr": "Teknik Hacim",  "tour_priority": 14, "is_living_space": False},
            {"code": "1190", "name_tr": "Sığınak",        "tour_priority": 15, "is_living_space": False},
            {"code": "2000", "name_tr": "Dükkan",         "tour_priority": 2,  "is_living_space": True},
            {"code": "2010", "name_tr": "Depo",           "tour_priority": 11, "is_living_space": False},
            {"code": "2020", "name_tr": "Ofis",           "tour_priority": 5,  "is_living_space": True},
            {"code": "3000", "name_tr": "Otopark",        "tour_priority": 10, "is_living_space": False},
            # İsim tabanlı kodlar (bazı GML üreticileri)
            {"code": "salon",       "name_tr": "Salon",       "tour_priority": 2,  "is_living_space": True},
            {"code": "yatakodasi",  "name_tr": "Yatak Odası", "tour_priority": 5,  "is_living_space": True},
            {"code": "cocukodasi",  "name_tr": "Çocuk Odası", "tour_priority": 5,  "is_living_space": True},
            {"code": "mutfak",      "name_tr": "Mutfak",       "tour_priority": 3,  "is_living_space": True},
            {"code": "banyo",       "name_tr": "Banyo",        "tour_priority": 7,  "is_living_space": True},
            {"code": "wc",          "name_tr": "WC",           "tour_priority": 8,  "is_living_space": True},
            {"code": "hol",         "name_tr": "Hol",          "tour_priority": 0,  "is_living_space": True},
            {"code": "koridor",     "name_tr": "Koridor",      "tour_priority": 1,  "is_living_space": True},
            {"code": "kiler",       "name_tr": "Kiler",        "tour_priority": 4,  "is_living_space": True},
            {"code": "balkon",      "name_tr": "Balkon",       "tour_priority": 6,  "is_living_space": True},
            {"code": "teras",       "name_tr": "Teras",        "tour_priority": 6,  "is_living_space": True},
            {"code": "merdiven",    "name_tr": "Merdiven",     "tour_priority": 9,  "is_living_space": False},
            {"code": "garaj",       "name_tr": "Garaj",        "tour_priority": 10, "is_living_space": False},
            {"code": "depo",        "name_tr": "Depo",         "tour_priority": 11, "is_living_space": False},
            {"code": "sigınak",     "name_tr": "Sığınak",      "tour_priority": 15, "is_living_space": False},
        ],
    )

    # ── credit_rate_config tablosu (§9) ──────────────────────────────────────
    op.create_table(
        "credit_rate_config",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("interior_source", sa.String(30), nullable=False),
        sa.Column("resolution", sa.String(20), nullable=False),
        sa.Column("duration_seconds", sa.Integer, nullable=False),
        sa.Column("credit_cost", sa.Numeric(5, 2), nullable=False),
        sa.Column("description", sa.String(200)),
    )

    # Kredi tablosu: iç mekân tipi × çözünürlük × süre → kredi
    # GML_3D: +2 kredi, PHOTOS: +1 kredi, LISTING_DATA: +0 kredi (temel)
    # 1080p: +0 kredi, 4K: +1 kredi
    # Her 15s: +1 kredi (min 1)
    rates = []
    for interior, base_interior in [("gml_3d", 2), ("photos", 1), ("listing_data", 0)]:
        for res, base_res in [("1080p", 0), ("4k", 1)]:
            for dur in [15, 30, 60, 90]:
                dur_credits = max(1, dur // 15)
                total = dur_credits + base_res + base_interior
                rates.append({
                    "interior_source": interior,
                    "resolution": res,
                    "duration_seconds": dur,
                    "credit_cost": float(total),
                    "description": f"{interior} / {res} / {dur}s = {total} kredi",
                })

    op.bulk_insert(
        sa.table(
            "credit_rate_config",
            sa.column("interior_source"), sa.column("resolution"),
            sa.column("duration_seconds"), sa.column("credit_cost"),
            sa.column("description"),
        ),
        rates,
    )

    # ── music_tracks tablosu ─────────────────────────────────────────────────
    op.create_table(
        "music_tracks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("artist", sa.String(200)),
        sa.Column("license", sa.String(100), nullable=False),
        sa.Column("license_url", sa.String(500)),
        sa.Column("file_key", sa.String(500)),    # MinIO key
        sa.Column("duration_seconds", sa.Integer),
        sa.Column("genre", sa.String(50)),
        sa.Column("bpm", sa.Integer),
        sa.Column("mood", sa.String(50)),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
    )

    op.bulk_insert(
        sa.table(
            "music_tracks",
            sa.column("id"), sa.column("title"), sa.column("artist"),
            sa.column("license"), sa.column("license_url"),
            sa.column("file_key"), sa.column("duration_seconds"),
            sa.column("genre"), sa.column("bpm"), sa.column("mood"),
            sa.column("is_active"),
        ),
        [
            {
                "id": "music-01",
                "title": "Cinematic Real Estate Background",
                "artist": "Pixabay Music",
                "license": "Pixabay License",
                "license_url": "https://pixabay.com/service/license-summary/",
                "file_key": None,
                "duration_seconds": 180,
                "genre": "Ambient",
                "bpm": 75,
                "mood": "professional",
                "is_active": True,
            },
            {
                "id": "music-02",
                "title": "Inspiring Corporate",
                "artist": "Pixabay Music",
                "license": "Pixabay License",
                "license_url": "https://pixabay.com/service/license-summary/",
                "file_key": None,
                "duration_seconds": 120,
                "genre": "Corporate",
                "bpm": 90,
                "mood": "uplifting",
                "is_active": True,
            },
            {
                "id": "music-03",
                "title": "Modern Architecture Ambient",
                "artist": "FreeMusicArchive",
                "license": "CC0 1.0 Universal",
                "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
                "file_key": None,
                "duration_seconds": 240,
                "genre": "Ambient",
                "bpm": 60,
                "mood": "calm",
                "is_active": False,  # İndirilmesi gerekiyor
            },
        ],
    )

    # ── zoning_defaults tablosu ───────────────────────────────────────────────
    op.create_table(
        "zoning_defaults",
        sa.Column("zoning_type", sa.String(100), primary_key=True),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("taks_default", sa.Float),
        sa.Column("kaks_default", sa.Float),
        sa.Column("setback_front_m", sa.Float),
        sa.Column("setback_rear_m", sa.Float),
        sa.Column("setback_side_m", sa.Float),
        sa.Column("max_height_m", sa.Float),
        sa.Column("notes", sa.Text),
    )

    op.bulk_insert(
        sa.table(
            "zoning_defaults",
            sa.column("zoning_type"), sa.column("display_name"),
            sa.column("taks_default"), sa.column("kaks_default"),
            sa.column("setback_front_m"), sa.column("setback_rear_m"),
            sa.column("setback_side_m"), sa.column("max_height_m"),
            sa.column("notes"),
        ),
        [
            {
                "zoning_type": "konut_az_yogunluklu",
                "display_name": "Konut — Az Yoğunluklu",
                "taks_default": 0.20, "kaks_default": 0.40,
                "setback_front_m": 5.0, "setback_rear_m": 3.0,
                "setback_side_m": 3.0, "max_height_m": 6.5,
                "notes": "2 kat max, müstakil konut bölgesi",
            },
            {
                "zoning_type": "konut_orta_yogunluklu",
                "display_name": "Konut — Orta Yoğunluklu",
                "taks_default": 0.30, "kaks_default": 1.20,
                "setback_front_m": 5.0, "setback_rear_m": 3.0,
                "setback_side_m": 3.0, "max_height_m": 12.5,
                "notes": "4 kat max",
            },
            {
                "zoning_type": "konut_yuksek_yogunluklu",
                "display_name": "Konut — Yüksek Yoğunluklu",
                "taks_default": 0.35, "kaks_default": 2.10,
                "setback_front_m": 5.0, "setback_rear_m": 3.0,
                "setback_side_m": 3.0, "max_height_m": 21.5,
                "notes": "7 kat max",
            },
            {
                "zoning_type": "villa_bolgesi",
                "display_name": "Villa Bölgesi",
                "taks_default": 0.15, "kaks_default": 0.30,
                "setback_front_m": 5.0, "setback_rear_m": 5.0,
                "setback_side_m": 3.0, "max_height_m": 6.5,
                "notes": "1-2 kat; havuz, garaj, peyzaj izni",
            },
            {
                "zoning_type": "ticaret_bolgesi",
                "display_name": "Ticaret Bölgesi",
                "taks_default": 0.40, "kaks_default": 2.40,
                "setback_front_m": 3.0, "setback_rear_m": 3.0,
                "setback_side_m": 0.0, "max_height_m": 30.0,
                "notes": "Ofis/alışveriş; cepheye sıfır çekme",
            },
            {
                "zoning_type": "karma_kullanim",
                "display_name": "Karma Kullanım (Konut+Ticaret)",
                "taks_default": 0.35, "kaks_default": 1.75,
                "setback_front_m": 5.0, "setback_rear_m": 3.0,
                "setback_side_m": 3.0, "max_height_m": 21.5,
                "notes": "Alt kat ticaret üst kat konut",
            },
            {
                "zoning_type": "sanayi",
                "display_name": "Sanayi Bölgesi",
                "taks_default": 0.50, "kaks_default": 1.50,
                "setback_front_m": 10.0, "setback_rear_m": 5.0,
                "setback_side_m": 5.0, "max_height_m": None,
                "notes": "Yükseklik kısıtı projeye göre değişir",
            },
            {
                "zoning_type": "tarım",
                "display_name": "Tarım Arazisi",
                "taks_default": 0.05, "kaks_default": 0.10,
                "setback_front_m": 10.0, "setback_rear_m": 10.0,
                "setback_side_m": 5.0, "max_height_m": 6.5,
                "notes": "Tarımsal yapı izni; konut yasak",
            },
        ],
    )


def downgrade() -> None:
    op.drop_table("zoning_defaults")
    op.drop_table("music_tracks")
    op.drop_table("credit_rate_config")
    op.drop_table("part_usage_types")
