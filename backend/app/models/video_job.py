import uuid
import enum
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, DateTime, Integer, ForeignKey, Enum, Text, Float, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class VideoJobStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class VideoResolution(str, enum.Enum):
    HD_1080P = "1080p"
    UHD_4K = "4k"


class VideoOrientation(str, enum.Enum):
    LANDSCAPE = "16:9"
    PORTRAIT = "9:16"


class VideoJob(Base):
    __tablename__ = "video_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    listing_id: Mapped[str] = mapped_column(String(36), ForeignKey("listings.id"), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False)

    # Video parametreleri
    duration_seconds: Mapped[int] = mapped_column(Integer, default=30)
    resolution: Mapped[VideoResolution] = mapped_column(Enum(VideoResolution), default=VideoResolution.HD_1080P)
    orientation: Mapped[VideoOrientation] = mapped_column(Enum(VideoOrientation), default=VideoOrientation.LANDSCAPE)

    # Kredi
    credit_cost: Mapped[float] = mapped_column(Float, nullable=False)
    is_watermarked: Mapped[bool] = mapped_column(Boolean, default=True)  # ücretsiz deneme → watermark'lı

    # Durum
    status: Mapped[VideoJobStatus] = mapped_column(Enum(VideoJobStatus), default=VideoJobStatus.PENDING)
    celery_task_id: Mapped[Optional[str]] = mapped_column(String(255))
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    progress_pct: Mapped[int] = mapped_column(Integer, default=0)

    # Çıktı
    output_file_key: Mapped[Optional[str]] = mapped_column(String(500))  # MinIO key
    scenario_text: Mapped[Optional[str]] = mapped_column(Text)
    render_meta: Mapped[Optional[dict]] = mapped_column(JSON)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    listing: Mapped["Listing"] = relationship("Listing", back_populates="video_jobs")
