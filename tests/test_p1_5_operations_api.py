from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.config import Settings
from backend.providers.base import ProviderFailure
from backend.providers.mock import MockProvider
from backend.services.extraction import ExtractedArticle
from backend.storage.sqlite import CaptureStore


class PendingProvider:
    def process(self, request):
        del request
        return ProviderFailure(
            error_code="AI_UNAVAILABLE",
            message="AI temporarily unavailable — capture was saved.",
        )


class NoNetworkExtractor:
    def extract(self, url: str) -> ExtractedArticle:
        raise AssertionError("unexpected URL fetch: " + url)


class P15OperationsAPITests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db_path = Path(self.temp.name) / "operations.sqlite3"
        self.settings = Settings(
            app_env="test",
            ai_provider="mock",
            database_path=self.db_path,
            auth_mode="token",
            api_auth_token="fictional-test-token",
            allowed_origins=("http://127.0.0.1:8000",),
        )
        self.store = CaptureStore(self.db_path)
        self.headers = {"Authorization": "Bearer fictional-test-token"}

    def _client(self, provider=None) -> TestClient:
        return TestClient(
            create_app(
                settings=self.settings,
                store=self.store,
                provider=provider or MockProvider(),
                extractor=NoNetworkExtractor(),
            )
        )

    def _create(self, client: TestClient, *, text="Fictional project update.") -> str:
        response = client.post(
            "/api/v1/capture",
            json={
                "schema_version": "1",
                "capture_type": "content",
                "source_type": "selected_text",
                "source": None,
                "raw_content": text,
                "requested_processing": "project_knowledge",
                "allowed_projects": ["Project Alpha", "Project Beta"],
            },
            headers=self.headers,
        )
        return response.json()["capture_id"]

    def test_review_and_project_assignment_are_allowlisted(self) -> None:
        client = self._client()
        capture_id = self._create(client)
        updated = client.patch(
            "/api/v1/captures/" + capture_id,
            json={"reviewed": True, "assigned_project": "Project Alpha"},
            headers=self.headers,
        )
        self.assertEqual(updated.status_code, 200)
        self.assertTrue(updated.json()["reviewed"])
        self.assertEqual(updated.json()["assigned_project"], "Project Alpha")
        rejected = client.patch(
            "/api/v1/captures/" + capture_id,
            json={"reviewed": True, "assigned_project": "Secret Project"},
            headers=self.headers,
        )
        self.assertEqual(rejected.status_code, 422)

    def test_dismiss_processing_keeps_pending_raw_capture(self) -> None:
        client = self._client(PendingProvider())
        capture_id = self._create(client, text="Fictional pending source.")
        dismissed = client.post(
            "/api/v1/captures/" + capture_id + "/dismiss",
            headers=self.headers,
        )
        self.assertEqual(dismissed.status_code, 200)
        stored = self.store.get(capture_id)
        self.assertTrue(stored.processing_dismissed)
        self.assertEqual(stored.raw_content, "Fictional pending source.")

    def test_filters_cover_project_date_title_and_source(self) -> None:
        client = self._client()
        capture_id = self._create(client, text="Fictional searchable evidence.")
        client.patch(
            "/api/v1/captures/" + capture_id,
            json={"reviewed": True, "assigned_project": "Project Alpha"},
            headers=self.headers,
        )
        for query in (
            "project=Project%20Alpha",
            "query=Fictional%20capture",
            "created_from=2020-01-01&created_to=2099-12-31",
            "source_type=selected_text&requested_processing=project_knowledge",
        ):
            with self.subTest(query=query):
                response = client.get(
                    "/api/v1/captures?" + query,
                    headers=self.headers,
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["pagination"]["total_items"], 1)
        for query in (
            "status=unknown",
            "capture_type=audio",
            "source_type=filesystem",
            "requested_processing=agent",
            "created_from=2026-99-99",
        ):
            with self.subTest(invalid=query):
                response = client.get(
                    "/api/v1/captures?" + query,
                    headers=self.headers,
                )
                self.assertEqual(response.status_code, 422)

    def test_today_page_data_is_bounded_and_has_operational_counts(self) -> None:
        client = self._client(PendingProvider())
        self._create(client)
        result = client.get("/api/v1/dashboard/today", headers=self.headers)
        self.assertEqual(result.status_code, 200)
        body = result.json()
        self.assertEqual(body["pending_count"], 1)
        self.assertEqual(body["failed_count"], 0)
        self.assertLessEqual(len(body["recent_captures"]), 5)

    def test_projects_return_only_assigned_project_summaries(self) -> None:
        client = self._client()
        capture_id = self._create(client)
        client.patch(
            "/api/v1/captures/" + capture_id,
            json={"reviewed": False, "assigned_project": "Project Alpha"},
            headers=self.headers,
        )
        response = client.get("/api/v1/projects", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"][0]["project"], "Project Alpha")
        self.assertIn("latest_progress", response.json()["data"][0])
        self.assertIn("next_action", response.json()["data"][0])

    def test_daily_report_requires_human_selection_and_only_previews(self) -> None:
        client = self._client()
        capture_id = self._create(client)
        empty = client.post(
            "/api/v1/reports/preview",
            json={"report_type": "daily", "period": "2026-08-30", "capture_ids": []},
            headers=self.headers,
        )
        self.assertEqual(empty.status_code, 422)
        preview = client.post(
            "/api/v1/reports/preview",
            json={
                "report_type": "daily",
                "period": "2026-08-30",
                "capture_ids": [capture_id],
            },
            headers=self.headers,
        )
        self.assertEqual(preview.status_code, 200)
        self.assertIn("# Daily Progress Report", preview.json()["markdown"])
        self.assertIn(capture_id, preview.json()["selected_capture_ids"])
        self.assertFalse(preview.json()["sent"])
        self.assertFalse(preview.json()["published"])

    def test_period_report_rejects_duplicate_or_unknown_capture_ids(self) -> None:
        client = self._client()
        capture_id = self._create(client)
        duplicate = client.post(
            "/api/v1/reports/preview",
            json={
                "report_type": "period",
                "period": "2026-08-01 to 2026-08-30",
                "capture_ids": [capture_id, capture_id],
            },
            headers=self.headers,
        )
        self.assertEqual(duplicate.status_code, 422)
        missing = client.post(
            "/api/v1/reports/preview",
            json={
                "report_type": "period",
                "period": "2026-08",
                "capture_ids": ["00000000-0000-4000-8000-000000000000"],
            },
            headers=self.headers,
        )
        self.assertEqual(missing.status_code, 404)

    def test_operations_require_auth_and_do_not_offer_delete(self) -> None:
        client = self._client()
        self.assertEqual(client.get("/api/v1/projects").status_code, 401)
        self.assertEqual(client.get("/api/v1/dashboard/today").status_code, 401)
        capture_id = self._create(client)
        self.assertEqual(
            client.delete(
                "/api/v1/captures/" + capture_id,
                headers=self.headers,
            ).status_code,
            405,
        )


if __name__ == "__main__":
    unittest.main()
