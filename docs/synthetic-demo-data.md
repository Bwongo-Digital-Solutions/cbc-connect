# Synthetic CBC demo data

CBC Connect includes five fictional CBC result payloads under `backend/demo/`. Each includes a fictional patient name, age, Ugandan-style address, patient reference and sample ID. They populate the dashboard and pending-review queue so a clinic can explore search, patient biodata, result details, original measurements, audit events and the review workflow without entering real patient data.

## Load the clinic demo dataset

From the repository root, after starting the application:

```sh
export CBC_ANALYZER_API_KEY='the-same-key-configured-in-your-.env'
sh scripts/seed-demo-data.sh
```

The script submits each fixture through the normal analyzer-ingestion API. Newly inserted records appear as `PENDING_REVIEW`; the script never creates review records or marks results as approved. Re-running it is safe: new sample/device pairs are inserted; if a sample/device pair already exists, the API fills only missing patient biodata fields and preserves existing identity values and original CBC measurements. Complete existing records are left unchanged. The script does not delete or reset any existing data.

Use `CBC_API_URL` to target a different API address, for example `CBC_API_URL=http://localhost:8900`.

## Individual analyzer-ingestion fixture

To test a single normalized payload instead of the full set:

```sh
export CBC_ANALYZER_API_KEY='the-same-key-configured-in-your-.env'
sh scripts/ingest-synthetic-demo.sh
```

## Safety boundaries

- All patient names, ages, addresses, sample IDs and patient references are fictional. The Ugandan-style locations are illustrative and do not identify real patients.
- Values are generated illustrative software-test values, not reference intervals, medical guidance or diagnostic examples.
- No flags or clinical interpretation are supplied.
- Every fixture identifies the analyzer as `HumaCount 30TS (SIMULATED)`.
- This is not a real HumaCount 30TS export and does not validate a device parser.
- Do not use demo records for patient care or clinical decisions. Keep the demo dataset out of production environments.
