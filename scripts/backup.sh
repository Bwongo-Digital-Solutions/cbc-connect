#!/usr/bin/env sh
set -eu
mkdir -p backups
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
db_file="backups/cbc-connect-db-$stamp.sql.gz"
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' | gzip > "$db_file"
volume="$(docker volume ls -q --filter label=com.docker.compose.volume=template_data | head -n 1)"
if [ -z "$volume" ]; then
  echo "Could not locate the Compose template_data volume" >&2
  exit 1
fi
docker run --rm -v "$volume:/data:ro" -v "$PWD/backups:/backup" alpine:3.20 \
  tar -czf "/backup/cbc-connect-templates-$stamp.tar.gz" -C /data .
echo "Created $db_file and backups/cbc-connect-templates-$stamp.tar.gz"
