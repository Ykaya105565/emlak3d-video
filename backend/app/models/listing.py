import uuid
import enum
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, DateTime, Boolean, ForeignKey, Float, Integer, Text, Enum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class InteriorSourceType(str, enum.Enum):
    GML_3D = "gml_3d"          # Öncelik 1: CityGML → gerçek 3D tur
    PHOTOS = "photos"           # Öncelik 2: Fotoğraflar
    LISTING_DATA = "listing_data"  # Öncelik 3: İlan verisi → grafik animasyon


class ListingType(str, enum.Enum):
    APARTMENT = "apartment"
    HOUSE = "house"
    LAND = "land"
    COMMERCIAL = "commercial"
    OFFICE = "office"


class Listing(Base):
    __tablename__ = "listings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False)
    owner_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)

    # Temel bilgiler
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    listing_type: Mapped[ListingType] = mapped_column(Enum(ListingType), nullable=False)
    price: Mapped[Optional[float]] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(10), default="TRY")

    # Konum
    address_text: Mapped[Optional[str]] = mapped_column(Text)
    city: Mapped[Optional[str]] = mapped_column(String(100))
    district: Mapped[Optional[str]] = mapped_column(String(100))
    lat: Mapped[Optional[float]] = mapped_column(Float)
    lng: Mapped[Optional[float]] = mapped_column(Float)
    geocoding_provider: Mapped[Optional[str]] = mapped_column(String(50))  # "google" | "nominatim"
    geocoding_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)  # Kullanıcı haritada onayladı mı?

    # Parsel (TKGM/MAKS)
    ada: Mapped[Optional[str]] = mapped_column(String(50))
    parsel: Mapped[Optional[str]] = mapped_column(String(50))
    takbis_no: Mapped[Optional[str]] = mapped_column(String(50))

    # Taşınmaz özellikleri
    gross_area: Mapped[Optional[float]] = mapped_column(Float)   # m²
    net_area: Mapped[Optional[float]] = mapped_column(Float)     # m²
    room_count: Mapped[Optional[int]] = mapped_column(Integer)
    floor: Mapped[Optional[int]] = mapped_column(Integer)
    total_floors: Mapped[Optional[int]] = mapped_column(Integer)
    building_age: Mapped[Optional[int]] = mapped_column(Integer)
    has_elevator: Mapped[Optional[bool]] = mapped_column(Boolean)
    has_parking: Mapped[Optional[bool]] = mapped_column(Boolean)
    has_balcony: Mapped[Optional[bool]] = mapped_column(Boolean)
    description: Mapped[Optional[str]] = mapped_column(Text)

    # Villa Hayali (arsa için)
    taks: Mapped[Optional[float]] = mapped_column(Float)
    kaks: Mapped[Optional[float]] = mapped_column(Float)
    setback_front: Mapped[Optional[float]] = mapped_column(Float)
    setback_side: Mapped[Optional[float]] = mapped_column(Float)
    max_floors: Mapped[Optional[int]] = mapped_column(Integer)

    # İç mekân kaynağı (otomatik seçilir)
    interior_source: Mapped[Optional[InteriorSourceType]] = mapped_column(Enum(InteriorSourceType))

    # GML meta
    gml_file_key: Mapped[Optional[str]] = mapped_column(String(500))  # MinIO key
    gml_room_inventory: Mapped[Optional[dict]] = mapped_column(JSON)  # parse sonucu

    # 3D kapsama
    has_3d_coverage: Mapped[Optional[bool]] = mapped_column(Boolean)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="listings")
    owner: Mapped["User"] = relationship("User", back_populates="listings")
    media: Mapped[list["ListingMedia"]] = relationship("ListingMedia", back_populates="listing", cascade="all, delete-orphan")
    video_jobs: Mapped[list["VideoJob"]] = relationship("VideoJob", back_populates="listing")


class ListingMedia(Base):
    __tablename__ = "listing_media"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    listing_id: Mapped[str] = mapped_column(String(36), ForeignKey("listings.id"), nullable=False)
    file_key: Mapped[str] = mapped_column(String(500), nullable=False)  # MinIO key
    media_type: Mapped[str] = mapped_column(String(50))  # "photo" | "gml"
    original_filename: Mapped[Optional[str]] = mapped_column(String(255))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    kvkk_consent_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("kvkk_consents.id"))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    listing: Mapped["Listing"] = relationship("Listing", back_populates="media")
