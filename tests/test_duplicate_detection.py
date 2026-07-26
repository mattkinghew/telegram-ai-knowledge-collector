from __future__ import annotations

import hashlib
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

from business_knowledge_capture.cli import main
from business_knowledge_capture.core import (
    DuplicateResult,
    ExtractedSource,
    ProtectedPathError,
    capture_inbox_note,
    create_inbox_note,
    extract_source,
    find_exact_duplicates,
    generate_progress_report,
    guard_path,
    initialize_vault,
    load_protected_patterns,
    normalize_url_for_duplicate,
    review_note,
)


class DuplicateDetectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(dir="/private/tmp")
        self.vault = Path(self.temp.name) / "vault"
        (self.vault / "00_Inbox").mkdir(parents=True)
        (self.vault / "10_Work" / "11_Projects").mkdir(parents=True)
        (self.vault / "90_System").mkdir()
        initialize_vault(self.vault)
        self.patterns = load_protected_patterns(self.vault)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def source_text(self, value: str) -> ExtractedSource:
        return extract_source(vault=self.vault, patterns=self.patterns, text=value)

    def source_url(self, value: str) -> ExtractedSource:
        return extract_source(vault=self.vault, patterns=self.patterns, url=value)

    def write_candidate(self, name: str, *, content_hash: str = "", source_url: str = "") -> Path:
        path = self.vault / "00_Inbox" / name
        path.write_text(
            "# Candidate\n\n"
            "## Metadata\n\n"
            f"- Source URL: {source_url}\n"
            f"- Content Hash: {content_hash}\n\n"
            "## Source Notes\n\n"
            "This body must not be used for duplicate matching.\n",
            encoding="utf-8",
        )
        return path

    def test_only_direct_inbox_markdown_candidates_are_inspected(self) -> None:
        source = self.source_text("direct scope")
        direct = self.write_candidate("direct.txt", content_hash=source.content_hash)
        self.assertEqual(find_exact_duplicates(vault=self.vault, source=source).status, "unique")
        self.assertTrue(direct.is_file())

    def test_inbox_subdirectories_are_not_recursively_checked(self) -> None:
        source = self.source_text("nested scope")
        nested = self.vault / "00_Inbox" / "nested"
        nested.mkdir()
        (nested / "duplicate.md").write_text(
            f"## Metadata\n\n- Content Hash: {source.content_hash}\n\n## Source Notes\nsecret",
            encoding="utf-8",
        )
        self.assertEqual(find_exact_duplicates(vault=self.vault, source=source).status, "unique")

    def test_symlink_candidate_is_skipped_without_following(self) -> None:
        source = self.source_text("symlink scope")
        target = Path(self.temp.name) / "outside.md"
        target.write_text(f"## Metadata\n\n- Content Hash: {source.content_hash}\n", encoding="utf-8")
        (self.vault / "00_Inbox" / "link.md").symlink_to(target)
        result = find_exact_duplicates(vault=self.vault, source=source)
        self.assertEqual(result.status, "unique")
        self.assertTrue(result.diagnostics)

    def test_protected_path_rules_remain_enforced(self) -> None:
        with self.assertRaises(ProtectedPathError):
            guard_path(self.vault / "Private" / "note.md", self.vault, self.patterns)

    def test_vault_external_markdown_is_not_read(self) -> None:
        source = self.source_text("external scope")
        external = Path(self.temp.name) / "external.md"
        external.write_text(f"## Metadata\n\n- Content Hash: {source.content_hash}\n", encoding="utf-8")
        with mock.patch(
            "business_knowledge_capture.core._read_inbox_metadata",
            wraps=__import__(
                "business_knowledge_capture.core",
                fromlist=["_read_inbox_metadata"],
            )._read_inbox_metadata,
        ) as reader:
            result = find_exact_duplicates(vault=self.vault, source=source)
        self.assertEqual(result.status, "unique")
        reader.assert_not_called()

    def test_candidate_limit_makes_check_unavailable(self) -> None:
        source = self.source_text("candidate limit")
        self.write_candidate("a.md")
        self.write_candidate("b.md")
        result = find_exact_duplicates(vault=self.vault, source=source, max_candidates=1)
        self.assertEqual(result.status, "check_unavailable")
        self.assertEqual(result.match_type, "unavailable")
        self.assertIn("limit exceeded", result.diagnostics[0])

    def test_same_text_is_content_hash_duplicate(self) -> None:
        create_inbox_note(vault=self.vault, source=self.source_text("same text"))
        _, result = capture_inbox_note(vault=self.vault, source=self.source_text("same text"))
        self.assertEqual(result.match_type, "content_hash")

    def test_different_text_is_unique(self) -> None:
        create_inbox_note(vault=self.vault, source=self.source_text("first"))
        _, result = capture_inbox_note(vault=self.vault, source=self.source_text("second"))
        self.assertEqual(result, DuplicateResult("unique", "none"))

    def test_same_file_bytes_are_content_hash_duplicate(self) -> None:
        first = Path(self.temp.name) / "first.txt"
        second = Path(self.temp.name) / "second.txt"
        first.write_bytes(b"identical bytes")
        second.write_bytes(b"identical bytes")
        create_inbox_note(
            vault=self.vault,
            source=extract_source(vault=self.vault, patterns=self.patterns, file_path=str(first)),
        )
        _, result = capture_inbox_note(
            vault=self.vault,
            source=extract_source(vault=self.vault, patterns=self.patterns, file_path=str(second)),
        )
        self.assertEqual(result.match_type, "content_hash")

    def test_missing_file_duplicate_check_is_unavailable(self) -> None:
        missing = Path(self.temp.name) / "missing.pdf"
        source = extract_source(vault=self.vault, patterns=self.patterns, file_path=str(missing))
        self.assertEqual(find_exact_duplicates(vault=self.vault, source=source).status, "check_unavailable")

    def test_source_without_hash_or_url_is_not_misclassified(self) -> None:
        source = ExtractedSource("file", processing_status="registered_metadata_only")
        result = find_exact_duplicates(vault=self.vault, source=source)
        self.assertEqual(result, DuplicateResult("check_unavailable", "unavailable"))

    def test_url_normalizes_scheme_and_hostname_case(self) -> None:
        self.assertEqual(
            normalize_url_for_duplicate("HTTPS://Example.COM/resource"),
            "https://example.com/resource",
        )

    def test_url_normalizes_idna_hostname(self) -> None:
        self.assertEqual(
            normalize_url_for_duplicate("https://例子.测试/resource"),
            "https://xn--fsqu00a.xn--0zwm56d/resource",
        )

    def test_url_normalizes_default_ports(self) -> None:
        self.assertEqual(normalize_url_for_duplicate("http://example.com:80"), "http://example.com/")
        self.assertEqual(normalize_url_for_duplicate("https://example.com:443"), "https://example.com/")

    def test_url_removes_fragment(self) -> None:
        self.assertEqual(
            normalize_url_for_duplicate("https://example.com/resource#one"),
            "https://example.com/resource",
        )

    def test_url_preserves_path_case(self) -> None:
        self.assertNotEqual(
            normalize_url_for_duplicate("https://example.com/Resource"),
            normalize_url_for_duplicate("https://example.com/resource"),
        )

    def test_url_preserves_trailing_slash_difference(self) -> None:
        self.assertNotEqual(
            normalize_url_for_duplicate("https://example.com/resource"),
            normalize_url_for_duplicate("https://example.com/resource/"),
        )

    def test_url_preserves_query_order(self) -> None:
        self.assertNotEqual(
            normalize_url_for_duplicate("https://example.com/resource?a=1&b=2"),
            normalize_url_for_duplicate("https://example.com/resource?b=2&a=1"),
        )

    def test_url_preserves_http_https_difference(self) -> None:
        self.assertNotEqual(
            normalize_url_for_duplicate("http://example.com/resource"),
            normalize_url_for_duplicate("https://example.com/resource"),
        )

    def test_unsupported_url_scheme_is_not_comparable(self) -> None:
        self.assertEqual(normalize_url_for_duplicate("ftp://example.com/resource"), "")

    def test_normalized_url_duplicate_is_detected(self) -> None:
        create_inbox_note(
            vault=self.vault,
            source=self.source_url("https://Example.com:443/resource#overview"),
        )
        _, result = capture_inbox_note(
            vault=self.vault,
            source=self.source_url("https://example.com/resource#details"),
        )
        self.assertEqual(result.match_type, "normalized_url")

    def test_unique_metadata_is_rendered(self) -> None:
        note = create_inbox_note(vault=self.vault, source=self.source_text("unique metadata"))
        body = note.read_text(encoding="utf-8")
        self.assertIn("- Duplicate Status: unique", body)
        self.assertIn("- Duplicate Match Type: none", body)
        self.assertIn("- Duplicate Match Count: 0", body)

    def test_content_hash_duplicate_metadata_is_rendered(self) -> None:
        create_inbox_note(vault=self.vault, source=self.source_text("hash metadata"))
        note = create_inbox_note(vault=self.vault, source=self.source_text("hash metadata"))
        body = note.read_text(encoding="utf-8")
        self.assertIn("- Duplicate Status: exact_duplicate_suggested", body)
        self.assertIn("- Duplicate Match Type: content_hash", body)

    def test_url_duplicate_metadata_is_rendered(self) -> None:
        create_inbox_note(vault=self.vault, source=self.source_url("https://EXAMPLE.com:443/a#x"))
        note = create_inbox_note(vault=self.vault, source=self.source_url("https://example.com/a#y"))
        self.assertIn("- Duplicate Match Type: normalized_url", note.read_text(encoding="utf-8"))

    def test_both_hash_and_url_match_type_is_rendered(self) -> None:
        source = self.source_url("https://example.com/same")
        create_inbox_note(vault=self.vault, source=source)
        note = create_inbox_note(vault=self.vault, source=source)
        self.assertIn("- Duplicate Match Type: content_hash_and_url", note.read_text(encoding="utf-8"))

    def test_only_five_duplicate_paths_are_recorded(self) -> None:
        source = self.source_text("many matches")
        for index in range(7):
            self.write_candidate(f"{index}.md", content_hash=source.content_hash)
        result = find_exact_duplicates(vault=self.vault, source=source)
        self.assertEqual(result.match_count, 7)
        self.assertEqual(len(result.matches), 5)
        self.assertEqual(result.matches, tuple(sorted(result.matches)))

    def test_duplicate_paths_are_vault_relative(self) -> None:
        source = self.source_text("relative match")
        candidate = self.write_candidate("relative.md", content_hash=source.content_hash)
        result = find_exact_duplicates(vault=self.vault, source=source)
        self.assertEqual(result.matches, ("00_Inbox/relative.md",))
        self.assertNotIn(str(self.vault), ",".join(result.matches))
        self.assertTrue(candidate.is_file())

    def test_duplicate_path_metadata_stays_on_one_line(self) -> None:
        source = self.source_text("newline path")
        self.write_candidate("line\nbreak.md", content_hash=source.content_hash)
        note = create_inbox_note(vault=self.vault, source=source)
        duplicate_line = next(
            line
            for line in note.read_text(encoding="utf-8").splitlines()
            if line.startswith("- Duplicate Of:")
        )
        self.assertEqual(duplicate_line, "- Duplicate Of: 00_Inbox/line break.md")

    def test_mark_duplicate_checks_manual_review_box(self) -> None:
        note = create_inbox_note(vault=self.vault, source=self.source_text("review duplicate"))
        review_note(vault=self.vault, note_path=note, mark=["duplicate"])
        self.assertIn("- [x] Duplicate status reviewed", note.read_text(encoding="utf-8"))

    def test_old_p0_note_without_duplicate_fields_can_generate_report(self) -> None:
        note = self.vault / "00_Inbox" / "legacy.md"
        note.write_text(
            "# Legacy\n\n## Metadata\n\n- Source URL:\n- Content Hash:\n\n"
            "## One-line Summary\n\nLegacy summary\n\n## Suggested Actions\n\nReview legacy note\n",
            encoding="utf-8",
        )
        report = generate_progress_report(
            vault=self.vault,
            completed_paths=[note],
            in_progress_paths=[],
            period_label="legacy",
            report_type="daily",
        )
        self.assertIn("Legacy", report.read_text(encoding="utf-8"))

    def test_old_p0_note_can_use_existing_review_marks(self) -> None:
        note = self.vault / "00_Inbox" / "legacy-review.md"
        note.write_text(
            "# Legacy\n\n## Metadata\n\n- Suggested Category: 其他\n- Action Required:\n"
            "- Related Project:\n- Related Area:\n\n## Relevance\n\n"
            "Suggested category: **其他** (low confidence).\n\n## Suggested Actions\n\n"
            "Review\n\n## Source Notes\n\nLegacy\n\n## Manual Review\n\n"
            "- [ ] Summary reviewed\n- [ ] Classification reviewed\n- [ ] Action confirmed\n"
            "- [ ] Related links added\n- [ ] Final destination confirmed\n",
            encoding="utf-8",
        )
        review_note(vault=self.vault, note_path=note, mark=["summary"])
        self.assertIn("- [x] Summary reviewed", note.read_text(encoding="utf-8"))

    def test_cli_duplicate_warning_uses_relative_match_path(self) -> None:
        first_stdout = StringIO()
        with redirect_stdout(first_stdout), redirect_stderr(StringIO()):
            self.assertEqual(
                main(["capture", "--vault", str(self.vault), "--text", "CLI duplicate"]),
                0,
            )
        second_stdout = StringIO()
        second_stderr = StringIO()
        with redirect_stdout(second_stdout), redirect_stderr(second_stderr):
            self.assertEqual(
                main(["capture", "--vault", str(self.vault), "--text", "CLI duplicate"]),
                0,
            )
        warning = second_stderr.getvalue()
        self.assertIn("WARNING: Exact duplicate suggested.", warning)
        self.assertIn("Match type: content_hash", warning)
        self.assertIn("Existing notes: 1", warning)
        self.assertIn("00_Inbox/", warning)
        self.assertNotIn(str(self.vault), warning)

    def test_malformed_candidate_is_skipped_without_blocking_capture(self) -> None:
        (self.vault / "00_Inbox" / "malformed.md").write_text("# Missing metadata\n", encoding="utf-8")
        note, result = capture_inbox_note(vault=self.vault, source=self.source_text("still captured"))
        self.assertTrue(note.is_file())
        self.assertEqual(result.status, "unique")
        self.assertTrue(result.diagnostics)

    def test_text_hash_uses_complete_normalized_capture_text(self) -> None:
        source = self.source_text("  exact text  ")
        self.assertEqual(source.content_hash, hashlib.sha256(b"exact text").hexdigest())


if __name__ == "__main__":
    unittest.main()
