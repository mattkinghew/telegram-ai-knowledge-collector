# P1.5 Backup and Restore Drill

Status: local mechanics `AUTOMATED_PASS`; staging drill `PENDING`. Use a
maintenance window and fictional staging data only. Never target a Vault,
protected path, `.env`, symlink, or existing backup/restore file.

## Required records

Create through the staged application flow and record five IDs outside Git:

| Record | Required state | Retry count | Fictional marker |
|---|---|---:|---|
| Processed 1 | `processed` | 0 | `FICTIONAL-BACKUP-PROCESSED-01` |
| Processed 2 | `processed` | 0 | `FICTIONAL-BACKUP-PROCESSED-02` |
| Processed 3 | `processed` | 0 | `FICTIONAL-BACKUP-PROCESSED-03` |
| Pending | `pending` | 1 | `FICTIONAL-BACKUP-PENDING-01` |
| Failed | `failed` | recorded | `FICTIONAL-BACKUP-FAILED-01` |

Use a controlled provider failure for pending and a separately approved
controlled internal-error test for failed. Do not corrupt the database or add a
public test endpoint. If the failed state cannot be produced safely in staging,
stop and leave this gate `PENDING`.

## Backup and clean restore

1. Record the exact commit, deployment ID, source SQLite path, and UTC start.
2. Pause writes or enable a maintenance window. Do not rely on a filesystem
   copy of a live database.
3. Choose new backup and restore files on the persistent disk. The tool refuses
   protected paths, symlinks, missing parents, existing targets, and any record
   set other than three processed, one pending, and one failed.
4. Run the standard-library Online Backup drill:

```bash
PYTHONPATH=src python3 tools/p1_5_backup_restore_drill.py \
  --source /absolute/staging-data/p1_5_capture.sqlite3 \
  --backup /absolute/staging-data/evidence/p1_5_capture.backup.sqlite3 \
  --restore /absolute/staging-data/evidence/p1_5_capture.restore.sqlite3 \
  --expected-capture-id ID_1 \
  --expected-capture-id ID_2 \
  --expected-capture-id ID_3 \
  --expected-capture-id ID_4 \
  --expected-capture-id ID_5
```

The JSON output contains only count, status counts, integrity, backup size,
SHA-256 checksum, and restore duration. It never prints IDs or record content.

## Restart and application verification

1. Point a clean isolated service instance at the restored file; never
   overwrite the source database.
2. Restart the service and require `/health` HTTP 200.
3. Query all five known IDs with authenticated GET and compare every stored
   field to the pre-backup evidence: source, raw content, status, retry count,
   timestamps, result, and Markdown.
4. Load Today, Inbox, Projects, Pending, and Reports against the restored store.
5. Record UTC end and the tool's `restore_duration_ms`, then restore the normal
   staging configuration.

| Check | Expected | Observed | Safe evidence reference |
|---|---|---|---|
| Integrity | `ok` for backup and restore | | |
| Capture IDs | All five preserved | | |
| Raw/source | Exact fictional values preserved | | |
| Status | 3 processed / 1 pending / 1 failed | | |
| Retry count | Exact values preserved | | |
| Timestamps | Exact values preserved | | |
| Corruption | None | | |
| Web App restored read | All required views load | | |
| Restore duration | Recorded range/value | | |

The repository test proves local mechanics only. Staging remains `PENDING`
until restart and Web App evidence are supplied.
