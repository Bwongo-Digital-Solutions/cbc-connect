# CBC Connect

CBC Connect is an independent CBC analyzer results receiving and review workspace. It is being developed as a standalone product first, with optional Bahmni Lite Lab Lite and Bahmni Standard OpenELIS adapters planned later.

## Current standalone development workflow
- Results dashboard with status filtering and search by sample or patient reference.
- Manual sample registration using the laboratory accession/barcode as the sample ID.
- Protocol-neutral JSON ingestion endpoint for normalized analyzer payloads.
- Detailed result view showing original analyzer values.
- Review submission stores reviewed values separately; it never overwrites the original analyzer measurements.
- Pending results move to `REVIEWED` only after a review record is submitted.
- Per-result audit events for registration, ingestion, review and template upload.
- Configurable analyte display names, units and decimal precision. Configuration does not convert incoming values.
- DOCX/PDF report-template file upload and metadata listing.

## Run locally
```bash
cp .env.example .env
docker compose up --build
```
Dashboard: http://localhost:5173  
API documentation: http://localhost:8000/docs  
Health: http://localhost:8000/health

## API overview
- `GET /api/v1/dashboard`
- `GET /api/v1/results?status=PENDING_REVIEW&q=...`
- `GET /api/v1/results/{id}`
- `POST /api/v1/samples`
- `POST /api/v1/analyzer/ingest` (normalized development payload; not a claim that HumaCount speaks JSON)
- `POST /api/v1/results/{id}/review`
- `GET/POST /api/v1/analytes`
- `GET/POST /api/v1/templates`

## Important limitations
This is still an engineering development build. Authentication, role-based authorization, secure identity management, report rendering/merge and PDF generation, validated device parsing, backup/restore, deployment hardening, and clinical validation are not implemented. The reviewer field is an audit label, not proof of identity or authorization. Do not deploy with patient-identifiable data or use this system for clinical decisions until those controls and validations are completed.

## HumaCount 30TS
Do not assume a protocol. Confirm the exact model/firmware, configured serial/TCP interface, protocol/export format and settings. Obtain de-identified sample messages/exports and validate a device-specific parser. The JSON ingestion endpoint accepts normalized development data only.

## Integration sequence
1. Complete and validate standalone CBC Connect.
2. Add an optional Bahmni Lite adapter using the installed Lab Lite version's supported interfaces.
3. Add an optional Bahmni Standard adapter using supported OpenELIS APIs/import mechanisms.

Never write directly to OpenMRS or OpenELIS databases. Use synthetic data until security, device parsing, workflow and clinical validation are complete.
