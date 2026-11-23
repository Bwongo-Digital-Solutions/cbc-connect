from datetime import datetime, timezone
from sqlalchemy import DateTime, Integer, JSON, String, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base

def utcnow():
    return datetime.now(timezone.utc)

class CBCResult(Base):
    __tablename__ = "cbc_results"
    __table_args__ = (UniqueConstraint("sample_id", "device_id", name="uq_sample_device"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sample_id: Mapped[str] = mapped_column(String(120), index=True)
    patient_reference: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    analyzer: Mapped[str] = mapped_column(String(120))
    device_id: Mapped[str] = mapped_column(String(120), index=True)
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    status: Mapped[str] = mapped_column(String(30), default="PENDING_REVIEW", index=True)
    values: Mapped[dict] = mapped_column(JSON)

class ResultReview(Base):
    __tablename__ = "result_reviews"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    result_id: Mapped[int] = mapped_column(ForeignKey("cbc_results.id"), unique=True, index=True)
    reviewer: Mapped[str] = mapped_column(String(120))
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_values: Mapped[dict] = mapped_column(JSON)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    result_id: Mapped[int | None] = mapped_column(ForeignKey("cbc_results.id"), nullable=True, index=True)
    actor: Mapped[str] = mapped_column(String(120))
    action: Mapped[str] = mapped_column(String(80))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class AnalyteConfig(Base):
    __tablename__ = "analyte_configs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(120))
    unit: Mapped[str | None] = mapped_column(String(40), nullable=True)
    precision: Mapped[int] = mapped_column(Integer, default=2)
    enabled: Mapped[bool] = mapped_column(default=True)

class ReportTemplate(Base):
    __tablename__ = "report_templates"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(120))
    storage_path: Mapped[str] = mapped_column(String(500))
    uploaded_by: Mapped[str] = mapped_column(String(120))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class UserAccount(Base):
    __tablename__ = "user_accounts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(30), default="TECHNICIAN")
    active: Mapped[bool] = mapped_column(default=True)
