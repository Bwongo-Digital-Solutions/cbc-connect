from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class Measurement(BaseModel):
    value: float
    unit: str | None = None
    flag: str | None = None

class AnalyzerPayload(BaseModel):
    sample_id: str = Field(min_length=1, max_length=120)
    patient_reference: str | None = None
    analyzer: str = Field(min_length=1, max_length=120)
    observed_at: datetime | None = None
    values: dict[str, Measurement]

class ResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    sample_id: str
    patient_reference: str | None
    analyzer: str
    device_id: str
    observed_at: datetime | None
    received_at: datetime
    status: str
    values: dict
