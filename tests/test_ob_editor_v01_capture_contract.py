from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.config import Settings
from backend.models import CaptureRequest
from backend.models import ProviderResult
from backend.providers.base import ProviderFailure
from backend.providers.mock import MockProvider
from backend.services.capture import CaptureService
from backend.services.extraction import URLExtractor
from backend.storage.sqlite import CaptureStore


class FailureProvider:
    def __init__(self, code: str) -> None:
        self.code = code

    def process(self, request):
        return ProviderFailure(error_code=self.code, message="untrusted detail")


class OpaqueProvider:
    def process(self, request):
        return {"malformed": True}


class ObEditorV01CaptureContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "capture.sqlite3"
        settings = Settings(
            app_env="test",
            ai_provider="mock",
            database_path=self.path,
            auth_mode="dev",
            api_auth_token=None,
            allowed_origins=("http://127.0.0.1:8000",),
        )
        self.payload = {
            "schema_version": "1",
            "capture_type": "content",
            "source_type": "selected_text",
            "raw_content": "raw content must survive AI failure",
            "requested_processing": "summary",
        }
        self.settings = settings

    def client(self, provider) -> tuple[TestClient, CaptureStore]:
        store = CaptureStore(self.path)
        return TestClient(create_app(settings=self.settings, store=store, provider=provider)), store

    def test_valid_capture_returns_processed_result(self) -> None:
        client, _ = self.client(MockProvider())
        response = client.post("/api/v1/capture", json=self.payload)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "processed")
        self.assertIn("id", body)
        self.assertIn("result", body)

    def test_missing_required_input_is_rejected(self) -> None:
        client, store = self.client(MockProvider())
        response = client.post("/api/v1/capture", json={"schema_version": "1"})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"]["code"], "INVALID_REQUEST")
        self.assertEqual(store.list().total_items, 0)

    def test_ai_failure_is_failed_and_raw_content_is_recoverable(self) -> None:
        client, _ = self.client(FailureProvider("AI_UNAVAILABLE"))
        created = client.post("/api/v1/capture", json=self.payload).json()
        self.assertEqual(created["status"], "failed")
        self.assertEqual(created["error"]["code"], "AI_UNAVAILABLE")
        self.assertNotIn("result", created)

        status = client.get("/api/v1/captures/" + created["id"])
        self.assertEqual(status.status_code, 200)
        self.assertEqual(status.json()["status"], "failed")
        self.assertEqual(status.json()["raw_content"], self.payload["raw_content"])
        self.assertNotIn("result", status.json())

    def test_malformed_ai_response_is_failed(self) -> None:
        client, _ = self.client(OpaqueProvider())
        response = client.post("/api/v1/capture", json=self.payload)
        self.assertEqual(response.json()["status"], "failed")
        self.assertEqual(response.json()["error"]["code"], "INTERNAL_ERROR")

    def test_timeout_is_failed_and_raw_content_is_preserved(self) -> None:
        client, store = self.client(FailureProvider("AI_TIMEOUT"))
        response = client.post("/api/v1/capture", json=self.payload)
        capture_id = response.json()["id"]
        self.assertEqual(response.json()["status"], "failed")
        self.assertEqual(response.json()["error"]["code"], "AI_TIMEOUT")
        self.assertEqual(store.get(capture_id).raw_content, self.payload["raw_content"])

    def test_unknown_capture_id_returns_not_found(self) -> None:
        client, _ = self.client(MockProvider())
        response = client.get("/api/v1/captures/00000000-0000-4000-8000-000000000000")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "NOT_FOUND")

    def test_pending_processing_processed_transition_is_persisted(self) -> None:
        store = CaptureStore(self.path)
        service = CaptureService(
            store=store,
            provider=MockProvider(),
            extractor=URLExtractor(),
            defer_processing=True,
        )
        request = CaptureRequest.model_validate(self.payload)
        accepted = service.create(request)
        self.assertEqual(accepted.status, "pending")
        self.assertEqual(store.get(accepted.capture_id).status, "pending")
        store.mark_processing(accepted.capture_id)
        self.assertEqual(store.get(accepted.capture_id).status, "processing")
        completed = service.process_existing(accepted.capture_id)
        self.assertEqual(completed.status, "processed")
        self.assertEqual(store.get(accepted.capture_id).status, "processed")


if __name__ == "__main__":
    unittest.main()
