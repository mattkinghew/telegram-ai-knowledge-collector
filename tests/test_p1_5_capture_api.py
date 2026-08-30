from __future__ import annotations

import logging
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.config import Settings, SettingsError
from backend.providers.base import ProviderFailure
from backend.providers.mock import MockProvider
from backend.services.extraction import ExtractedArticle
from backend.storage.sqlite import CaptureStore


class UnavailableThenMockProvider:
    def __init__(self) -> None:
        self.calls = 0

    def process(self, request):
        self.calls += 1
        if self.calls == 1:
            return ProviderFailure(
                error_code="AI_UNAVAILABLE",
                message="AI temporarily unavailable — capture was saved.",
            )
        return MockProvider().process(request)


class NoCallProvider:
    def process(self, request):
        raise AssertionError("provider must not be called")


class LeakyFailureProvider:
    def process(self, request):
        return ProviderFailure(
            error_code="AI_UNAVAILABLE",
            message="provider leaked: " + request.raw_content,
        )


class FixtureExtractor:
    def __init__(self) -> None:
        self.calls = []

    def extract(self, url: str) -> ExtractedArticle:
        self.calls.append(url)
        return ExtractedArticle(
            final_url=url,
            content_type="text/html",
            text="Fictional extracted article text for review.",
        )


class P15CaptureAPITests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db_path = Path(self.temp.name) / "api.sqlite3"
        self.settings = Settings(
            app_env="test",
            ai_provider="mock",
            database_path=self.db_path,
            auth_mode="token",
            api_auth_token="fictional-test-token",
            allowed_origins=("http://127.0.0.1:8000",),
        )
        self.store = CaptureStore(self.db_path)
        self.provider = MockProvider()
        self.client = TestClient(
            create_app(
                settings=self.settings,
                store=self.store,
                provider=self.provider,
                extractor=FixtureExtractor(),
            )
        )
        self.headers = {"Authorization": "Bearer fictional-test-token"}
        self.voice = {
            "schema_version": "1",
            "capture_type": "voice",
            "source_type": "voice_transcript",
            "source": None,
            "raw_content": "完成 fictional API test，下一步 review。",
            "requested_processing": "voice_structure",
            "allowed_projects": ["Project Alpha"],
        }

    def test_health_is_public_and_contains_no_configuration(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"ok": True, "status": "healthy"})
        self.assertEqual(response.headers["x-content-type-options"], "nosniff")
        self.assertEqual(self.client.get("/openapi.json").status_code, 404)

    def test_deployed_mode_cannot_disable_authentication(self) -> None:
        with self.assertRaises(SettingsError):
            Settings(
                app_env="production",
                ai_provider="mock",
                database_path=self.db_path,
                auth_mode="dev",
                api_auth_token=None,
                allowed_origins=("https://app.example",),
            )

        macos_system_path = Path("/private/tmp/p1_5_fictional.sqlite3")
        settings = Settings(
            app_env="production",
            ai_provider="mock",
            database_path=macos_system_path,
            auth_mode="token",
            api_auth_token="fictional-production-token",
            allowed_origins=("https://app.example",),
        )
        self.assertEqual(settings.database_path, macos_system_path)

        with self.assertRaises(SettingsError):
            Settings(
                app_env="production",
                ai_provider="mock",
                database_path=Path("/private/tmp/Private/captures.sqlite3"),
                auth_mode="token",
                api_auth_token="fictional-production-token",
                allowed_origins=("https://app.example",),
            )
        with self.assertRaises(SettingsError):
            Settings(
                app_env="production",
                ai_provider="mock",
                database_path=Path("Private") / "captures.sqlite3",
                auth_mode="token",
                api_auth_token="fictional-production-token",
                allowed_origins=("https://app.example",),
            )

    def test_non_health_endpoints_reject_missing_and_invalid_auth(self) -> None:
        for headers in ({}, {"Authorization": "Bearer wrong-token"}):
            with self.subTest(headers=headers):
                response = self.client.get("/api/v1/captures", headers=headers)
                self.assertEqual(response.status_code, 401)
                self.assertEqual(response.json()["error"]["code"], "AUTH_REQUIRED")

    def test_capture_status_and_list_form_one_processed_flow(self) -> None:
        created = self.client.post(
            "/api/v1/capture", json=self.voice, headers=self.headers
        )
        self.assertEqual(created.status_code, 200)
        body = created.json()
        self.assertTrue(body["ok"])
        self.assertEqual(body["status"], "processed")
        self.assertIn(self.voice["raw_content"], body["result"]["markdown"])

        status = self.client.get(
            "/api/v1/captures/" + body["capture_id"], headers=self.headers
        )
        self.assertEqual(status.status_code, 200)
        self.assertEqual(status.json()["raw_content"], self.voice["raw_content"])

        listing = self.client.get(
            "/api/v1/captures?page=1&page_size=10&status=processed",
            headers=self.headers,
        )
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.json()["pagination"]["total_items"], 1)

    def test_raw_save_never_calls_provider(self) -> None:
        app = create_app(
            settings=self.settings,
            store=CaptureStore(Path(self.temp.name) / "raw.sqlite3"),
            provider=NoCallProvider(),
            extractor=FixtureExtractor(),
        )
        client = TestClient(app)
        payload = dict(self.voice, requested_processing="raw_save")
        response = client.post("/api/v1/capture", json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "processed")
        self.assertIn("ai_status: none", response.json()["result"]["markdown"])

    def test_provider_failure_is_pending_and_manual_retry_can_process(self) -> None:
        provider = UnavailableThenMockProvider()
        store = CaptureStore(Path(self.temp.name) / "retry.sqlite3")
        client = TestClient(
            create_app(
                settings=self.settings,
                store=store,
                provider=provider,
                extractor=FixtureExtractor(),
            )
        )
        created = client.post("/api/v1/capture", json=self.voice, headers=self.headers)
        self.assertEqual(created.status_code, 202)
        self.assertEqual(created.json()["status"], "pending")
        capture_id = created.json()["capture_id"]
        self.assertEqual(store.get(capture_id).raw_content, self.voice["raw_content"])

        retried = client.post(
            "/api/v1/captures/" + capture_id + "/retry", headers=self.headers
        )
        self.assertEqual(retried.status_code, 200)
        self.assertEqual(retried.json()["status"], "processed")
        self.assertEqual(store.get(capture_id).retry_count, 1)

    def test_article_url_uses_extracted_text_but_preserves_original_raw(self) -> None:
        extractor = FixtureExtractor()
        store = CaptureStore(Path(self.temp.name) / "url.sqlite3")
        client = TestClient(
            create_app(
                settings=self.settings,
                store=store,
                provider=MockProvider(),
                extractor=extractor,
            )
        )
        payload = {
            "schema_version": "1",
            "capture_type": "content",
            "source_type": "article_url",
            "source": "https://example.com/fictional",
            "raw_content": "",
            "requested_processing": "summary",
            "allowed_projects": [],
        }
        response = client.post("/api/v1/capture", json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        capture_id = response.json()["capture_id"]
        self.assertEqual(store.get(capture_id).raw_content, "")
        self.assertIn("Extracted Source Text", response.json()["result"]["markdown"])
        self.assertEqual(extractor.calls, [payload["source"]])

    def test_video_reference_without_transcript_stays_pending_and_is_not_fetched(self) -> None:
        extractor = FixtureExtractor()
        payload = {
            "schema_version": "1",
            "capture_type": "content",
            "source_type": "video_url",
            "source": "https://video.example/fictional",
            "raw_content": "",
            "requested_processing": "summary",
            "allowed_projects": [],
        }
        app = create_app(
            settings=self.settings,
            store=CaptureStore(Path(self.temp.name) / "video.sqlite3"),
            provider=NoCallProvider(),
            extractor=extractor,
        )
        response = TestClient(app).post(
            "/api/v1/capture", json=payload, headers=self.headers
        )
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json()["status"], "pending")
        self.assertEqual(extractor.calls, [])

    def test_invalid_and_oversized_requests_have_bounded_errors(self) -> None:
        invalid = self.client.post(
            "/api/v1/capture",
            json=dict(self.voice, unexpected=True),
            headers=self.headers,
        )
        self.assertEqual(invalid.status_code, 422)
        self.assertEqual(invalid.json()["error"]["code"], "INVALID_REQUEST")
        oversized = self.client.post(
            "/api/v1/capture",
            content=b"x" * 131_073,
            headers={**self.headers, "Content-Type": "application/json"},
        )
        self.assertEqual(oversized.status_code, 413)
        self.assertEqual(oversized.json()["error"]["code"], "PAYLOAD_TOO_LARGE")

        def chunks():
            for _ in range(129):
                yield b"x" * 1_024

        chunked = self.client.post(
            "/api/v1/capture",
            content=chunks(),
            headers=self.headers,
        )
        self.assertEqual(chunked.status_code, 413)
        self.assertEqual(chunked.json()["error"]["code"], "PAYLOAD_TOO_LARGE")

    def test_logs_exclude_raw_source_and_auth_value(self) -> None:
        logger = logging.getLogger("backend.capture")
        with self.assertLogs(logger, level="INFO") as captured:
            self.client.post("/api/v1/capture", json=self.voice, headers=self.headers)
        output = "\n".join(captured.output)
        self.assertNotIn(self.voice["raw_content"], output)
        self.assertNotIn("fictional-test-token", output)
        self.assertNotIn("Authorization", output)
        self.assertIn("processing=voice_structure", output)

    def test_provider_failure_message_cannot_echo_raw_content(self) -> None:
        client = TestClient(
            create_app(
                settings=self.settings,
                store=CaptureStore(Path(self.temp.name) / "leaky.sqlite3"),
                provider=LeakyFailureProvider(),
                extractor=FixtureExtractor(),
            )
        )
        response = client.post(
            "/api/v1/capture", json=self.voice, headers=self.headers
        )
        self.assertEqual(response.status_code, 202)
        self.assertNotIn(self.voice["raw_content"], response.text)
        self.assertEqual(
            response.json()["message"],
            "AI temporarily unavailable — capture was saved.",
        )


if __name__ == "__main__":
    unittest.main()
