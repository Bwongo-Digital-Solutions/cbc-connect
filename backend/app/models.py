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
    patient_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    patient_age: Mapped[str | None] = mapped_column(String(80), nullable=True)
    patient_address: Mapped[str | None] = mapped_column(Text, nullable=True)
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


class ReferenceInterval(Base):
    __tablename__ = "reference_intervals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    analyte_code: Mapped[str] = mapped_column(String(40), index=True)
    population: Mapped[str] = mapped_column(String(160))
    age_min_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    age_max_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sex: Mapped[str] = mapped_column(String(20), default="ALL")
    lower_value: Mapped[float] = mapped_column()
    upper_value: Mapped[float] = mapped_column()
    unit: Mapped[str] = mapped_column(String(40))
    source: Mapped[str] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(20), default="DRAFT")
    verified_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ResultDocument(Base):
    __tablename__ = "result_documents"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    result_id: Mapped[int] = mapped_column(ForeignKey("cbc_results.id"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(120))
    storage_path: Mapped[str] = mapped_column(String(500))
    uploaded_by: Mapped[str] = mapped_column(String(120))
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    parent_document_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    document_kind: Mapped[str] = mapped_column(String(20), default="SOURCE")
    annotation_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class ClinicProfile(Base):
    __tablename__ = "clinic_profile"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    clinic_name: Mapped[str] = mapped_column(String(200), default="Clinic")
    address: Mapped[str] = mapped_column(Text, default="")
    phone: Mapped[str] = mapped_column(String(120), default="0775-872-454, 0751-319-201")
    email: Mapped[str] = mapped_column(String(160), default="")
    theme_color: Mapped[str] = mapped_column(String(7), default="#0879D9")
    header_text: Mapped[str] = mapped_column(Text, default="")
    footer_text: Mapped[str] = mapped_column(Text, default="Powered by ClinicHIS")
    logo_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    logo_display_mode: Mapped[str] = mapped_column(String(20), default="header")
    logo_opacity: Mapped[float] = mapped_column(Float, default=0.10)
    updated_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
