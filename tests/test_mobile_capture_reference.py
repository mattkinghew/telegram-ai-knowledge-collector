from __future__ import annotations

import json
import unittest
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

from tools.mobile_capture_reference import (
    MobileCaptureValidationError,
    build_mobile_filename,
    build_obsidian_uri,
    normalize_capture_input,
    render_mobile_markdown,
    validate_mobile_capture,
)


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "mobile_capture"


class MobileCaptureReferenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.capture = {
            "schema_version": "1",
            "captured_at": "2026-08-13T09:05:07+08:00",
            "source_type": "personal",
            "source": "",
            "raw_content": "原始內容 & #100%? = yes / no : ✅",
            "insight": "保留使用者原文。",
            "context": "用於 fictional project。",
            "action": "",
            "output_goal": "collect",
            "project": "",
        }

    def test_markdown_is_deterministic(self) -> None:
        normalized = normalize_capture_input(self.capture)
        self.assertEqual(
            render_mobile_markdown(normalized),
            render_mobile_markdown(normalized),
        )

    def test_chinese_emoji_and_markdown_punctuation_survive_exactly(self) -> None:
        markdown = render_mobile_markdown(normalize_capture_input(self.capture))
        self.assertIn(self.capture["raw_content"], markdown)
        self.assertIn(self.capture["insight"], markdown)

    def test_multiline_raw_content_normalizes_line_endings_only(self) -> None:
        capture = dict(self.capture, raw_content="第一行\r\n  第二行\r第三行  ")
        normalized = normalize_capture_input(capture)
        self.assertEqual(normalized["raw_content"], "第一行\n  第二行\n第三行  ")
        self.assertIn("第一行\n  第二行\n第三行  ", render_mobile_markdown(normalized))

    def test_quick_save_omits_ai_suggestions_section(self) -> None:
        markdown = render_mobile_markdown(normalize_capture_input(self.capture))
        self.assertNotIn("## AI 整理建議", markdown)

    def test_ai_suggestions_are_separate_from_source_and_user_layers(self) -> None:
        normalized = normalize_capture_input(self.capture)
        markdown = render_mobile_markdown(
            normalized,
            ai_suggestions={
                "one_sentence_insight": "這是未確認的 AI 建議。",
                "supporting_points": ["建議核對來源。"],
                "possible_applications": [],
                "suggested_next_action": None,
                "output_angle": None,
                "related_project": None,
                "facts_to_verify": [],
                "missing_information": [],
                "confidence": "low",
            },
        )
        self.assertEqual(markdown.count(self.capture["raw_content"]), 1)
        self.assertIn("## AI 整理建議", markdown)
        self.assertIn("未確認建議", markdown)

    def test_empty_action_and_project_are_accepted(self) -> None:
        normalized = validate_mobile_capture(self.capture)
        self.assertEqual(normalized["action"], "")
        self.assertEqual(normalized["project"], "")

    def test_url_source_preserves_query_fragment_and_percent_encoding(self) -> None:
        source = "https://example.com/a%20b?q=one%20two&x=100%25#part-1"
        capture = dict(
            self.capture,
            source_type="url",
            source=source,
            raw_content=source,
        )
        normalized = validate_mobile_capture(capture)
        self.assertEqual(normalized["source"], source)

    def test_invalid_values_are_rejected(self) -> None:
        cases = (
            dict(self.capture, raw_content=" \n "),
            dict(self.capture, source_type="unknown"),
            dict(self.capture, source_type="url", source="ftp://example.com"),
            dict(self.capture, output_goal="urgent"),
            dict(self.capture, raw_content="x" * 50_001),
            dict(self.capture, unexpected="field"),
        )
        for capture in cases:
            with self.subTest(capture=capture), self.assertRaises(
                MobileCaptureValidationError
            ):
                validate_mobile_capture(capture)

    def test_filename_is_stable_and_collision_suffix_is_explicit(self) -> None:
        captured_at = "2026-08-13T09:05:07+08:00"
        self.assertEqual(build_mobile_filename(captured_at), "00_Inbox/2026-08-13-090507")
        self.assertEqual(
            build_mobile_filename(captured_at, collision_index=2),
            "00_Inbox/2026-08-13-090507-2",
        )

    def test_uri_has_one_of_each_parameter_and_decodes_to_markdown(self) -> None:
        markdown = render_mobile_markdown(normalize_capture_input(self.capture))
        uri = build_obsidian_uri(
            "EXAMPLE_VAULT_ID",
            build_mobile_filename(self.capture["captured_at"]),
            markdown,
        )
        parsed = urlparse(uri)
        params = parse_qs(parsed.query, keep_blank_values=True, strict_parsing=True)
        self.assertEqual(parsed.scheme, "obsidian")
        self.assertEqual(parsed.netloc, "new")
        self.assertEqual(set(params), {"vault", "file", "content"})
        self.assertEqual([len(params[key]) for key in params], [1, 1, 1])
        self.assertEqual(params["vault"][0], "EXAMPLE_VAULT_ID")
        self.assertEqual(params["content"][0], markdown)
        encoded_content = uri.split("content=", 1)[1]
        self.assertEqual(encoded_content, quote(markdown, safe=""))
        self.assertIn("%25", encoded_content)
        for character in "&#?=/:":
            with self.subTest(character=character):
                self.assertNotIn(character, encoded_content)

    def test_all_twenty_fixtures_are_fictional_and_valid(self) -> None:
        fixture_paths = sorted(FIXTURE_DIR.glob("*.json"))
        self.assertEqual(len(fixture_paths), 20)
        self.assertEqual(fixture_paths[0].stem, "01_chinese_short")
        self.assertEqual(
            fixture_paths[-1].stem,
            "20_duplicate_timestamp_collision_case",
        )
        forbidden = (
            "/Users/",
            "/private/",
            "/Library/Mobile Documents/",
            "Matt_Space",
            "Authorization:",
            "Bearer ",
        )
        for path in fixture_paths:
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertFalse(any(value in text for value in forbidden))
                payload = json.loads(text)
                validate_mobile_capture(payload["capture"])


if __name__ == "__main__":
    unittest.main()
