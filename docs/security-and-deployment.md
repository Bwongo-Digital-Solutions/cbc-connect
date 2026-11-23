# Security and deployment baseline

- Set unique high-entropy values for database password, CBC_JWT_SECRET (at least 32 characters), bootstrap administrator password and analyzer API key.
- Keep the environment file, backups, exports and logs containing patient data out of Git and restrict filesystem permissions.
- Bootstrap admin is created only when absent. Create named staff accounts through authenticated POST /api/v1/users; roles are TECHNICIAN, SUPERVISOR and ADMIN.
- Access tokens expire after the configured CBC_TOKEN_MINUTES (default 30). Use HTTPS through a properly configured reverse proxy in any non-local deployment.
- Restrict network access to the API, database and analyzer receiver. The database is not published to the host by Compose.
- Analyzer ingestion requires the separate X-Analyzer-Key; use a unique key per installation and rotate it after compromise.
- Review and user-management audit entries use authenticated account identity. Do not share accounts.
- Configure host firewall, TLS, secure backups, monitoring, patching, retention and incident response before production.
- This baseline does not constitute a penetration test or regulatory compliance certification.
