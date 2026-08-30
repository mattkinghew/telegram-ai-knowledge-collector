from __future__ import annotations

import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path

from backend.models import CaptureRequest
from backend.storage.sqlite import CaptureStore
from tools.p1_5_backup_restore_drill import DrillError, run_drill


class P15BackupRestoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(
            dir=Path(tempfile.gettempdir()).resolve()
        )
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source.sqlite3"
        self.backup = self.root / "backup.sqlite3"
        self.restore = self.root / "restore.sqlite3"
        self.store = CaptureStore(self.source)
        self.capture_ids = self._seed_required_records()

    def _request(self, marker: str) -> CaptureRequest:
        return CaptureRequest(
            schema_version="1",
            capture_type="content",
            source_type="selected_text",
            source=None,
            raw_content=marker,
            requested_processing="raw_save",
            allowed_projects=[],
        )

    def _seed_required_records(self):
        capture_ids = []
        for index in range(3):
            record = self.store.create(
                self._request(f"FICTIONAL-BACKUP-PROCESSED-{index + 1:02d}")
            )
            self.store.mark_processed(record.capture_id, None, "# Fictional processed")
            capture_ids.append(record.capture_id)

        pending = self.store.create(self._request("FICTIONAL-BACKUP-PENDING-01"))
        self.store.begin_retry(pending.capture_id)
        self.store.mark_failure(
            pending.capture_id,
            status="pending",
            error_code="AI_UNAVAILABLE",
            message="Fictional pending state.",
        )
        capture_ids.append(pending.capture_id)

        failed = self.store.create(self._request("FICTIONAL-BACKUP-FAILED-01"))
        self.store.mark_failure(
            failed.capture_id,
            status="failed",
            error_code="INTERNAL_ERROR",
            message="Fictional failed state.",
        )
        capture_ids.append(failed.capture_id)
        return capture_ids

    def test_drill_preserves_all_record_fields_and_returns_sanitized_evidence(self) -> None:
        expected = {
            capture_id: asdict(self.store.get(capture_id))
            for capture_id in self.capture_ids
        }

        evidence = run_drill(
            source=self.source,
            backup=self.backup,
            restore=self.restore,
            expected_capture_ids=self.capture_ids,
        )

        self.assertTrue(evidence["ok"])
        self.assertEqual(evidence["capture_count"], 5)
        self.assertEqual(
            evidence["status_counts"],
            {"processed": 3, "pending": 1, "failed": 1},
        )
        self.assertEqual(evidence["integrity"], "ok")
        self.assertEqual(len(evidence["backup_sha256"]), 64)
        serialized = repr(evidence)
        for capture_id in self.capture_ids:
            self.assertNotIn(capture_id, serialized)
        self.assertNotIn("FICTIONAL-BACKUP", serialized)

        restored = CaptureStore(self.restore)
        actual = {
            capture_id: asdict(restored.get(capture_id))
            for capture_id in self.capture_ids
        }
        self.assertEqual(actual, expected)

    def test_drill_fails_closed_for_protected_or_existing_targets(self) -> None:
        with self.assertRaises(DrillError):
            run_drill(
                source=self.root / "Private" / "source.sqlite3",
                backup=self.backup,
                restore=self.restore,
                expected_capture_ids=self.capture_ids,
            )

        self.backup.write_bytes(b"do-not-overwrite")
        with self.assertRaises(DrillError):
            run_drill(
                source=self.source,
                backup=self.backup,
                restore=self.restore,
                expected_capture_ids=self.capture_ids,
            )
        self.assertEqual(self.backup.read_bytes(), b"do-not-overwrite")


if __name__ == "__main__":
    unittest.main()
