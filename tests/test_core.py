from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from business_knowledge_capture.core import (
    DisabledSummarizer,
    ProtectedPathError,
    classify,
    create_inbox_note,
    extract_source,
    generate_progress_report,
    guard_path,
    initialize_vault,
    load_protected_patterns,
    review_note,
    validate_vault,
)


class CoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.vault = Path(self.temp.name) / "Matt_Space"
        (self.vault / "00_Inbox").mkdir(parents=True)
        (self.vault / "10_Work" / "11_Projects").mkdir(parents=True)
        (self.vault / "90_System").mkdir()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_init_uses_migrated_project_root(self) -> None:
        result = initialize_vault(self.vault)
        self.assertIn("10_Work/11_Projects/14_New_Role_90_Day", result["project"])
        self.assertTrue((self.vault / "90_System" / "Protected_Paths.md").is_file())
        self.assertTrue((self.vault / "10_Work" / "11_Projects" / "14_New_Role_90_Day" / "03_Progress_Reports").is_dir())

    def test_protected_path_blocked(self) -> None:
        initialize_vault(self.vault)
        patterns = load_protected_patterns(self.vault)
        protected = self.vault / "20_Areas" / "25_Self_Management" / "secret.md"
        with self.assertRaises(ProtectedPathError):
            guard_path(protected, self.vault, patterns)

    def test_text_capture_creates_flat_inbox_note(self) -> None:
        initialize_vault(self.vault)
        source = extract_source(
            vault=self.vault,
            patterns=load_protected_patterns(self.vault),
            text="AI PM 新工作 onboarding stakeholder plan",
        )
        output = create_inbox_note(vault=self.vault, source=source, title="First week plan", summarizer=DisabledSummarizer())
        body = output.read_text(encoding="utf-8")
        self.assertEqual(output.parent, self.vault / "00_Inbox")
        self.assertIn("- Suggested Category: 重要知識", body)
        self.assertIn("- Summary Status: pending", body)

    def test_media_is_awaiting_transcription(self) -> None:
        initialize_vault(self.vault)
        media = Path(self.temp.name) / "meeting.mp3"
        media.write_bytes(b"ID3")
        source = extract_source(vault=self.vault, patterns=load_protected_patterns(self.vault), file_path=str(media))
        self.assertEqual(source.processing_status, "awaiting_transcription")

    def test_docx_text_extraction_without_external_dependency(self) -> None:
        initialize_vault(self.vault)
        docx = Path(self.temp.name) / "sample.docx"
        document_xml = b'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:body><w:p><w:r><w:t>AWS exam learning note</w:t></w:r></w:p></w:body>
</w:document>'''
        with zipfile.ZipFile(docx, "w") as archive:
            archive.writestr("word/document.xml", document_xml)
        source = extract_source(vault=self.vault, patterns=load_protected_patterns(self.vault), file_path=str(docx))
        self.assertEqual(source.processing_status, "text_ready")
        self.assertIn("AWS exam", source.readable_text)

    def test_resource_classification_for_deadline(self) -> None:
        result = classify("Free certification course application", deadline="2026-08-31")
        self.assertEqual(result.category, "資源")
        self.assertEqual(result.confidence, "high")

    def test_manual_review_updates_fields_and_checkboxes(self) -> None:
        initialize_vault(self.vault)
        source = extract_source(vault=self.vault, patterns=load_protected_patterns(self.vault), text="Reference guide for future use.")
        note = create_inbox_note(vault=self.vault, source=source)
        review_note(vault=self.vault, note_path=note, category="次要知識", action_required="Review next month", mark=["classification", "action"])
        body = note.read_text(encoding="utf-8")
        self.assertIn("- Suggested Category: 次要知識", body)
        self.assertIn("- [x] Classification reviewed", body)
        self.assertIn("- [x] Action confirmed", body)

    def test_progress_report_from_selected_notes(self) -> None:
        initialize_vault(self.vault)
        source = extract_source(
            vault=self.vault,
            patterns=load_protected_patterns(self.vault),
            text="Completed onboarding checklist and saved evidence.",
            external_file_link="https://drive.google.com/example",
        )
        note = create_inbox_note(vault=self.vault, source=source, title="Onboarding checklist", action_required="Share with manager")
        report = generate_progress_report(
            vault=self.vault,
            completed_paths=[note],
            in_progress_paths=[],
            period_label="2026-07-26",
            report_type="daily",
            commitments=["Confirm next milestone"],
        )
        body = report.read_text(encoding="utf-8")
        self.assertIn("Onboarding checklist", body)
        self.assertIn("https://drive.google.com/example", body)
        self.assertIn("Confirm next milestone", body)

    def test_all_supported_file_types_register(self) -> None:
        initialize_vault(self.vault)
        expected = {
            ".txt": "text_ready",
            ".md": "text_ready",
            ".jpg": "registered_metadata_only",
            ".png": "registered_metadata_only",
            ".mp3": "awaiting_transcription",
            ".mp4": "awaiting_transcription",
        }
        for extension, status in expected.items():
            path = Path(self.temp.name) / f"sample{extension}"
            path.write_bytes(b"sample")
            source = extract_source(vault=self.vault, patterns=load_protected_patterns(self.vault), file_path=str(path))
            self.assertEqual(source.processing_status, status, extension)

        pdf = Path(self.temp.name) / "sample.pdf"
        pdf.write_bytes(b"%PDF-1.4\n%%EOF")
        source = extract_source(vault=self.vault, patterns=load_protected_patterns(self.vault), file_path=str(pdf))
        self.assertIn(source.processing_status, {"awaiting_text_extraction", "extraction_failed", "text_ready"})
        self.assertEqual(source.local_file, str(pdf))

    def test_url_registers_without_network_fetch(self) -> None:
        initialize_vault(self.vault)
        source = extract_source(
            vault=self.vault,
            patterns=load_protected_patterns(self.vault),
            url="https://example.com/resource",
        )
        self.assertEqual(source.processing_status, "url_registered")
        self.assertEqual(source.source_url, "https://example.com/resource")
        self.assertEqual(source.readable_text, "")

    def test_missing_file_is_preserved_as_error_record(self) -> None:
        initialize_vault(self.vault)
        missing = Path(self.temp.name) / "missing.pdf"
        source = extract_source(vault=self.vault, patterns=load_protected_patterns(self.vault), file_path=str(missing))
        note = create_inbox_note(vault=self.vault, source=source, title="Missing source")
        body = note.read_text(encoding="utf-8")
        self.assertIn("- Processing Status: source_missing", body)
        self.assertIn(str(missing), body)

    def test_validate_rejects_inbox_subfolder(self) -> None:
        initialize_vault(self.vault)
        (self.vault / "00_Inbox" / "nested").mkdir()
        errors = validate_vault(self.vault)
        self.assertTrue(any("flat" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
