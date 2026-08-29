from __future__ import annotations

import copy
import unittest
from pathlib import Path

from tools.two_entry_capture_reference import (
    TwoEntryCaptureError,
    build_content_capture,
    build_voice_flash,
    classify_content_source,
    validate_content_capture,
    validate_content_suggestion,
)


ROOT = Path(__file__).parent.parent


class TwoEntryCaptureP14Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.content = {
            "schema_version": "1",
            "created": "2026-08-20T10:30:00+08:00",
            "input_kind": "shared_text",
            "source": "",
            "raw_content": "Fictional shared text with 中文、emoji 🧭 and **Markdown**.",
            "requested_processing": "summary",
        }
        self.suggestion = {
            "processing_mode": "summary",
            "suggested_title": "Fictional travel note",
            "thirty_second_summary": "A fictional workflow can keep capture reviewable.",
            "core_points": [
                "Raw evidence remains separate from suggestions.",
                "The user can save without AI.",
            ],
            "why_worth_saving": "It documents a bounded mobile workflow.",
            "immediate_uses": ["Review the fictional acceptance case."],
            "convertible_material": ["Short internal note"],
            "facts_to_verify": ["Confirm the result on a real device."],
            "recommendation": None,
            "short_article_draft": None,
        }
        self.voice = {
            "schema_version": "1",
            "captured_at": "2026-08-20T10:30:00+08:00",
            "source_type": "voice_transcript",
            "raw_transcript": "完成咗 fictional review，下一步測試 offline fallback。",
            "allowed_projects": ["Project Alpha"],
        }

    def test_voice_flash_reuses_p1_3_and_preserves_pending_transcript(self) -> None:
        result = build_voice_flash(self.voice)
        self.assertEqual(result["ai_status"], "pending")
        self.assertEqual(result["notification"], "✓ 已保存，待稍後整理")
        self.assertIn(self.voice["raw_transcript"], result["markdown"])
        self.assertIn("ai_status: pending", result["markdown"])

    def test_voice_flash_structured_path_preserves_original_transcript(self) -> None:
        structured = {
            "suggested_title": "Fictional voice note",
            "capture_type": "mixed",
            "one_sentence_summary": "A fictional review needs an offline test.",
            "completed": ["Completed the fictional review"],
            "in_progress": [],
            "next_actions": ["Test the offline fallback"],
            "blockers": [],
            "decisions": [],
            "knowledge": [],
            "content_ideas": [],
            "project_updates": [],
            "facts_to_verify": [],
            "related_projects": ["Project Alpha"],
            "confidence": "medium",
        }
        result = build_voice_flash(self.voice, structured)
        self.assertEqual(result["ai_status"], "suggested")
        self.assertEqual(result["notification"], "✓ 已整理並保存")
        self.assertIn(self.voice["raw_transcript"], result["markdown"])

    def test_url_classification_is_deterministic_and_requires_no_manual_category(self) -> None:
        cases = {
            "https://example.com/article?q=a%20b#part": "article_url",
            "https://x.com/example/status/123": "social_post",
            "https://www.youtube.com/watch?v=fictional": "video_url",
        }
        for source, expected in cases.items():
            with self.subTest(source=source):
                self.assertEqual(classify_content_source("url", source), expected)

    def test_shared_selected_and_clipboard_text_are_classified_without_questions(self) -> None:
        self.assertEqual(classify_content_source("shared_text", ""), "selected_text")
        self.assertEqual(classify_content_source("selected_text", ""), "selected_text")
        self.assertEqual(classify_content_source("clipboard", ""), "clipboard_text")
        with self.assertRaises(TwoEntryCaptureError):
            classify_content_source([], "")  # type: ignore[arg-type]
        with self.assertRaises(TwoEntryCaptureError):
            classify_content_source("url", None)  # type: ignore[arg-type]

    def test_url_only_processing_is_pending_and_never_claims_summary(self) -> None:
        capture = dict(
            self.content,
            input_kind="url",
            source="https://example.com/article?q=a%20b#part",
            raw_content="",
        )
        result = build_content_capture(capture)
        self.assertEqual(result["source_type"], "article_url")
        self.assertEqual(result["ai_status"], "pending")
        self.assertEqual(result["notification"], "✓ 已保存，待稍後整理")
        self.assertIn(capture["source"], result["markdown"])
        self.assertNotIn("## 30 秒摘要", result["markdown"])

    def test_shared_text_summary_keeps_source_and_suggestion_layers_separate(self) -> None:
        original = copy.deepcopy(self.content)
        result = build_content_capture(self.content, self.suggestion)
        self.assertEqual(result["ai_status"], "suggested")
        self.assertEqual(result["notification"], "✓ 已整理並保存")
        self.assertIn("## 30 秒摘要", result["markdown"])
        self.assertIn("## 原始內容", result["markdown"])
        self.assertIn(self.content["raw_content"], result["markdown"])
        self.assertIn("以下內容是未確認建議", result["markdown"])
        self.assertEqual(self.content, original)

    def test_selected_text_and_video_takeaway_are_preserved(self) -> None:
        selected = dict(self.content, input_kind="selected_text")
        video = dict(
            self.content,
            input_kind="url",
            source="https://youtu.be/fictional",
            raw_content="User takeaway only; no transcript was supplied.",
        )
        self.assertIn(selected["raw_content"], build_content_capture(selected)["markdown"])
        rendered = build_content_capture(video)["markdown"]
        self.assertIn(video["source"], rendered)
        self.assertIn(video["raw_content"], rendered)
        self.assertNotIn("transcript available", rendered.lower())

    def test_image_and_file_references_reject_paths_and_preserve_safe_names(self) -> None:
        for input_kind, filename in (
            ("image", "fictional-screenshot.png"),
            ("file", "fictional-brief.pdf"),
        ):
            with self.subTest(input_kind=input_kind):
                capture = dict(
                    self.content,
                    input_kind=input_kind,
                    source=filename,
                    raw_content="",
                    requested_processing="raw_save",
                )
                result = build_content_capture(capture)
                self.assertIn(filename, result["markdown"])
                with self.assertRaises(TwoEntryCaptureError):
                    validate_content_capture(dict(capture, source="folder/" + filename))

    def test_raw_save_never_calls_or_claims_ai(self) -> None:
        capture = dict(self.content, requested_processing="raw_save")
        result = build_content_capture(capture)
        self.assertEqual(result["ai_status"], "none")
        self.assertEqual(result["notification"], "✓ 已保存")
        self.assertIn("ai_status: none", result["markdown"])
        self.assertNotIn("## AI 整理建議", result["markdown"])
        with self.assertRaises(TwoEntryCaptureError):
            build_content_capture(capture, self.suggestion)

    def test_offline_pending_record_contains_every_retry_input_without_retrying(self) -> None:
        result = build_content_capture(self.content)
        for value in (
            "source_type: selected_text",
            "requested_processing: summary",
            'created: "' + self.content["created"] + '"',
            self.content["raw_content"],
        ):
            self.assertIn(value, result["markdown"])
        self.assertNotIn("retry", result["markdown"].lower())

    def test_short_article_and_recommendation_modes_are_explicit_and_bounded(self) -> None:
        article = dict(
            self.suggestion,
            processing_mode="short_article",
            short_article_draft="AI draft\n" + "這是一段虛構內容，用來驗證短文章草稿只會在明確選擇後出現。" * 6,
        )
        article_capture = dict(self.content, requested_processing="short_article")
        article_result = build_content_capture(article_capture, article)
        self.assertIn("## AI 草稿", article_result["markdown"])

        recommendation = dict(
            self.suggestion,
            processing_mode="recommendation",
            recommendation="Review the evidence before using the fictional workflow.",
        )
        recommendation_capture = dict(self.content, requested_processing="recommendation")
        recommendation_result = build_content_capture(
            recommendation_capture, recommendation
        )
        self.assertIn("## 深入建議", recommendation_result["markdown"])

    def test_invalid_or_mismatched_suggestions_fail_without_data_loss(self) -> None:
        with self.assertRaises(TwoEntryCaptureError):
            validate_content_suggestion(
                dict(self.suggestion, processing_mode="short_article")
            )
        with self.assertRaises(TwoEntryCaptureError):
            build_content_capture(
                self.content,
                dict(self.suggestion, processing_mode="recommendation"),
            )
        fallback = build_content_capture(self.content)
        self.assertIn(self.content["raw_content"], fallback["markdown"])

    def test_contract_is_strict_and_rejects_empty_text_or_unknown_fields(self) -> None:
        with self.assertRaises(TwoEntryCaptureError):
            validate_content_capture(dict(self.content, raw_content=""))
        with self.assertRaises(TwoEntryCaptureError):
            validate_content_capture(dict(self.content, extra="not allowed"))

    def test_required_p1_4_docs_exist_and_legacy_build_sheets_remain(self) -> None:
        required = (
            "docs/P1_4_SIMPLIFIED_MOBILE_PRODUCT_DECISION.md",
            "docs/SHORTCUT_BUILD_SHEET_VOICE_FLASH_V2.md",
            "docs/SHORTCUT_BUILD_SHEET_CONTENT_CAPTURE_V2.md",
            "docs/P1_4_OFFLINE_BEHAVIOR.md",
            "docs/PENDING_ENRICHMENT_CONTRACT_V1.md",
            "docs/P1_4_TWO_SHORTCUT_DEVICE_ACCEPTANCE.md",
            "docs/SHORTCUT_BUILD_SHEET_KNOWLEDGE_CAPTURE.md",
            "docs/SHORTCUT_BUILD_SHEET_PROJECT_UPDATE.md",
            "docs/SHORTCUT_BUILD_SHEET_VOICE_CAPTURE.md",
        )
        for relative in required:
            with self.subTest(relative=relative):
                self.assertTrue((ROOT / relative).is_file())
        product = (ROOT / required[0]).read_text(encoding="utf-8")
        self.assertIn("語音閃念", product)
        self.assertIn("收集內容", product)
        self.assertIn("fallback / reference / legacy-compatible", product.casefold())


if __name__ == "__main__":
    unittest.main()
