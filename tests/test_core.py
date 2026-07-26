from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from business_knowledge_capture.core import (
    DisabledSummarizer,
    ProtectedPathError,
    UnsafePathError,
    VaultStructureError,
    _SafeRedirectHandler,
    classify,
    create_inbox_note,
    detect_project_root,
    extract_source,
    generate_progress_report,
    guard_path,
    initialize_vault,
    load_protected_patterns,
    review_note,
    validate_public_url,
    validate_vault,
)


class CoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(dir="/private/tmp")
        self.vault = Path(self.temp.name) / "Example_Business_Vault"
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
        self.assertIn("## Suggested Actions\n\nReview next month", body)
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

    def test_duplicate_new_role_projects_are_rejected(self) -> None:
        (self.vault / "10_Work" / "11_Projects" / "14_New_Role_90_Day").mkdir()
        (self.vault / "10_Projects" / "14_New_Role_90_Day").mkdir(parents=True)
        with self.assertRaises(VaultStructureError):
            detect_project_root(self.vault)

    def test_existing_legacy_project_is_reused(self) -> None:
        (self.vault / "10_Work").rename(self.vault / "10_Work_unused")
        legacy = self.vault / "10_Projects" / "14_New_Role_90_Day"
        legacy.mkdir(parents=True)
        self.assertEqual(detect_project_root(self.vault), self.vault / "10_Projects")

    def test_explicit_project_root_cannot_escape_approved_roots(self) -> None:
        with self.assertRaises(VaultStructureError):
            detect_project_root(self.vault, "../unapproved")

    def test_protected_paths_merge_preserves_custom_rules_and_is_idempotent(self) -> None:
        protected = self.vault / "90_System" / "Protected_Paths.md"
        protected.write_text("# Custom policy\n\n- `Custom_Restricted/**`\n", encoding="utf-8")
        initialize_vault(self.vault)
        first = protected.read_text(encoding="utf-8")
        initialize_vault(self.vault)
        second = protected.read_text(encoding="utf-8")
        self.assertIn("Custom_Restricted/**", first)
        rule_lines = {
            line.strip()[3:-1]
            for line in first.splitlines()
            if line.strip().startswith("- `") and line.strip().endswith("`")
        }
        for pattern in (
            "20_Areas/25_Self_Management/**",
            "25_Self_Management/**",
            "Private/**",
            "Credentials/**",
            ".env",
            ".obsidian/**",
        ):
            self.assertIn(pattern, rule_lines)
        self.assertEqual(first, second)

    def test_existing_template_conflict_creates_stable_v2_without_overwrite(self) -> None:
        templates = self.vault / "90_System" / "Templates"
        templates.mkdir()
        original = templates / "Inbox_Note.md"
        original.write_text("# User template\n", encoding="utf-8")
        initialize_vault(self.vault)
        versioned = templates / "Inbox_Note.v2.md"
        first_version = versioned.read_text(encoding="utf-8")
        initialize_vault(self.vault)
        self.assertEqual(original.read_text(encoding="utf-8"), "# User template\n")
        self.assertEqual(versioned.read_text(encoding="utf-8"), first_version)
        self.assertFalse((templates / "Inbox_Note.v3.md").exists())

    def test_same_template_content_is_preserved(self) -> None:
        first = initialize_vault(self.vault)
        template = Path(first["inbox_template"])
        before = template.read_text(encoding="utf-8")
        second = initialize_vault(self.vault)
        self.assertEqual(Path(second["inbox_template"]), template)
        self.assertEqual(template.read_text(encoding="utf-8"), before)

    def test_capture_blocks_symlink_file_without_reading_target(self) -> None:
        initialize_vault(self.vault)
        target = Path(self.temp.name) / "target.txt"
        target.write_text("must not be read", encoding="utf-8")
        link = Path(self.temp.name) / "source.txt"
        link.symlink_to(target)
        patterns = load_protected_patterns(self.vault)
        with mock.patch("pathlib.Path.read_text", side_effect=AssertionError("target read")):
            with self.assertRaises(UnsafePathError):
                extract_source(
                    vault=self.vault,
                    patterns=patterns,
                    file_path=str(link),
                )

    def test_review_blocks_symlink_note(self) -> None:
        initialize_vault(self.vault)
        target = self.vault / "00_Inbox" / "target.md"
        target.write_text("# Target\n", encoding="utf-8")
        link = self.vault / "00_Inbox" / "link.md"
        link.symlink_to(target)
        with self.assertRaises(UnsafePathError):
            review_note(vault=self.vault, note_path=link, category="重要知識")

    def test_symlink_ancestor_is_blocked(self) -> None:
        initialize_vault(self.vault)
        target = Path(self.temp.name) / "external"
        target.mkdir()
        (target / "note.txt").write_text("target", encoding="utf-8")
        link_dir = Path(self.temp.name) / "linked"
        link_dir.symlink_to(target, target_is_directory=True)
        with self.assertRaises(UnsafePathError):
            extract_source(
                vault=self.vault,
                patterns=load_protected_patterns(self.vault),
                file_path=str(link_dir / "note.txt"),
            )

    def test_review_rejects_external_markdown(self) -> None:
        initialize_vault(self.vault)
        external = Path(self.temp.name) / "external.md"
        external.write_text("# External\n", encoding="utf-8")
        with self.assertRaises(UnsafePathError):
            review_note(vault=self.vault, note_path=external)

    def test_report_rejects_external_markdown(self) -> None:
        initialize_vault(self.vault)
        external = Path(self.temp.name) / "external.md"
        external.write_text("# External\n", encoding="utf-8")
        with self.assertRaises(UnsafePathError):
            generate_progress_report(
                vault=self.vault,
                completed_paths=[external],
                in_progress_paths=[],
                period_label="2026-07-26",
                report_type="daily",
            )

    def test_review_rejects_non_markdown_and_protected_note(self) -> None:
        initialize_vault(self.vault)
        text_file = self.vault / "00_Inbox" / "note.txt"
        text_file.write_text("text", encoding="utf-8")
        with self.assertRaises(UnsafePathError):
            review_note(vault=self.vault, note_path=text_file)
        protected = self.vault / "Private" / "note.md"
        with self.assertRaises(ProtectedPathError):
            review_note(vault=self.vault, note_path=protected)

    def test_url_validator_blocks_non_public_targets(self) -> None:
        blocked = (
            "http://localhost",
            "http://service.localhost/path",
            "http://127.0.0.1",
            "http://[::1]",
            "http://10.0.0.1",
            "http://169.254.1.1",
            "http://224.0.0.1",
            "http://192.0.2.1",
            "file:///tmp/a",
            "ftp://example.com/a",
            "data:text/plain,hello",
            "javascript:alert(1)",
        )
        for url in blocked:
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    validate_public_url(url)

    def test_url_validator_accepts_public_resolution(self) -> None:
        records = [(2, 1, 6, "", ("93.184.216.34", 443))]
        resolver = mock.Mock(return_value=records)
        self.assertEqual(
            validate_public_url("https://example.com/resource", resolver=resolver),
            "https://example.com/resource",
        )
        resolver.assert_called_once()

    def test_redirect_target_is_validated_before_following(self) -> None:
        handler = _SafeRedirectHandler()
        request = mock.Mock()
        with mock.patch(
            "business_knowledge_capture.core.validate_public_url",
            side_effect=ValueError("blocked"),
        ) as validator:
            with self.assertRaises(ValueError):
                handler.redirect_request(
                    request,
                    None,
                    302,
                    "Found",
                    {},
                    "http://127.0.0.1/private",
                )
        validator.assert_called_once_with("http://127.0.0.1/private")

    def test_metadata_newlines_are_sanitized_but_source_notes_are_preserved(self) -> None:
        initialize_vault(self.vault)
        raw = "line one\n## Original source heading\nline three"
        source = extract_source(
            vault=self.vault,
            patterns=load_protected_patterns(self.vault),
            text=raw,
            external_file_link="https://example.com\n## Injected",
        )
        note = create_inbox_note(
            vault=self.vault,
            source=source,
            title="Title\n## Injected",
            action_required="Act\n## Injected",
            related_project="Project\n## Injected",
            related_area="Area\n## Injected",
            deadline="2026-07-26",
        )
        body = note.read_text(encoding="utf-8")
        self.assertIn("# Title ## Injected", body)
        self.assertIn("- Action Required: Act ## Injected", body)
        self.assertIn("- External File Link: https://example.com ## Injected", body)
        self.assertIn("- Deadline: 2026-07-26", body)
        self.assertIn(raw, body)

    def test_manual_category_updates_metadata_and_relevance(self) -> None:
        initialize_vault(self.vault)
        source = extract_source(
            vault=self.vault,
            patterns=load_protected_patterns(self.vault),
            text="x",
        )
        note = create_inbox_note(vault=self.vault, source=source)
        before = note.read_text(encoding="utf-8")
        self.assertIn("- Suggested Category: 其他", before)
        review_note(
            vault=self.vault,
            note_path=note,
            category="重要知識",
            mark=["classification"],
        )
        after = note.read_text(encoding="utf-8")
        self.assertIn("- Suggested Category: 重要知識", after)
        self.assertIn("Suggested category: **重要知識** (manual confidence).", after)
        self.assertNotIn("Suggested category: **其他**", after)
        self.assertIn("- [x] Classification reviewed", after)


if __name__ == "__main__":
    unittest.main()
