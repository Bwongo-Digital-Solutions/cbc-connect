# Synthetic CBC demo

This fixture exercises the normalized JSON ingestion endpoint only. It is deliberately labelled **synthetic** and does not represent the HumaCount 30TS vendor protocol, serial output, network framing or a real patient.

## Run

1. Configure CBC_ANALYZER_API_KEY in the API container environment and restart the API.
2. From the repository root, export the exact same key and run:

```sh
export CBC_ANALYZER_API_KEY='your-configured-demo-key'
sh scripts/ingest-synthetic-demo.sh
```

You can override the API address with CBC_API_URL, for example:

```sh
CBC_API_URL=http://localhost:8000 sh scripts/ingest-synthetic-demo.sh
```

3. Open the dashboard and search for sample SYNTH-CBC-0001. It should appear as PENDING_REVIEW.
4. Open the result, inspect the original values, then complete the review workflow using a signed-in staff account.
5. The sample/device pair is intentionally unique. Re-running the script returns HTTP 409 as duplicate protection is expected. Use a new synthetic sample ID and matching device ID in a copied fixture to test a second ingestion.

## Safety boundaries

- All identifiers are fictional.
- Values are illustrative software-test data, not reference intervals or medical guidance.
- No abnormal flags or clinical interpretation are supplied.
- The analyzer name explicitly says SIMULATED.
- Do not connect this fixture to a live analyzer or use it for patient care.
- This is not a HumaCount 30TS parser test. Real device parsing remains disabled until the exact model/firmware/interface and genuine de-identified exports are available.
