from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener

from backend.models import CaptureRequest
from backend.storage.sqlite import CaptureStore
from tools.p1_5_backup_restore_drill import run_drill


ROOT = Path(__file__).parent.parent
TOKEN = "fictional-restart-token"
RAW_CONTENT = "Fictional restart acceptance marker: Project Alpha review complete."
ALLOWED_ORIGIN = "https://fictional-staging.example"


class P15ProcessRestartTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(
            dir=Path(tempfile.gettempdir()).resolve()
        )
        self.addCleanup(self.temp.cleanup)
        self.temp_path = Path(self.temp.name)
        self.db_path = self.temp_path / "captures.sqlite3"
        self.log_path = self.temp_path / "uvicorn.log"
        self.port = self._available_port()
        self.base_url = f"http://127.0.0.1:{self.port}"
        self.opener = build_opener(ProxyHandler({}))
        self.process: subprocess.Popen[bytes] | None = None
        self.addCleanup(self._stop_server)

    @staticmethod
    def _available_port() -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            return int(sock.getsockname()[1])

    def _start_server(self) -> None:
        environment = os.environ.copy()
        environment.pop("GEMINI_API_KEY", None)
        environment.pop("GEMINI_MODEL", None)
        environment.update(
            {
                "APP_ENV": "production",
                "AI_PROVIDER": "mock",
                "ENABLE_LIVE_AI": "false",
                "AUTH_MODE": "token",
                "API_AUTH_TOKEN": TOKEN,
                "ALLOWED_ORIGINS": ALLOWED_ORIGIN,
                "DATABASE_URL": f"sqlite:///{self.db_path}",
                "PYTHONPATH": os.pathsep.join((str(ROOT), str(ROOT / "src"))),
                "PYTHONPYCACHEPREFIX": str(self.temp_path / "pycache"),
            }
        )
        log_handle = self.log_path.open("ab")
        try:
            self.process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "backend.app:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(self.port),
                ],
                cwd=ROOT,
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
            )
        finally:
            log_handle.close()

        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                diagnostic = self.log_path.read_text(
                    encoding="utf-8", errors="replace"
                )
                diagnostic = diagnostic.replace(TOKEN, "[REDACTED]").replace(
                    RAW_CONTENT, "[REDACTED]"
                )
                self.fail(
                    "Uvicorn exited before the health check succeeded: "
                    + diagnostic[-1_000:]
                )
            try:
                status, _, body = self._request("GET", "/health")
            except (URLError, TimeoutError):
                time.sleep(0.05)
                continue
            if status == 200 and body == {"ok": True, "status": "healthy"}:
                return
            time.sleep(0.05)
        self.fail("Uvicorn did not become healthy within 10 seconds")

    def _stop_server(self) -> None:
        if self.process is None or self.process.poll() is not None:
            return
        self.process.terminate()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=5)

    def _request(
        self,
        method: str,
        path: str,
        *,
        payload: dict | None = None,
        authorized: bool = False,
        origin: str | None = None,
    ) -> tuple[int, object, object]:
        headers = {}
        if authorized:
            headers["Authorization"] = f"Bearer {TOKEN}"
        if origin:
            headers["Origin"] = origin
        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = Request(
            self.base_url + path,
            data=data,
            headers=headers,
            method=method,
        )
        try:
            response = self.opener.open(request, timeout=2)
        except HTTPError as exc:
            response = exc
        raw = response.read()
        content_type = response.headers.get_content_type()
        body = (
            json.loads(raw.decode("utf-8"))
            if raw and content_type == "application/json"
            else raw
        )
        return response.status, response.headers, body

    def test_production_mock_capture_survives_real_process_restart(self) -> None:
        self._start_server()
        payload = {
            "schema_version": "1",
            "capture_type": "voice",
            "source_type": "voice_transcript",
            "source": None,
            "raw_content": RAW_CONTENT,
            "requested_processing": "voice_structure",
            "allowed_projects": ["Project Alpha"],
        }

        unauthorized, _, unauthorized_body = self._request(
            "GET", "/api/v1/captures"
        )
        self.assertEqual(unauthorized, 401)
        self.assertEqual(unauthorized_body["error"]["code"], "AUTH_REQUIRED")

        created_status, created_headers, created = self._request(
            "POST",
            "/api/v1/capture",
            payload=payload,
            authorized=True,
            origin=ALLOWED_ORIGIN,
        )
        self.assertEqual(created_status, 200)
        self.assertEqual(created["status"], "processed")
        self.assertIn(RAW_CONTENT, created["result"]["markdown"])
        self.assertEqual(
            created_headers.get("Access-Control-Allow-Origin"), ALLOWED_ORIGIN
        )
        capture_id = created["capture_id"]

        before_status, _, before = self._request(
            "GET", f"/api/v1/captures/{capture_id}", authorized=True
        )
        self.assertEqual(before_status, 200)
        self.assertEqual(before["raw_content"], RAW_CONTENT)
        self.assertEqual(before["status"], "processed")

        review_status, _, reviewed = self._request(
            "PATCH",
            f"/api/v1/captures/{capture_id}",
            payload={"reviewed": True, "assigned_project": "Project Alpha"},
            authorized=True,
        )
        self.assertEqual(review_status, 200)
        self.assertTrue(reviewed["reviewed"])
        self.assertEqual(reviewed["assigned_project"], "Project Alpha")

        pending_status, _, pending = self._request(
            "POST",
            "/api/v1/capture",
            payload={
                "schema_version": "1",
                "capture_type": "content",
                "source_type": "video_url",
                "source": "https://example.com/fictional-video",
                "raw_content": "",
                "requested_processing": "summary",
                "allowed_projects": [],
            },
            authorized=True,
        )
        self.assertEqual(pending_status, 202)
        self.assertEqual(pending["status"], "pending")
        pending_id = pending["capture_id"]

        retry_status, _, retried = self._request(
            "POST", f"/api/v1/captures/{pending_id}/retry", authorized=True
        )
        self.assertEqual(retry_status, 202)
        self.assertEqual(retried["status"], "pending")

        today_status, _, today = self._request(
            "GET", "/api/v1/dashboard/today", authorized=True
        )
        self.assertEqual(today_status, 200)
        self.assertEqual(today["pending_count"], 1)

        projects_status, _, projects = self._request(
            "GET", "/api/v1/projects", authorized=True
        )
        self.assertEqual(projects_status, 200)
        self.assertEqual(projects["data"][0]["project"], "Project Alpha")

        pending_list_status, _, pending_list = self._request(
            "GET",
            "/api/v1/captures?page=1&page_size=10&status=pending",
            authorized=True,
        )
        self.assertEqual(pending_list_status, 200)
        self.assertEqual(pending_list["pagination"]["total_items"], 1)
        self.assertEqual(pending_list["data"][0]["capture_id"], pending_id)

        report_status, _, report = self._request(
            "POST",
            "/api/v1/reports/preview",
            payload={
                "report_type": "daily",
                "period": "Fictional local restart rehearsal",
                "capture_ids": [capture_id],
            },
            authorized=True,
        )
        self.assertEqual(report_status, 200)
        self.assertFalse(report["sent"])
        self.assertFalse(report["published"])

        _, _, processed_before_restart = self._request(
            "GET", f"/api/v1/captures/{capture_id}", authorized=True
        )
        _, _, pending_before_restart = self._request(
            "GET", f"/api/v1/captures/{pending_id}", authorized=True
        )

        self._stop_server()
        self.process = None
        self._start_server()

        after_status, _, after = self._request(
            "GET", f"/api/v1/captures/{capture_id}", authorized=True
        )
        self.assertEqual(after_status, 200)
        self.assertEqual(after["capture_id"], capture_id)
        self.assertEqual(after["raw_content"], RAW_CONTENT)
        self.assertEqual(after["status"], "processed")
        self.assertEqual(after["created_at"], processed_before_restart["created_at"])
        self.assertEqual(after["updated_at"], processed_before_restart["updated_at"])
        self.assertTrue(after["reviewed"])
        self.assertEqual(after["assigned_project"], "Project Alpha")

        pending_after_status, _, pending_after = self._request(
            "GET", f"/api/v1/captures/{pending_id}", authorized=True
        )
        self.assertEqual(pending_after_status, 200)
        self.assertEqual(pending_after["status"], "pending")
        self.assertEqual(pending_after["retry_count"], 1)
        self.assertEqual(pending_after["raw_content"], "")
        self.assertEqual(
            pending_after["created_at"], pending_before_restart["created_at"]
        )
        self.assertEqual(
            pending_after["updated_at"], pending_before_restart["updated_at"]
        )

        list_status, list_headers, listing = self._request(
            "GET",
            "/api/v1/captures?page=1&page_size=10",
            authorized=True,
            origin="https://not-allowed.example",
        )
        self.assertEqual(list_status, 200)
        self.assertEqual(listing["pagination"]["total_items"], 2)
        self.assertNotIn("Access-Control-Allow-Origin", list_headers)

        web_status, _, _ = self._request("GET", "/app/")
        self.assertEqual(web_status, 200)

        self._stop_server()
        logs = self.log_path.read_text(encoding="utf-8")
        self.assertNotIn(TOKEN, logs)
        self.assertNotIn(RAW_CONTENT, logs)

    def test_restored_five_record_database_is_readable_after_server_start(self) -> None:
        source = self.temp_path / "source.sqlite3"
        backup = self.temp_path / "backup.sqlite3"
        restore = self.temp_path / "restore.sqlite3"
        store = CaptureStore(source)
        capture_ids = []

        for index in range(3):
            record = store.create(
                CaptureRequest(
                    schema_version="1",
                    capture_type="content",
                    source_type="selected_text",
                    source=None,
                    raw_content=f"FICTIONAL-RESTORE-PROCESSED-{index + 1:02d}",
                    requested_processing="raw_save",
                    allowed_projects=[],
                )
            )
            store.mark_processed(record.capture_id, None, "# Fictional restored item")
            capture_ids.append(record.capture_id)

        pending = store.create(
            CaptureRequest(
                schema_version="1",
                capture_type="content",
                source_type="selected_text",
                source=None,
                raw_content="FICTIONAL-RESTORE-PENDING-01",
                requested_processing="raw_save",
                allowed_projects=[],
            )
        )
        store.begin_retry(pending.capture_id)
        store.mark_failure(
            pending.capture_id,
            status="pending",
            error_code="AI_UNAVAILABLE",
            message="Fictional pending state.",
        )
        capture_ids.append(pending.capture_id)

        failed = store.create(
            CaptureRequest(
                schema_version="1",
                capture_type="content",
                source_type="selected_text",
                source=None,
                raw_content="FICTIONAL-RESTORE-FAILED-01",
                requested_processing="raw_save",
                allowed_projects=[],
            )
        )
        store.mark_failure(
            failed.capture_id,
            status="failed",
            error_code="INTERNAL_ERROR",
            message="Fictional failed state.",
        )
        capture_ids.append(failed.capture_id)

        evidence = run_drill(
            source=source,
            backup=backup,
            restore=restore,
            expected_capture_ids=capture_ids,
        )
        self.assertEqual(
            evidence["status_counts"],
            {"processed": 3, "pending": 1, "failed": 1},
        )
        self.assertGreaterEqual(evidence["restore_duration_ms"], 0)

        self.db_path = restore
        self._start_server()

        expected_statuses = [
            "processed",
            "processed",
            "processed",
            "pending",
            "failed",
        ]
        for capture_id, expected_status in zip(capture_ids, expected_statuses):
            status, _, record = self._request(
                "GET", f"/api/v1/captures/{capture_id}", authorized=True
            )
            self.assertEqual(status, 200)
            self.assertEqual(record["capture_id"], capture_id)
            self.assertEqual(record["status"], expected_status)
            self.assertIn("FICTIONAL-RESTORE-", record["raw_content"])
        self.assertEqual(
            self._request(
                "GET", f"/api/v1/captures/{pending.capture_id}", authorized=True
            )[2]["retry_count"],
            1,
        )

        list_status, _, listing = self._request(
            "GET", "/api/v1/captures?page=1&page_size=10", authorized=True
        )
        self.assertEqual(list_status, 200)
        self.assertEqual(listing["pagination"]["total_items"], 5)
        self.assertTrue(all("raw_content" not in item for item in listing["data"]))

        web_status, _, _ = self._request("GET", "/app/")
        self.assertEqual(web_status, 200)

        self._stop_server()
        logs = self.log_path.read_text(encoding="utf-8")
        self.assertNotIn(TOKEN, logs)
        self.assertNotIn("FICTIONAL-RESTORE-", logs)


if __name__ == "__main__":
    unittest.main()
