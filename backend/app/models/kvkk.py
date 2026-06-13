import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class KVKKConsent(Base):
    """
    Her veri yükleme/işleme işlemi için kullanıcı onayı kaydı.
    Privacy-by-design: rıza olmadan veri işlenemez.
    """
    __tablename__ = "kvkk_consents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False)

    # Onay türü: "gml_upload" | "photo_upload" | "data_processing" | "video_generation"
    consent_type: Mapped[str] = mapped_column(String(100), nullable=False)
    # İlgili kaynağın kimliği (listing_id veya file key)
    resource_id: Mapped[Optional[str]] = mapped_column(String(255))

    # Onay detayları
    is_granted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    consent_text_version: Mapped[str] = mapped_column(String(50), default="1.0")
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    user_agent: Mapped[Optional[str]] = mapped_column(Text)

    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    withdrawn_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship("User", back_populates="consents")
