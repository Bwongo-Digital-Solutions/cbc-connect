from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any

@dataclass(frozen=True)
class NormalizedMeasurement:
    value: float
    unit: str | None = None
    flag: str | None = None

@dataclass(frozen=True)
class NormalizedCBCMessage:
    sample_id: str
    analyzer: str
    observed_at: datetime | None
    values: dict[str, NormalizedMeasurement]
    raw_message: str

class AnalyzerAdapter(ABC):
    """Implement only after vendor protocol and real device samples are verified."""
    @abstractmethod
    def parse(self, payload: bytes) -> NormalizedCBCMessage:
        raise NotImplementedError

class UnsupportedDeviceFormat(ValueError):
    pass
