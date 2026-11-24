from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class Measurement(BaseModel):
    value: float
    unit: str | None = None
    flag: str | None = None

class AnalyzerPayload(BaseModel):
    sample_id: str = Field(min_length=1, max_length=120)
    patient_reference: str | None = None
    patient_name: str | None = Field(default=None, max_length=200)
    patient_age: str | None = Field(default=None, max_length=80)
    patient_address: str | None = Field(default=None, max_length=1000)
    gender: str | None = Field(default=None, max_length=30)
    patient_contact: str | None = Field(default=None, max_length=80)
    requesting_officer: str | None = Field(default=None, max_length=200)
    requested_test: str | None = Field(default=None, max_length=2000)
    collected_at: datetime | None = None
    analyzer: str = Field(min_length=1, max_length=120)
    observed_at: datetime | None = None
    values: dict[str, Measurement]

class ManualSample(BaseModel):
    sample_id: str = Field(min_length=1, max_length=120)
    patient_reference: str | None = None
    patient_name: str | None = Field(default=None, max_length=200)
    patient_age: str | None = Field(default=None, max_length=80)
    patient_address: str | None = Field(default=None, max_length=1000)
    gender: str | None = Field(default=None, max_length=30)
    patient_contact: str | None = Field(default=None, max_length=80)
    requesting_officer: str | None = Field(default=None, max_length=200)
    requested_test: str | None = Field(default=None, max_length=2000)
    collected_at: datetime | None = None

class ReviewIn(BaseModel):
    reviewer: str | None = None
    comments: str | None = None
    analyte_comments: dict[str, str] = Field(default_factory=dict)
    reviewed_values: dict[str, Measurement]

class AnalyteIn(BaseModel):
    code: str = Field(min_length=1, max_length=40)
    display_name: str = Field(min_length=1, max_length=120)
    unit: str | None = None
    precision: int = Field(default=2, ge=0, le=6)
    enabled: bool = True

class ResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    sample_id: str
    patient_fields_from_analyzer: list[str] = Field(default_factory=list)
    patient_reference: str | None
    patient_name: str | None = None
    patient_age: str | None = None
    patient_address: str | None = None
    gender: str | None = None
    patient_contact: str | None = None
    requesting_officer: str | None = None
    requested_test: str | None = None
    collected_at: datetime | None = None
    analyzer: str
    device_id: str
    observed_at: datetime | None
    received_at: datetime
    status: str
    values: dict
