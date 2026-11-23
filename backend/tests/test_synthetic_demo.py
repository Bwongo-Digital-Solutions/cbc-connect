import json
from pathlib import Path
from app.schemas import AnalyzerPayload

def test_synthetic_demo_payload_matches_normalized_ingest_schema():
    fixture = Path(__file__).parents[1] / "demo" / "synthetic_cbc_export.json"
    raw = json.loads(fixture.read_text(encoding="utf-8"))
    notice = raw.pop("_demo_notice")
    assert notice.startswith("SYNTHETIC TRAINING DATA ONLY")
    payload = AnalyzerPayload.model_validate(raw)
    assert payload.sample_id == "SYNTH-CBC-0001"
    assert payload.analyzer == "HumaCount 30TS (SIMULATED)"
    assert {"WBC", "RBC", "HGB", "HCT", "MCV", "PLT"}.issubset(payload.values)
    assert all(item.flag is None for item in payload.values.values())
