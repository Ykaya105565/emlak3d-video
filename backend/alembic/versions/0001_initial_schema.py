"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-06-13

Tüm tablo tanımları: tenant, user, listing, listing_media,
credit_wallet, credit_transaction, video_job, kvkk_consent.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Tenant ───────────────────────────────────────────────────────────────
    op.create_table(
        "tenants",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("plan", sa.String(50), nullable=False, server_default="free"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), onupdate=sa.text("now()")),
    )

    # ── User ─────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255)),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("is_superuser", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])

    # ── KVKK Consent ─────────────────────────────────────────────────────────
    op.create_table(
        "kvkk_consents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("purpose", sa.String(100), nullable=False),
        sa.Column("ip_address", sa.String(45)),
        sa.Column("user_agent", sa.String(500)),
        sa.Column("consented_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("withdrawn_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── Listing ───────────────────────────────────────────────────────────────
    op.create_table(
        "listings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),

        # Temel bilgiler
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("listing_type", sa.String(50), nullable=False),  # satilik/kiralik
        sa.Column("property_type", sa.String(50)),  # daire/villa/arsa/...

        # Konum
        sa.Column("city", sa.String(100)),
        sa.Column("district", sa.String(100)),
        sa.Column("address_text", sa.Text),
        sa.Column("lat", sa.Float, nullable=True),
        sa.Column("lng", sa.Float, nullable=True),
        sa.Column("geocoding_confirmed", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("geocoding_provider", sa.String(50)),

        # Fiziksel
        sa.Column("gross_area", sa.Float),
        sa.Column("net_area", sa.Float),
        sa.Column("room_count", sa.String(20)),
        sa.Column("floor", sa.Integer),
        sa.Column("total_floors", sa.Integer),
        sa.Column("building_age", sa.Integer),

        # Fiyat
        sa.Column("price", sa.Numeric(15, 2)),
        sa.Column("currency", sa.String(10), server_default="TRY"),

        # GML / İç mekân
        sa.Column("interior_source", sa.String(30), nullable=False, server_default="listing_data"),
        sa.Column("gml_file_key", sa.String(500)),
        sa.Column("gml_room_inventory", sa.JSON),
        sa.Column("gml_epsg", sa.Integer),
        sa.Column("gml_crs", sa.String(50)),

        # Villa Hayali (Arsa)
        sa.Column("taks", sa.Float),
        sa.Column("kaks", sa.Float),
        sa.Column("setback_front", sa.Float),
        sa.Column("setback_rear", sa.Float),
        sa.Column("setback_left", sa.Float),
        sa.Column("setback_right", sa.Float),
        sa.Column("parcel_area_m2", sa.Float),
        sa.Column("zoning_type", sa.String(100)),

        # Durum
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("is_published", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_listings_tenant_id", "listings", ["tenant_id"])
    op.create_index("ix_listings_user_id", "listings", ["user_id"])
    op.create_index("ix_listings_city", "listings", ["city"])

    # ── Listing Media ─────────────────────────────────────────────────────────
    op.create_table(
        "listing_media",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("listing_id", sa.String(36), sa.ForeignKey("listings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("media_type", sa.String(20), nullable=False, server_default="photo"),
        sa.Column("file_key", sa.String(500), nullable=False),
        sa.Column("original_filename", sa.String(500)),
        sa.Column("file_size_bytes", sa.BigInteger),
        sa.Column("mime_type", sa.String(100)),
        sa.Column("order_index", sa.Integer, server_default="0"),
        sa.Column("kvkk_consent_id", sa.String(36), sa.ForeignKey("kvkk_consents.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_listing_media_listing_id", "listing_media", ["listing_id"])

    # ── Credit Wallet ─────────────────────────────────────────────────────────
    op.create_table(
        "credit_wallets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("balance", sa.Numeric(10, 2), nullable=False, server_default="5.0"),
        sa.Column("lifetime_earned", sa.Numeric(10, 2), nullable=False, server_default="5.0"),
        sa.Column("lifetime_spent", sa.Numeric(10, 2), nullable=False, server_default="0.0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # ── Credit Transaction ────────────────────────────────────────────────────
    op.create_table(
        "credit_transactions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("wallet_id", sa.String(36), sa.ForeignKey("credit_wallets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("balance_after", sa.Numeric(10, 2), nullable=False),
        sa.Column("transaction_type", sa.String(30), nullable=False),  # purchase / spend / refund / bonus
        sa.Column("description", sa.String(500)),
        sa.Column("reference_id", sa.String(36)),  # VideoJob.id veya Stripe payment_intent_id
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_credit_transactions_wallet_id", "credit_transactions", ["wallet_id"])

    # ── Video Job ─────────────────────────────────────────────────────────────
    op.create_table(
        "video_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("listing_id", sa.String(36), sa.ForeignKey("listings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),

        # Parametreler
        sa.Column("duration_seconds", sa.Integer, nullable=False, server_default="30"),
        sa.Column("resolution", sa.String(20), nullable=False, server_default="1080p"),
        sa.Column("orientation", sa.String(10), nullable=False, server_default="16:9"),
        sa.Column("is_watermarked", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("credit_cost", sa.Numeric(10, 2), nullable=False, server_default="0"),

        # İçerik
        sa.Column("interior_source", sa.String(30), nullable=False, server_default="listing_data"),
        sa.Column("scenario_text", sa.Text),

        # Durum
        sa.Column("status", sa.String(30), nullable=False, server_default="queued"),
        sa.Column("progress_pct", sa.Integer, server_default="0"),
        sa.Column("error_message", sa.Text),

        # Çıktı
        sa.Column("output_file_key", sa.String(500)),

        # Zaman damgaları
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_video_jobs_listing_id", "video_jobs", ["listing_id"])
    op.create_index("ix_video_jobs_tenant_id", "video_jobs", ["tenant_id"])
    op.create_index("ix_video_jobs_status", "video_jobs", ["status"])

    # ── PostGIS uzantısı (eğer yoksa) ────────────────────────────────────────
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")


def downgrade() -> None:
    op.drop_table("video_jobs")
    op.drop_table("credit_transactions")
    op.drop_table("credit_wallets")
    op.drop_table("listing_media")
    op.drop_table("listings")
    op.drop_table("kvkk_consents")
    op.drop_table("users")
    op.drop_table("tenants")
