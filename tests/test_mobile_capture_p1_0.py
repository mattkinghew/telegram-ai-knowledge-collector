from __future__ import annotations

import json
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from tools.mobile_capture_reference import (
    MobileCaptureValidationError,
    build_mobile_filename,
    build_obsidian_uri,
    normalize_capture_input,
    render_mobile_markdown,
)


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "mobile_capture_p1_0"


class MobileCaptureP10Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.capture = {
            "schema_version": "1",
            "captured_at": "2026-08-13T00:45:30+08:00",
            "source_type": "personal",
            "source": "",
            "raw_content": "原始內容 & #100%? = yes / no : ✅",
            "insight": "AI 系統的人工覆核應該屬於正式工作流程",
            "context": "用於 fictional workflow review。",
            "action": "建立一個離線測試。",
            "project": "",
        }

    def test_typed_capture_uses_insight_as_h1(self) -> None:
        markdown = render_mobile_markdown(self.capture)
        self.assertIn(
            "# AI 系統的人工覆核應該屬於正式工作流程\n",
            markdown,
        )
        self.assertNotIn("# Quick Capture", markdown)

    def test_voice_transcript_capture_is_supported(self) -> None:
        normalized = normalize_capture_input(
            dict(self.capture, source_type="voice_transcript")
        )
        self.assertEqual(normalized["source_type"], "voice_transcript")

    def test_clipboard_capture_is_supported(self) -> None:
        normalized = normalize_capture_input(dict(self.capture, source_type="clipboard"))
        self.assertEqual(normalized["source_type"], "clipboard")

    def test_context_and_action_may_both_be_empty(self) -> None:
        capture = dict(self.capture, context="", action="")
        markdown = render_mobile_markdown(capture)
        self.assertIn("## 可以幫我處理\n\n## 下一步\n\n", markdown)

    def test_output_goal_defaults_to_collect(self) -> None:
        normalized = normalize_capture_input(self.capture)
        self.assertEqual(normalized["output_goal"], "collect")
        self.assertIn("output_goal: collect", render_mobile_markdown(self.capture))

    def test_quick_save_has_no_ai_section_and_uses_none_status(self) -> None:
        markdown = render_mobile_markdown(self.capture)
        self.assertIn("ai_status: none", markdown)
        self.assertNotIn("## AI 整理建議", markdown)

    def test_multiline_raw_content_is_preserved_after_newline_normalization(self) -> None:
        capture = dict(self.capture, raw_content="第一行\r\n第二行\r第三行")
        markdown = render_mobile_markdown(capture)
        self.assertIn("第一行\n第二行\n第三行", markdown)

    def test_emoji_and_markdown_characters_are_preserved(self) -> None:
        raw = "## 不是標題轉換\n- [ ] 保留 `code` & 100% ✅"
        markdown = render_mobile_markdown(dict(self.capture, raw_content=raw))
        self.assertIn(raw, markdown)

    def test_uri_reserved_characters_decode_to_exact_markdown(self) -> None:
        markdown = render_mobile_markdown(self.capture)
        file_path = build_mobile_filename(
            self.capture["captured_at"], unique_suffix="4821"
        )
        uri = build_obsidian_uri("EXAMPLE_VAULT_ID", file_path, markdown)
        params = parse_qs(urlparse(uri).query, strict_parsing=True)
        self.assertEqual(params["content"], [markdown])

    def test_same_second_with_different_suffixes_has_different_paths(self) -> None:
        first = build_mobile_filename(
            self.capture["captured_at"], unique_suffix="4821"
        )
        second = build_mobile_filename(
            self.capture["captured_at"], unique_suffix="7394"
        )
        self.assertEqual(first, "00_Inbox/2026-08-13-004530-4821")
        self.assertEqual(second, "00_Inbox/2026-08-13-004530-7394")
        self.assertNotEqual(first, second)

    def test_invalid_filename_suffix_is_rejected(self) -> None:
        for suffix in ("", "123", "12345", "12a4", 4821):
            with self.subTest(suffix=suffix), self.assertRaises(
                MobileCaptureValidationError
            ):
                build_mobile_filename(
                    self.capture["captured_at"], unique_suffix=suffix
                )

    def test_empty_raw_content_is_rejected(self) -> None:
        with self.assertRaisesRegex(MobileCaptureValidationError, "raw_content"):
            normalize_capture_input(dict(self.capture, raw_content=" \n "))

    def test_empty_insight_is_rejected(self) -> None:
        with self.assertRaisesRegex(MobileCaptureValidationError, "insight"):
            normalize_capture_input(dict(self.capture, insight=" \n "))

    def test_multiline_insight_is_rejected_to_keep_one_h1(self) -> None:
        with self.assertRaisesRegex(MobileCaptureValidationError, "single line"):
            normalize_capture_input(dict(self.capture, insight="第一行\n第二行"))

    def test_ten_p1_fixtures_are_fictional_valid_and_quick_save_only(self) -> None:
        fixture_paths = sorted(FIXTURE_DIR.glob("*.json"))
        self.assertEqual(len(fixture_paths), 10)
        forbidden = (
            "/Users/",
            "/private/",
            "/Library/Mobile Documents/",
            "Matt_Space",
            "Authorization:",
            "Bearer ",
            "MAKE_WEBHOOK_URL",
        )
        for path in fixture_paths:
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertFalse(any(value in text for value in forbidden))
                payload = json.loads(text)["capture"]
                normalized = normalize_capture_input(payload)
                self.assertIn(
                    normalized["source_type"],
                    {"personal", "voice_transcript", "clipboard"},
                )
                self.assertEqual(normalized["output_goal"], "collect")
                self.assertNotIn("## AI 整理建議", render_mobile_markdown(payload))


if __name__ == "__main__":
    unittest.main()
