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


ROOT = Path(__file__).parent.parent
TOKEN = "fictional-restart-token"
RAW_CONTENT = "Fictional restart acceptance marker: Project Alpha review complete."
ALLOWED_ORIGIN = "https://fictional-staging.example"


class P15ProcessRestartTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
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
                self.fail("Uvicorn exited before the health check succeeded")
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
        self.assertEqual(after["created_at"], before["created_at"])
        self.assertEqual(after["updated_at"], before["updated_at"])

        list_status, list_headers, listing = self._request(
            "GET",
            "/api/v1/captures?page=1&page_size=10",
            authorized=True,
            origin="https://not-allowed.example",
        )
        self.assertEqual(list_status, 200)
        self.assertEqual(listing["pagination"]["total_items"], 1)
        self.assertNotIn("Access-Control-Allow-Origin", list_headers)

        web_status, _, _ = self._request("GET", "/app/")
        self.assertEqual(web_status, 200)

        self._stop_server()
        logs = self.log_path.read_text(encoding="utf-8")
        self.assertNotIn(TOKEN, logs)
        self.assertNotIn(RAW_CONTENT, logs)


if __name__ == "__main__":
    unittest.main()
