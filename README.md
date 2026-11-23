# CBC Connect

Standalone CBC analyzer results receiving and review platform. This repository starts with the independent CBC Connect application; Bahmni Lite Lab Lite and Bahmni Standard OpenELIS adapters are later milestones.

## Current scope
- FastAPI backend with PostgreSQL persistence.
- React + TypeScript dashboard.
- Protocol-neutral analyzer ingestion endpoint.
- Incoming results remain **PENDING_REVIEW**; ingestion never approves or finalizes clinical results.
- Docker Compose development environment.

## Run
```bash
cp .env.example .env
docker compose up --build
```
Dashboard: http://localhost:5173 · API docs: http://localhost:8000/docs · Health: http://localhost:8000/health

## HumaCount 30TS
Do not assume a protocol. Confirm the actual model/firmware, configured serial/TCP interface, protocol/export format and settings. Obtain de-identified sample messages/exports and validate a device-specific parser. The JSON ingestion endpoint is a normalized development interface, not a claim that the analyzer speaks JSON.

## Milestones
1. Standalone CBC Connect: receiving, sample/result queue, review workflow, mappings and report templates.
2. Bahmni Lite: optional adapter using the deployed Lab Lite version's supported interfaces.
3. Bahmni Standard: optional OpenELIS adapter using supported APIs/import mechanisms.

Never write directly to OpenMRS or OpenELIS databases. This is an engineering scaffold, not a clinically validated LIS. Use synthetic data until security, workflow, device parsing and clinical validation are complete.
