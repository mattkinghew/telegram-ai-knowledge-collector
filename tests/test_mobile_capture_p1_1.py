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


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "mobile_capture_p1_1"


class MobileCaptureP11Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.capture = {
            "schema_version": "1",
            "captured_at": "2026-08-13T10:15:30+08:00",
            "source_type": "url",
            "source": "https://example.com/public-note",
            "raw_content": "Public example title\nhttps://example.com/public-note",
            "insight": "共享內容應保留來源與使用者反思。",
            "context": "用於 fictional Share Sheet 測試。",
            "action": "在裝置驗收時比較預覽與筆記。",
            "project": "",
        }

    def test_basic_https_url_is_preserved_in_frontmatter(self) -> None:
        source = "https://example.com/public-note"
        normalized = normalize_capture_input(dict(self.capture, source=source))
        self.assertEqual(normalized["source"], source)
        self.assertIn(f'source: "{source}"', render_mobile_markdown(normalized))

    def test_http_url_is_supported_without_fetching(self) -> None:
        source = "http://example.com/public-note"
        normalized = normalize_capture_input(dict(self.capture, source=source))
        self.assertEqual(normalized["source"], source)

    def test_url_query_string_is_preserved_exactly(self) -> None:
        source = "https://example.com/search?q=share%20sheet&lang=zh-HK"
        normalized = normalize_capture_input(dict(self.capture, source=source))
        self.assertEqual(normalized["source"], source)

    def test_url_fragment_is_preserved_exactly(self) -> None:
        source = "https://example.com/guide#capture-flow"
        normalized = normalize_capture_input(dict(self.capture, source=source))
        self.assertEqual(normalized["source"], source)

    def test_percent_encoded_url_is_preserved_exactly(self) -> None:
        source = "https://example.com/a%20b?q=100%25#part%201"
        normalized = normalize_capture_input(dict(self.capture, source=source))
        self.assertEqual(normalized["source"], source)

    def test_url_source_survives_obsidian_uri_round_trip(self) -> None:
        source = "https://example.com/a%20b?q=one%20two&x=100%25#part-1"
        capture = dict(self.capture, source=source, raw_content=source)
        markdown = render_mobile_markdown(capture)
        file_path = build_mobile_filename(
            capture["captured_at"], unique_suffix="4821"
        )
        uri = build_obsidian_uri("EXAMPLE_VAULT_ID", file_path, markdown)
        decoded_markdown = parse_qs(
            urlparse(uri).query,
            keep_blank_values=True,
            strict_parsing=True,
        )["content"][0]
        self.assertEqual(decoded_markdown, markdown)
        self.assertIn(f'source: "{source}"', decoded_markdown)

    def test_chinese_shared_text_is_preserved(self) -> None:
        raw = "這段分享文字必須完整保留。"
        capture = dict(
            self.capture,
            source_type="shared_text",
            source="",
            raw_content=raw,
        )
        self.assertEqual(normalize_capture_input(capture)["raw_content"], raw)

    def test_multiline_shared_text_is_preserved(self) -> None:
        raw = "第一行\n  第二行\n第三行"
        capture = dict(
            self.capture,
            source_type="shared_text",
            source="",
            raw_content=raw,
        )
        self.assertEqual(normalize_capture_input(capture)["raw_content"], raw)

    def test_markdown_rich_shared_text_is_preserved(self) -> None:
        raw = "## 標題\n- [ ] `code` & 100% ✅"
        capture = dict(
            self.capture,
            source_type="shared_text",
            source="",
            raw_content=raw,
        )
        self.assertIn(raw, render_mobile_markdown(capture))

    def test_image_reference_uses_user_description_without_ocr(self) -> None:
        description = "截圖顯示一個 fictional 表格；沒有進行 OCR。"
        capture = dict(
            self.capture,
            source_type="image_reference",
            source="example-screenshot.png",
            raw_content=description,
        )
        normalized = normalize_capture_input(capture)
        self.assertEqual(normalized["raw_content"], description)
        self.assertEqual(normalized["source"], "example-screenshot.png")

    def test_pdf_reference_uses_user_description_without_parsing(self) -> None:
        description = "這是 fictional PDF 的人工描述；沒有解析內容。"
        capture = dict(
            self.capture,
            source_type="file_reference",
            source="example-handout.pdf",
            raw_content=description,
        )
        self.assertEqual(normalize_capture_input(capture)["raw_content"], description)

    def test_generic_file_reference_uses_public_safe_filename(self) -> None:
        capture = dict(
            self.capture,
            source_type="file_reference",
            source="example-notes.txt",
            raw_content="這是 fictional file 的人工描述。",
        )
        self.assertEqual(normalize_capture_input(capture)["source"], "example-notes.txt")

    def test_missing_image_description_is_rejected(self) -> None:
        capture = dict(
            self.capture,
            source_type="image_reference",
            source="example.png",
            raw_content=" \n ",
        )
        with self.assertRaisesRegex(MobileCaptureValidationError, "raw_content"):
            normalize_capture_input(capture)

    def test_missing_file_description_is_rejected(self) -> None:
        capture = dict(
            self.capture,
            source_type="file_reference",
            source="example.pdf",
            raw_content="",
        )
        with self.assertRaisesRegex(MobileCaptureValidationError, "raw_content"):
            normalize_capture_input(capture)

    def test_malformed_url_is_rejected(self) -> None:
        capture = dict(self.capture, source="https://")
        with self.assertRaisesRegex(MobileCaptureValidationError, "HTTP or HTTPS"):
            normalize_capture_input(capture)

    def test_unsupported_input_type_is_rejected(self) -> None:
        capture = dict(self.capture, source_type="video")
        with self.assertRaisesRegex(MobileCaptureValidationError, "unsupported"):
            normalize_capture_input(capture)

    def test_existing_typed_p1_0_capture_remains_supported(self) -> None:
        capture = dict(
            self.capture,
            source_type="personal",
            source="",
            raw_content="手動輸入內容",
        )
        self.assertEqual(normalize_capture_input(capture)["source_type"], "personal")

    def test_existing_voice_p1_0_capture_remains_supported(self) -> None:
        capture = dict(
            self.capture,
            source_type="voice_transcript",
            source="",
            raw_content="已由使用者檢查的語音文字",
        )
        self.assertEqual(
            normalize_capture_input(capture)["source_type"], "voice_transcript"
        )

    def test_existing_clipboard_p1_0_capture_remains_supported(self) -> None:
        capture = dict(
            self.capture,
            source_type="clipboard",
            source="",
            raw_content="剪貼簿內容",
        )
        self.assertEqual(normalize_capture_input(capture)["source_type"], "clipboard")

    def test_shared_text_rejects_a_nonempty_source_field(self) -> None:
        capture = dict(
            self.capture,
            source_type="shared_text",
            source="unexpected origin",
            raw_content="共享文字",
        )
        with self.assertRaisesRegex(MobileCaptureValidationError, "source must be blank"):
            normalize_capture_input(capture)

    def test_reference_rejects_a_relative_path_instead_of_a_filename(self) -> None:
        capture = dict(
            self.capture,
            source_type="file_reference",
            source="folder/example.pdf",
            raw_content="文件的人工描述。",
        )
        with self.assertRaisesRegex(MobileCaptureValidationError, "filename"):
            normalize_capture_input(capture)

    def test_p1_1_fixtures_are_fictional_valid_and_quick_save_only(self) -> None:
        fixture_paths = sorted(FIXTURE_DIR.glob("*.json"))
        self.assertEqual(len(fixture_paths), 11)
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
                capture = json.loads(text)["capture"]
                normalized = normalize_capture_input(capture)
                self.assertIn(
                    normalized["source_type"],
                    {"url", "shared_text", "image_reference", "file_reference"},
                )
                self.assertEqual(normalized["output_goal"], "collect")
                self.assertNotIn("## AI 整理建議", render_mobile_markdown(capture))


if __name__ == "__main__":
    unittest.main()
