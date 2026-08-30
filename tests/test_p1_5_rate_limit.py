from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.config import Settings
from backend.models import CaptureRequest
from backend.providers.mock import MockProvider
from backend.security.rate_limit import InMemoryRateLimiter
from backend.storage.sqlite import CaptureStore


class P15RateLimitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = CaptureStore(Path(self.temp.name) / "rate-limit.sqlite3")
        settings = Settings(
            app_env="production",
            ai_provider="mock",
            database_path=self.store.path,
            auth_mode="token",
            api_auth_token="fictional-production-token",
            allowed_origins=("https://staging.example",),
        )
        limiter = InMemoryRateLimiter(
            limits={
                "capture": 1,
                "retry": 1,
                "read": 1,
                "report": 1,
                "mutation": 1,
            },
            window_seconds=60,
            clock=lambda: 1_020.0,
        )
        self.client = TestClient(
            create_app(
                settings=settings,
                store=self.store,
                provider=MockProvider(),
                rate_limiter=limiter,
            )
        )
        self.headers = {"Authorization": "Bearer fictional-production-token"}
        self.voice = {
            "schema_version": "1",
            "capture_type": "voice",
            "source_type": "voice_transcript",
            "source": None,
            "raw_content": "Fictional rate-limit capture.",
            "requested_processing": "voice_structure",
            "allowed_projects": ["Project Alpha"],
        }

    def test_production_limits_capture_read_retry_and_report_independently(self) -> None:
        created = self.client.post(
            "/api/v1/capture", json=self.voice, headers=self.headers
        )
        self.assertEqual(created.status_code, 200)
        capture_id = created.json()["capture_id"]
        self._assert_rate_limited(
            self.client.post(
                "/api/v1/capture", json=self.voice, headers=self.headers
            )
        )

        self.assertEqual(
            self.client.get("/api/v1/captures", headers=self.headers).status_code,
            200,
        )
        self._assert_rate_limited(
            self.client.get("/api/v1/captures", headers=self.headers)
        )

        report_payload = {
            "report_type": "daily",
            "period": "2026-08-31",
            "capture_ids": [capture_id],
        }
        self.assertEqual(
            self.client.post(
                "/api/v1/reports/preview",
                json=report_payload,
                headers=self.headers,
            ).status_code,
            200,
        )
        self._assert_rate_limited(
            self.client.post(
                "/api/v1/reports/preview",
                json=report_payload,
                headers=self.headers,
            )
        )

        pending = self.store.create(
            CaptureRequest.model_validate(
                dict(
                    self.voice,
                    raw_content="Fictional pending retry.",
                )
            )
        )
        self.store.mark_failure(
            pending.capture_id,
            status="pending",
            error_code="AI_UNAVAILABLE",
            message="AI temporarily unavailable — capture was saved.",
        )
        self.assertEqual(
            self.client.post(
                f"/api/v1/captures/{pending.capture_id}/retry",
                headers=self.headers,
            ).status_code,
            200,
        )
        self._assert_rate_limited(
            self.client.post(
                f"/api/v1/captures/{pending.capture_id}/retry",
                headers=self.headers,
            )
        )

    def test_health_is_not_rate_limited(self) -> None:
        for _ in range(3):
            self.assertEqual(self.client.get("/health").status_code, 200)

    def _assert_rate_limited(self, response) -> None:
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json()["error"]["code"], "RATE_LIMITED")
        self.assertEqual(response.headers["retry-after"], "60")
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual(response.headers["x-content-type-options"], "nosniff")


if __name__ == "__main__":
    unittest.main()
