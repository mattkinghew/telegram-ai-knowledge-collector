from __future__ import annotations

import unittest
from uuid import UUID

from pydantic import ValidationError

from backend.models import (
    CaptureRequest,
    CaptureResponse,
    ProviderResult,
    new_capture_id,
)
from backend.services.obsidian_handoff import (
    build_obsidian_handoff,
    build_suggested_filename,
    folder_for_record_type,
    sanitize_note_title,
)


class P15BackendContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.voice = {
            "schema_version": "1",
            "capture_type": "voice",
            "source_type": "voice_transcript",
            "source": None,
            "raw_content": "完成 fictional audit，下一步測試 fallback。",
            "requested_processing": "voice_structure",
            "allowed_projects": ["Project Alpha"],
        }
        self.content = {
            "schema_version": "1",
            "capture_type": "content",
            "source_type": "selected_text",
            "source": None,
            "raw_content": "Fictional public-safe source text.",
            "requested_processing": "summary",
            "allowed_projects": [],
        }

    def test_valid_voice_and_content_requests_preserve_raw_input(self) -> None:
        voice = CaptureRequest.model_validate(self.voice)
        content = CaptureRequest.model_validate(self.content)
        self.assertEqual(voice.raw_content, self.voice["raw_content"])
        self.assertEqual(content.raw_content, self.content["raw_content"])

    def test_voice_request_defaults_optional_mobile_fields(self) -> None:
        payload = dict(self.voice)
        payload.pop("source")
        payload.pop("allowed_projects")

        request = CaptureRequest.model_validate(payload)

        self.assertIsNone(request.source)
        self.assertEqual(request.allowed_projects, [])

    def test_explicit_optional_mobile_defaults_remain_compatible(self) -> None:
        payload = dict(self.voice, source=None, allowed_projects=[])

        request = CaptureRequest.model_validate(payload)

        self.assertIsNone(request.source)
        self.assertEqual(request.allowed_projects, [])

    def test_cleaned_transcript_uses_existing_backend_contract(self) -> None:
        payload = dict(self.voice, raw_content="完成 fictional CSV mapping。下一步測試 fallback。")

        request = CaptureRequest.model_validate(payload)

        self.assertEqual(request.raw_content, payload["raw_content"])
        self.assertEqual(request.requested_processing, "voice_structure")

    def test_record_type_defaults_to_free_and_allowlist_is_strict(self) -> None:
        request = CaptureRequest.model_validate(self.voice)
        self.assertEqual(request.record_type, "free")
        for record_type in ("daily_control", "work_log", "reflection", "todo", "meeting_followup"):
            self.assertEqual(
                CaptureRequest.model_validate(dict(self.voice, record_type=record_type)).record_type,
                record_type,
            )
        with self.assertRaises(ValidationError):
            CaptureRequest.model_validate(dict(self.voice, record_type="unknown"))

    def test_local_assist_metadata_stays_client_side(self) -> None:
        payload = dict(
            self.voice,
            raw_content="Clean fictional transcript.",
            record_type="daily_control",
            ai_status="local_suggested",
        )

        with self.assertRaises(ValidationError):
            CaptureRequest.model_validate(payload)

    def test_unknown_missing_and_nested_fields_are_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            CaptureRequest.model_validate(dict(self.content, unexpected=True))
        missing = dict(self.content)
        missing.pop("capture_type")
        with self.assertRaises(ValidationError):
            CaptureRequest.model_validate(missing)
        with self.assertRaises(ValidationError):
            CaptureRequest.model_validate(dict(self.content, raw_content={"text": "x"}))

    def test_capture_source_and_processing_must_be_compatible(self) -> None:
        with self.assertRaises(ValidationError):
            CaptureRequest.model_validate(
                dict(self.voice, source_type="selected_text")
            )
        with self.assertRaises(ValidationError):
            CaptureRequest.model_validate(
                dict(self.content, requested_processing="voice_structure")
            )

    def test_reference_sources_require_safe_values(self) -> None:
        url_capture = dict(
            self.content,
            source_type="article_url",
            source="https://example.com/fictional",
            raw_content="",
        )
        self.assertEqual(
            CaptureRequest.model_validate(url_capture).source,
            url_capture["source"],
        )
        for source in (
            "file:///etc/passwd",
            "ftp://example.com/a",
            "https://user:pass@example.com/a",
            "/Users/example/private.md",
            "../private.md",
        ):
            with self.subTest(source=source), self.assertRaises(ValidationError):
                CaptureRequest.model_validate(dict(url_capture, source=source))

    def test_text_and_voice_require_content_but_url_reference_may_be_empty(self) -> None:
        with self.assertRaises(ValidationError):
            CaptureRequest.model_validate(dict(self.content, raw_content=""))
        with self.assertRaises(ValidationError):
            CaptureRequest.model_validate(dict(self.voice, raw_content=" "))
        CaptureRequest.model_validate(
            dict(
                self.content,
                source_type="video_url",
                source="https://video.example/fictional",
                raw_content="",
            )
        )

    def test_lengths_and_project_allowlist_are_bounded(self) -> None:
        with self.assertRaises(ValidationError):
            CaptureRequest.model_validate(
                dict(self.content, raw_content="x" * 50_001)
            )
        with self.assertRaises(ValidationError):
            CaptureRequest.model_validate(
                dict(self.content, allowed_projects=["P"] * 9)
            )
        with self.assertRaises(ValidationError):
            CaptureRequest.model_validate(
                dict(self.content, allowed_projects=["Project Alpha", "Project Alpha"])
            )

    def test_provider_result_is_strict_and_mode_specific(self) -> None:
        result = ProviderResult.model_validate(
            {
                "processing_mode": "summary",
                "title": "Fictional source",
                "summary": "A bounded fictional summary.",
                "points": ["Raw evidence remains separate."],
                "why_it_matters": "It demonstrates the contract.",
                "sections": {},
            }
        )
        self.assertEqual(result.processing_mode, "summary")
        with self.assertRaises(ValidationError):
            ProviderResult.model_validate(
                dict(result.model_dump(), unexpected="not allowed")
            )
        with self.assertRaises(ValidationError):
            ProviderResult.model_validate(
                dict(result.model_dump(), points=["x"] * 4)
            )
        with self.assertRaises(ValidationError):
            ProviderResult.model_validate(
                dict(result.model_dump(), sections={"unexpected": ["x"]})
            )
        with self.assertRaises(ValidationError):
            ProviderResult.model_validate(
                dict(
                    result.model_dump(),
                    processing_mode="voice_structure",
                    sections={},
                )
            )
        with self.assertRaises(ValidationError):
            ProviderResult.model_validate(
                dict(
                    result.model_dump(),
                    processing_mode="short_article",
                    sections={"draft": ["Safe line\n## Injected heading"]},
                )
            )

    def test_capture_ids_are_opaque_uuids(self) -> None:
        first = new_capture_id()
        second = new_capture_id()
        self.assertNotEqual(first, second)
        self.assertEqual(str(UUID(first)), first)
        self.assertNotIn("fictional", first)

    def test_success_and_pending_responses_have_stable_shape(self) -> None:
        success = CaptureResponse(
            ok=True,
            capture_id=new_capture_id(),
            status="processed",
            result={"markdown": "# Fictional"},
            error_code=None,
            message=None,
        )
        pending = CaptureResponse(
            ok=False,
            capture_id=new_capture_id(),
            status="pending",
            result=None,
            error_code="AI_UNAVAILABLE",
            message="AI temporarily unavailable — capture was saved.",
        )
        self.assertTrue(success.ok)
        self.assertEqual(pending.error_code, "AI_UNAVAILABLE")

    def test_obsidian_handoff_sanitizes_cjk_and_path_traversal(self) -> None:
        title = "  每日/控制台: 測試..  "
        sanitized = sanitize_note_title(title)
        self.assertEqual(sanitized, "每日-控制台-測試")
        filename = build_suggested_filename("2026-09-03", title)
        self.assertEqual(filename, "2026-09-03-每日-控制台-測試.md")
        self.assertNotIn("/", filename)
        self.assertNotIn("..", filename)

    def test_obsidian_handoff_duplicate_suffix_is_deterministic(self) -> None:
        self.assertEqual(
            build_suggested_filename(
                "2026-09-03", "Fictional note", existing_names={"2026-09-03-Fictional note.md"}
            ),
            "2026-09-03-Fictional note-2.md",
        )

    def test_obsidian_folder_mapping_is_logical_only(self) -> None:
        self.assertEqual(folder_for_record_type("daily_control"), "Daily")
        self.assertEqual(folder_for_record_type("free"), "Inbox")

    def test_obsidian_handoff_is_logical_and_contains_no_vault_path(self) -> None:
        handoff = build_obsidian_handoff(
            markdown="# Fictional",
            suggested_date="2026-09-03",
            record_type="daily_control",
            title="每日控制台",
        )
        self.assertEqual(handoff["folder_key"], "daily_control")
        self.assertEqual(handoff["suggested_filename"], "2026-09-03-每日控制台.md")
        self.assertEqual(handoff["markdown"], "# Fictional")
        self.assertFalse(any("/Users/" in str(value) for value in handoff.values()))


if __name__ == "__main__":
    unittest.main()
