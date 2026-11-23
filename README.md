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
# Edit .env and replace every placeholder with unique random secrets
docker compose up --build
```
Dashboard: http://localhost:5173  
API documentation: http://localhost:8900/docs  
Health: http://localhost:8900/health

## Authentication and access
- The initial administrator is created from CBC_BOOTSTRAP_ADMIN and CBC_BOOTSTRAP_PASSWORD on first startup.
- Sign in through the dashboard. Additional staff accounts are created by an administrator with POST /api/v1/users and one of TECHNICIAN, SUPERVISOR or ADMIN roles.
- API sessions use expiring JWT bearer tokens. Analyzer ingestion uses the separate X-Analyzer-Key header.
- Configure HTTPS, secure secrets and backups before using any network-accessible deployment.

## Report templates
DOCX templates are rendered with docxtpl and converted to PDF using headless LibreOffice. Template authors can use these Jinja placeholders: sample_id, patient_reference, analyzer, reviewer, comments, received_at, reviewed_at, and results. The results variable is a list of objects with code, value, unit and flag fields. Uploaded PDF files are retained for reference but are not mergeable templates.

## API overview
- `GET /api/v1/dashboard`
- `GET /api/v1/results?status=PENDING_REVIEW&q=...`
- `GET /api/v1/results/{id}`
- `POST /api/v1/samples`
- `POST /api/v1/analyzer/ingest` (normalized development payload; not a claim that HumaCount speaks JSON)
- `POST /api/v1/results/{id}/review`
- `GET/POST /api/v1/analytes`
- `GET/POST /api/v1/templates`
- `POST /api/v1/auth/login`
- `POST /api/v1/users` (administrator)
- `GET/POST /api/v1/reference-intervals` and `POST /api/v1/reference-intervals/{id}/verify` (second-person review)

## Important limitations
This is still an engineering development build. Authentication and role checks, migrations, basic automated tests, DOCX merge/PDF rendering, and backup scripts are implemented as development foundations. They have not yet undergone security testing, operational acceptance or clinical validation. The HumaCount parser remains intentionally disabled until real device exports and protocol settings are supplied. Reference intervals are stored as drafts and are not used for automatic flags. Review and user-management audit actors are taken from the authenticated account; the reviewer text supplied by the browser is not trusted as identity. Do not deploy with patient-identifiable data or use this system for clinical decisions until those controls and validations are completed.

## Synthetic analyzer demo
Use `sh scripts/ingest-synthetic-demo.sh` with `CBC_ANALYZER_API_KEY` set to the API's configured key. The fixture at `backend/demo/synthetic_cbc_export.json` is fictional normalized JSON, not a real HumaCount protocol export. See `docs/synthetic-demo-data.md`.

## Backup and restore
See docs/backup-restore.md and run sh scripts/backup.sh for database and template-volume backups.

## HumaCount 30TS
Do not assume a protocol. Confirm the exact model/firmware, configured serial/TCP interface, protocol/export format and settings. Obtain de-identified sample messages/exports and validate a device-specific parser. The JSON ingestion endpoint accepts normalized development data only.

## Integration sequence
1. Complete and validate standalone CBC Connect.
2. Add an optional Bahmni Lite adapter using the installed Lab Lite version's supported interfaces.
3. Add an optional Bahmni Standard adapter using supported OpenELIS APIs/import mechanisms.

Never write directly to OpenMRS or OpenELIS databases. Use synthetic data until security, device parsing, workflow and clinical validation are complete.
