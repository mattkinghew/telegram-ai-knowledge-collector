from __future__ import annotations

import socket
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.config import Settings
from backend.providers.base import ProviderFailure
from backend.providers.mock import MockProvider
from backend.services.extraction import FetchResponse, URLExtractor
from backend.storage.sqlite import CaptureStore


ROOT = Path(__file__).parent.parent
PUBLIC_IP = "93.184.216.34"


def public_resolver(host: str, port: int, *, type: int):
    del port, type
    if host != "example.com":
        raise socket.gaierror("fictional unresolved host")
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (PUBLIC_IP, 443))]


class FixtureTransport:
    def __init__(self, body: bytes) -> None:
        self.body = body
        self.calls: list[str] = []

    def get(self, url: str, *, limits):
        del limits
        self.calls.append(url)
        return FetchResponse(
            200,
            {"content-type": "text/html; charset=utf-8"},
            self.body,
        )


class FailingProvider:
    def __init__(self, error_code: str) -> None:
        self.error_code = error_code

    def process(self, request):
        return ProviderFailure(
            error_code=self.error_code,
            message="untrusted provider message: " + request.raw_content,
        )


class P15EndToEndTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.headers = {"Authorization": "Bearer fictional-test-token"}

    def make_client(self, *, provider, extractor=None):
        path = Path(self.temp.name) / (str(id(provider)) + ".sqlite3")
        store = CaptureStore(path)
        settings = Settings(
            app_env="test",
            ai_provider="mock",
            database_path=path,
            auth_mode="token",
            api_auth_token="fictional-test-token",
            allowed_origins=("http://127.0.0.1:8000",),
        )
        client = TestClient(
            create_app(
                settings=settings,
                store=store,
                provider=provider,
                extractor=extractor,
            )
        )
        return client, store

    def test_article_fixture_flows_through_extraction_ai_storage_markdown_and_inbox(self) -> None:
        body = (ROOT / "samples" / "p1_5_article_fixture.html").read_bytes()
        transport = FixtureTransport(body)
        extractor = URLExtractor(resolver=public_resolver, transport=transport)
        client, store = self.make_client(provider=MockProvider(), extractor=extractor)
        payload = {
            "schema_version": "1",
            "capture_type": "content",
            "source_type": "article_url",
            "source": "https://example.com/fixture",
            "raw_content": "",
            "requested_processing": "summary",
            "allowed_projects": ["Fictional Project"],
        }

        response = client.post("/api/v1/capture", json=payload, headers=self.headers)

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["status"], "processed")
        self.assertEqual(transport.calls, [payload["source"]])
        self.assertIn("Fictional Capture Workflow", result["result"]["markdown"])
        self.assertIn("Unconfirmed AI Suggestions", result["result"]["markdown"])
        self.assertEqual(
            result["result"]["provider_result"]["processing_mode"], "summary"
        )

        record = store.get(result["capture_id"])
        self.assertEqual(record.raw_content, "")
        self.assertEqual(record.source, payload["source"])
        self.assertEqual(record.status, "processed")

        inbox = client.get(
            "/api/v1/captures?page=1&page_size=20&status=processed",
            headers=self.headers,
        )
        self.assertEqual(inbox.status_code, 200)
        self.assertEqual(inbox.json()["data"][0]["capture_id"], result["capture_id"])

    def test_provider_failures_preserve_original_capture_without_leaking_raw_text(self) -> None:
        raw_content = "fictional private transcript marker"
        for error_code in (
            "NETWORK_UNAVAILABLE",
            "AI_UNAVAILABLE",
            "AI_TIMEOUT",
            "INVALID_AI_JSON",
            "SCHEMA_MISMATCH",
            "PAYLOAD_TOO_LARGE",
            "INVALID_REQUEST",
        ):
            with self.subTest(error_code=error_code):
                client, store = self.make_client(provider=FailingProvider(error_code))
                response = client.post(
                    "/api/v1/capture",
                    json={
                        "schema_version": "1",
                        "capture_type": "voice",
                        "source_type": "voice_transcript",
                        "source": None,
                        "raw_content": raw_content,
                        "requested_processing": "voice_structure",
                        "allowed_projects": [],
                    },
                    headers=self.headers,
                )
                self.assertEqual(response.status_code, 202)
                payload = response.json()
                self.assertEqual(payload["error_code"], error_code)
                self.assertNotIn(raw_content, payload["message"])
                record = store.get(payload["capture_id"])
                self.assertEqual(record.raw_content, raw_content)
                self.assertEqual(record.requested_processing, "voice_structure")
                self.assertEqual(record.status, "pending")


if __name__ == "__main__":
    unittest.main()
