# P1.5 Backup and Restore Drill

Status: `PREPARED` / drill not executed. Run in an isolated local or staging
test environment with fictional data only.

## Preconditions

- [ ] Record the exact app commit and source `DATABASE_URL` without including a
  token or protected/personal path.
- [ ] Confirm `sqlite3` is available and the destination has enough space.
- [ ] Create a new restricted evidence directory outside Git.
- [ ] Keep the source service available only to the operator during the drill.

## Create known records

Create and record two identifiers through `POST /api/v1/capture`:

1. A processed `raw_save` capture containing `FICTIONAL-BACKUP-PROCESSED-01`.
2. A deterministic pending capture using the fictional source
   `https://example.com/fictional-backup-pending-01`, `source_type=video_url`,
   empty `raw_content`, and `requested_processing=summary`; retry it once so it
   keeps `status=pending`, `error_code=URL_FETCH_FAILED`, and `retry_count=1`
   without a network call.

| Record | `capture_id` | Status | Retry count | Raw marker |
|---|---|---|---:|---|
| Processed | | `processed` | 0 | FICTIONAL-BACKUP-PROCESSED-01 |
| Pending | | `pending` | 1 | Exact fictional URL; raw text empty by contract |

## Backup

Resolve all paths explicitly before running commands. Do not use a Vault,
protected path, `.env`, or repository-tracked destination.

```bash
SOURCE_DB=/absolute/path/to/p1_5_capture.sqlite3
BACKUP_DB=/absolute/restricted/evidence/p1_5_capture.backup.sqlite3
test -f "$SOURCE_DB"
test ! -e "$BACKUP_DB"
sqlite3 "$SOURCE_DB" ".backup '$BACKUP_DB'"
test -s "$BACKUP_DB"
sqlite3 "$BACKUP_DB" "PRAGMA integrity_check;"
```

Require a non-empty backup and exactly `ok` from `PRAGMA integrity_check`.
Record backup start/end in UTC, byte size, and a SHA-256 checksum. Store only
the checksum and evidence path in the acceptance record, not database content.

## Restore into a clean environment

1. Create a new empty test directory outside Git and set `RESTORE_DB` to a new
   filename. Refuse to continue if that file already exists.
2. Copy the verified backup to `RESTORE_DB` and run
   `sqlite3 "$RESTORE_DB" "PRAGMA integrity_check;"`.
3. Start the exact app commit on loopback with `APP_ENV=test`, `AUTH_MODE=dev`,
   `AI_PROVIDER=mock`, an explicit loopback `ALLOWED_ORIGINS`, and
   `DATABASE_URL=sqlite:///$RESTORE_DB`.
4. Query both known IDs through `GET /api/v1/captures/{capture_id}`.
5. Stop the isolated test server after evidence collection.

Do not point the restored instance at the source database or a real Vault. Do
not overwrite the source database as part of this drill.

## Acceptance record

| Check | Expected | Observed | Evidence reference |
|---|---|---|---|
| Backup exists | Non-empty file | | |
| SQLite integrity | `ok` before and after restore | | |
| Capture rows | Both IDs present | | |
| Processing state | Processed and pending retained | | |
| Retry metadata | Counts 0 and 1 retained | | |
| Raw/source input | Exact fictional markers retained | | |
| Result separation | Processed result retained; pending result absent | | |
| Corruption | None observed | | |
| Restore time | Start/end and elapsed duration recorded | | |

Result: `PENDING` until the user supplies drill evidence. A copied file without
integrity and record-level verification is not an accepted restore.
