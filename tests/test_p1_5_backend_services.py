from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.models import CaptureRequest
from backend.providers.gemini import GeminiConfigurationError, GeminiProvider
from backend.providers.mock import MockProvider
from backend.services.markdown import build_capture_markdown
from backend.storage.sqlite import CaptureStore, RetryLimitError


class P15BackendServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = CaptureStore(Path(self.temp.name) / "captures.sqlite3")
        self.request = CaptureRequest.model_validate(
            {
                "schema_version": "1",
                "capture_type": "voice",
                "source_type": "voice_transcript",
                "source": None,
                "raw_content": "完成 fictional review，下一步測試 retry。",
                "requested_processing": "voice_structure",
                "allowed_projects": ["Project Alpha"],
            }
        )

    def test_store_preserves_raw_input_through_processed_transition(self) -> None:
        record = self.store.create(self.request)
        self.assertEqual(record.status, "pending")
        self.store.mark_processing(record.capture_id)
        result = MockProvider().process(self.request)
        self.store.mark_processed(record.capture_id, result, "# Fictional")
        stored = self.store.get(record.capture_id)
        self.assertEqual(stored.status, "processed")
        self.assertEqual(stored.raw_content, self.request.raw_content)
        self.assertEqual(stored.result, result.model_dump())

    def test_failure_records_reason_without_overwriting_source(self) -> None:
        record = self.store.create(self.request)
        self.store.mark_failure(
            record.capture_id,
            status="pending",
            error_code="AI_UNAVAILABLE",
            message="AI temporarily unavailable — capture was saved.",
        )
        stored = self.store.get(record.capture_id)
        self.assertEqual(stored.error_code, "AI_UNAVAILABLE")
        self.assertEqual(stored.raw_content, self.request.raw_content)
        self.assertIsNone(stored.result)

    def test_retry_is_manual_bounded_and_keeps_raw_capture(self) -> None:
        record = self.store.create(self.request)
        for expected in (1, 2):
            retried = self.store.begin_retry(record.capture_id)
            self.assertEqual(retried.retry_count, expected)
            self.store.mark_failure(
                record.capture_id,
                status="failed",
                error_code="AI_TIMEOUT",
                message="Processing timed out — capture was saved.",
            )
        with self.assertRaises(RetryLimitError):
            self.store.begin_retry(record.capture_id)
        self.assertEqual(self.store.get(record.capture_id).raw_content, self.request.raw_content)

    def test_list_is_paginated_filtered_and_stable(self) -> None:
        first = self.store.create(self.request)
        second_request = self.request.model_copy(
            update={"capture_type": "content", "source_type": "selected_text", "requested_processing": "summary"}
        )
        second = self.store.create(second_request)
        page = self.store.list(page=1, page_size=1, capture_type="content")
        self.assertEqual(page.total_items, 1)
        self.assertEqual(page.items[0].capture_id, second.capture_id)
        self.assertNotEqual(first.capture_id, second.capture_id)

    def test_review_project_and_dismiss_do_not_change_raw_input(self) -> None:
        record = self.store.create(self.request)
        self.store.update_review(
            record.capture_id,
            reviewed=True,
            assigned_project="Project Alpha",
        )
        self.store.dismiss_processing(record.capture_id)
        stored = self.store.get(record.capture_id)
        self.assertTrue(stored.reviewed)
        self.assertTrue(stored.processing_dismissed)
        self.assertEqual(stored.assigned_project, "Project Alpha")
        self.assertEqual(stored.raw_content, self.request.raw_content)

    def test_mock_provider_returns_every_voice_contract_section(self) -> None:
        result = MockProvider().process(self.request)
        expected = {
            "completed",
            "in_progress",
            "next_actions",
            "blockers",
            "decisions",
            "knowledge",
            "content_ideas",
            "facts_to_verify",
            "related_projects",
        }
        self.assertEqual(set(result.sections), expected)
        self.assertEqual(result.processing_mode, "voice_structure")

    def test_mock_provider_supports_all_non_raw_modes(self) -> None:
        for mode in (
            "summary",
            "recommendation",
            "short_article",
            "project_knowledge",
        ):
            with self.subTest(mode=mode):
                request = self.request.model_copy(
                    update={
                        "capture_type": "content",
                        "source_type": "selected_text",
                        "requested_processing": mode,
                    }
                )
                result = MockProvider().process(request)
                self.assertEqual(result.processing_mode, mode)
                self.assertLessEqual(len(result.points), 3)

    def test_gemini_provider_fails_closed_without_credentials(self) -> None:
        with self.assertRaises(GeminiConfigurationError):
            GeminiProvider(api_key=None, model="gemini-3.6-flash")

    def test_markdown_separates_source_raw_and_unconfirmed_ai(self) -> None:
        result = MockProvider().process(self.request)
        markdown = build_capture_markdown(self.request, result)
        self.assertIn("## Original Source", markdown)
        self.assertIn(self.request.raw_content, markdown)
        self.assertIn("## Unconfirmed AI Suggestions", markdown)
        self.assertIn("ai_status: suggested", markdown)

    def test_pending_markdown_preserves_url_without_claiming_summary(self) -> None:
        request = CaptureRequest.model_validate(
            {
                "schema_version": "1",
                "capture_type": "content",
                "source_type": "article_url",
                "source": "https://example.com/fictional",
                "raw_content": "",
                "requested_processing": "summary",
                "allowed_projects": [],
            }
        )
        markdown = build_capture_markdown(request, None)
        self.assertIn(request.source, markdown)
        self.assertIn("ai_status: pending", markdown)
        self.assertNotIn("Unconfirmed AI Suggestions", markdown)
        self.assertNotIn("summary completed", markdown.casefold())


if __name__ == "__main__":
    unittest.main()
