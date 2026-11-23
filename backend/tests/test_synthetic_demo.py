import json
from pathlib import Path
from app.schemas import AnalyzerPayload


def test_all_synthetic_demo_payloads_match_normalized_ingest_schema():
    fixtures = sorted((Path(__file__).parents[1] / "demo").glob("synthetic_cbc_export*.json"))
    assert len(fixtures) >= 5
    sample_ids = set()
    for fixture in fixtures:
        raw = json.loads(fixture.read_text(encoding="utf-8"))
        notice = raw.pop("_demo_notice")
        assert notice.startswith("SYNTHETIC TRAINING DATA ONLY")
        payload = AnalyzerPayload.model_validate(raw)
        assert payload.analyzer == "HumaCount 30TS (SIMULATED)"
        assert len(payload.values) >= 15
        assert all(item.flag is None for item in payload.values.values())
        assert payload.sample_id.startswith("SYNTH-CBC-")
        sample_ids.add(payload.sample_id)
    assert len(sample_ids) == len(fixtures)
