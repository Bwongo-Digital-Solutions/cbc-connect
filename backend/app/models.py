from datetime import datetime, timezone
from sqlalchemy import DateTime, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base

class CBCResult(Base):
    __tablename__ = "cbc_results"
    __table_args__ = (UniqueConstraint("sample_id", "device_id", name="uq_sample_device"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sample_id: Mapped[str] = mapped_column(String(120), index=True)
    patient_reference: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    analyzer: Mapped[str] = mapped_column(String(120))
    device_id: Mapped[str] = mapped_column(String(120), index=True)
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    status: Mapped[str] = mapped_column(String(30), default="PENDING_REVIEW", index=True)
    values: Mapped[dict] = mapped_column(JSON)
