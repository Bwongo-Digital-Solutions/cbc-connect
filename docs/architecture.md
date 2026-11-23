# Architecture

Analyzer interface -> device-specific receiver/parser -> normalized CBC payload -> sample matching and duplicate checks -> pending-review result -> authorized review -> optional destination adapter.

Keep protocol parsing separate from the normalized result model. Store raw source messages only after secure retention/redaction controls are designed.

## Integrity requirements
- All incoming results start as PENDING_REVIEW.
- Preserve analyzer values; corrections are separate reviewed values with actor, reason and timestamp.
- Match by accession/sample/barcode identifiers; ambiguous matches require manual resolution.
- Detect duplicates by device and sample/run identity.
- Audit ingestion, mapping, review, correction and export events.
- Add authentication, role-based access, TLS, secrets, backups and retention controls before real patient data.

## Milestones
1. Standalone CBC Connect receiver, review queue, mappings, templates and print/export.
2. Bahmni Lite Lab Lite adapter after verifying deployed version and supported API.
3. Bahmni Standard OpenELIS adapter after verifying topology and supported integration.
Never write directly to OpenMRS or OpenELIS databases.
