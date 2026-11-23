# Backup and restore

## Backup
Run from the project directory after configuring the environment file:

```sh
sh scripts/backup.sh
```

The script creates a compressed PostgreSQL dump plus separate archives of the Docker Compose template_data and result_documents volumes under backups/. The document archive contains uploaded CBC source reports. Keep all backups encrypted, access-controlled and off-host. Test restoration regularly. Do not commit backups to Git.

## Restore database
Stop application writes, identify the target database, then restore a known-good dump:

```sh
gunzip -c backups/cbc-connect-db-YYYYMMDDTHHMMSSZ.sql.gz | docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" "$POSTGRES_DB"'
```

This is a logical restore into the configured database. For a clean restore, create an empty target database first; do not blindly replay into a live database.

## Restore templates
Find the Compose volume with:

```sh
docker volume ls --filter label=com.docker.compose.volume=template_data
```

Then restore the archive into the selected volume:

```sh
docker run --rm -v YOUR_TEMPLATE_VOLUME:/data -v "$PWD/backups:/backup" alpine:3.20 sh -c 'tar -xzf /backup/cbc-connect-templates-YYYYMMDDTHHMMSSZ.tar.gz -C /data'
```

Validate the restored files, database consistency, login, result retrieval and report generation before returning to service.


## Restore uploaded source documents

Find the Compose volume with:

```sh
docker volume ls --filter label=com.docker.compose.volume=result_documents
```

Then restore the matching document archive into the selected volume:

```sh
docker run --rm -v YOUR_DOCUMENT_VOLUME:/data -v "$PWD/backups:/backup" alpine:3.20 sh -c 'tar -xzf /backup/cbc-connect-documents-YYYYMMDDTHHMMSSZ.tar.gz -C /data'
```

Restore the database and document volume from the same backup time so document records continue to point to the correct files.
