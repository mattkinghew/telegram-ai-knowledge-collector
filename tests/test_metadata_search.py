from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import date
from io import StringIO
from pathlib import Path

from business_knowledge_capture.cli import main
from business_knowledge_capture.core import UnsafePathError, initialize_vault
from business_knowledge_capture.search import (
    InboxSearchQuery,
    InboxSearchRecord,
    format_search_diagnostics,
    format_search_json,
    format_search_text,
    parse_filter_date,
    search_inbox,
    sort_search_records,
)


class MetadataSearchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(dir="/private/tmp")
        self.vault = Path(self.temp.name) / "vault"
        (self.vault / "00_Inbox").mkdir(parents=True)
        (self.vault / "10_Work" / "11_Projects").mkdir(parents=True)
        (self.vault / "90_System").mkdir()
        initialize_vault(self.vault)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_note(self, name: str, title: str = "Note", **overrides: str) -> Path:
        metadata = {
            "Created": "2026-07-26T12:00:00+08:00",
            "Source Type": "text",
            "Source URL": "https://secret.example/private",
            "Local File": "/private/source/file.pdf",
            "Processing Status": "registered",
            "Suggested Category": "其他",
            "Action Required": "",
            "Deadline": "",
            "Related Project": "",
            "Related Area": "",
            "Source Filename": "",
            "File Type": "text/plain",
            "Content Hash": "a" * 64,
            "Duplicate Status": "unique",
            "Duplicate Match Type": "none",
        }
        metadata.update(overrides)
        body = "\n".join(f"- {key}: {value}" for key, value in metadata.items())
        path = self.vault / "00_Inbox" / name
        path.write_text(
            f"# {title}\n\n## Metadata\n\n{body}\n\n"
            "## One-line Summary\n\nSUMMARY-ONLY-SECRET\n\n"
            "## Source Notes\n\nSOURCE-NOTES-ONLY-SECRET\n",
            encoding="utf-8",
        )
        return path

    def result(self, **query_values: object):
        return search_inbox(
            vault=self.vault,
            query=InboxSearchQuery(**query_values),
        )

    def test_01_only_direct_inbox_markdown_is_scanned(self) -> None:
        self.write_note("direct.md", "Direct")
        (self.vault / "00_Inbox" / "ignored.txt").write_text("# Ignored", encoding="utf-8")
        self.assertEqual([r.title for r in self.result().records], ["Direct"])

    def test_02_inbox_subfolder_is_not_scanned(self) -> None:
        nested = self.vault / "00_Inbox" / "nested"
        nested.mkdir()
        (nested / "hidden.md").write_text("# Hidden", encoding="utf-8")
        self.assertEqual(self.result().total_matches, 0)

    def test_03_symlink_note_is_skipped(self) -> None:
        target = Path(self.temp.name) / "outside.md"
        target.write_text("# Outside\n\n## Metadata\n", encoding="utf-8")
        (self.vault / "00_Inbox" / "link.md").symlink_to(target)
        result = self.result()
        self.assertEqual(result.total_matches, 0)
        self.assertTrue(result.diagnostics)

    def test_04_symlink_ancestor_is_blocked(self) -> None:
        alias = Path(self.temp.name) / "vault-alias"
        alias.symlink_to(self.vault)
        with self.assertRaises(UnsafePathError):
            search_inbox(vault=alias, query=InboxSearchQuery())

    def test_05_vault_external_note_is_not_searched(self) -> None:
        (Path(self.temp.name) / "external.md").write_text("# External", encoding="utf-8")
        self.assertEqual(self.result().total_matches, 0)

    def test_06_candidate_limit_stops_without_partial_results(self) -> None:
        self.write_note("a.md")
        self.write_note("b.md")
        with self.assertRaisesRegex(ValueError, "candidate limit exceeded"):
            search_inbox(vault=self.vault, query=InboxSearchQuery(), max_candidates=1)

    def test_07_search_does_not_modify_notes(self) -> None:
        note = self.write_note("unchanged.md")
        before = hashlib.sha256(note.read_bytes()).hexdigest()
        self.result()
        self.assertEqual(hashlib.sha256(note.read_bytes()).hexdigest(), before)

    def test_08_source_notes_are_not_searchable(self) -> None:
        self.write_note("body.md")
        self.assertEqual(self.result(keyword="SOURCE-NOTES-ONLY-SECRET").total_matches, 0)

    def test_09_summary_is_not_searchable(self) -> None:
        self.write_note("summary.md")
        self.assertEqual(self.result(keyword="SUMMARY-ONLY-SECRET").total_matches, 0)

    def test_09b_malformed_body_before_metadata_is_not_read_for_search(self) -> None:
        path = self.vault / "00_Inbox" / "body-first.md"
        path.write_text(
            "# Body First\n\nBODY-BEFORE-METADATA-SECRET\n\n"
            "## Metadata\n\n- Related Project: Should Not Be Read\n",
            encoding="utf-8",
        )
        self.assertEqual(
            self.result(keyword="BODY-BEFORE-METADATA-SECRET").total_matches,
            0,
        )

    def test_10_text_output_has_no_absolute_vault_path(self) -> None:
        self.write_note("safe.md")
        self.assertNotIn(str(self.vault), format_search_text(self.result()))

    def test_11_private_word_in_title_is_not_a_path_block(self) -> None:
        self.write_note("ordinary.md", "Private research label")
        self.assertEqual(self.result(title="private").total_matches, 1)

    def test_12_legacy_p0_note_is_searchable(self) -> None:
        path = self.vault / "00_Inbox" / "legacy.md"
        path.write_text(
            "# Legacy\n\n## Metadata\n\n- Created: 2026-07-01\n"
            "- Suggested Category: 資源\n\n## Source Notes\n\nprivate body",
            encoding="utf-8",
        )
        self.assertEqual(self.result(title="legacy").total_matches, 1)

    def test_13_p1a_note_is_searchable(self) -> None:
        self.write_note("p1a.md", "P1A", **{"Duplicate Status": "exact_duplicate_suggested"})
        self.assertEqual(
            self.result(duplicate_statuses=("exact_duplicate_suggested",)).total_matches,
            1,
        )

    def test_14_missing_h1_uses_filename(self) -> None:
        path = self.vault / "00_Inbox" / "fallback-title.md"
        path.write_text("## Metadata\n\n- Created: 2026-07-26\n", encoding="utf-8")
        result = self.result()
        self.assertEqual(result.records[0].title, "fallback-title")
        self.assertTrue(result.diagnostics)

    def test_15_missing_metadata_does_not_crash(self) -> None:
        (self.vault / "00_Inbox" / "missing.md").write_text("# Missing\n", encoding="utf-8")
        result = self.result()
        self.assertEqual(result.total_matches, 1)
        self.assertEqual(result.records[0].title, "Missing")
        self.assertIn("missing or empty Metadata", " ".join(result.diagnostics))

    def test_16_invalid_created_is_missing_with_diagnostic(self) -> None:
        self.write_note("bad-created.md", **{"Created": "26/07/2026"})
        result = self.result()
        self.assertIsNone(result.records[0].created)
        self.assertIn("invalid Created", " ".join(result.diagnostics))

    def test_17_invalid_deadline_is_missing_with_diagnostic(self) -> None:
        self.write_note("bad-deadline.md", **{"Deadline": "tomorrow"})
        result = self.result()
        self.assertIsNone(result.records[0].deadline)
        self.assertIn("invalid Deadline", " ".join(result.diagnostics))

    def test_18_malformed_note_does_not_block_valid_result(self) -> None:
        (self.vault / "00_Inbox" / "bad.md").write_text("# Bad", encoding="utf-8")
        self.write_note("good.md", "Good")
        self.assertEqual(self.result(title="good").total_matches, 1)

    def test_19_diagnostic_output_is_capped(self) -> None:
        for index in range(22):
            (self.vault / "00_Inbox" / f"bad-{index}.md").write_text("# Bad", encoding="utf-8")
        diagnostics = format_search_diagnostics(self.result())
        self.assertEqual(len(diagnostics), 21)
        self.assertIn("suppressed: 2", diagnostics[-1])

    def test_20_title_substring_is_case_insensitive(self) -> None:
        self.write_note("aws.md", "AWS Onboarding")
        self.assertEqual(self.result(title="aws onboard").total_matches, 1)

    def test_21_keyword_searches_title(self) -> None:
        self.write_note("title.md", "AWS Guide")
        self.assertEqual(self.result(keyword="aws").total_matches, 1)

    def test_22_keyword_searches_allowed_metadata(self) -> None:
        self.write_note("project.md", **{"Related Project": "14_New_Role_90_Day"})
        self.assertEqual(self.result(keyword="new_role").total_matches, 1)

    def test_23_keyword_does_not_search_source_url(self) -> None:
        self.write_note("url.md")
        self.assertEqual(self.result(keyword="secret.example").total_matches, 0)

    def test_24_keyword_does_not_search_local_file(self) -> None:
        self.write_note("file.md")
        self.assertEqual(self.result(keyword="/private/source").total_matches, 0)

    def test_25_single_category_filter(self) -> None:
        self.write_note("resource.md", **{"Suggested Category": "資源"})
        self.assertEqual(self.result(categories=("資源",)).total_matches, 1)

    def test_26_multiple_categories_use_or(self) -> None:
        self.write_note("important.md", **{"Suggested Category": "重要知識"})
        self.write_note("resource.md", **{"Suggested Category": "資源"})
        self.assertEqual(self.result(categories=("重要知識", "資源")).total_matches, 2)

    def test_27_different_fields_use_and(self) -> None:
        self.write_note(
            "match.md",
            **{"Suggested Category": "資源", "Related Project": "New Role"},
        )
        self.write_note("category-only.md", **{"Suggested Category": "資源"})
        self.assertEqual(
            self.result(categories=("資源",), related_project="new role").total_matches,
            1,
        )

    def test_28_created_from_is_inclusive(self) -> None:
        self.write_note("date.md", **{"Created": "2026-07-01"})
        self.assertEqual(
            self.result(created_from=date(2026, 7, 1)).total_matches,
            1,
        )

    def test_29_created_to_is_inclusive(self) -> None:
        self.write_note("date.md", **{"Created": "2026-07-31T23:00:00+08:00"})
        self.assertEqual(self.result(created_to=date(2026, 7, 31)).total_matches, 1)

    def test_30_invalid_filter_date_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "ISO date"):
            parse_filter_date("07/31/2026", "--created-to")

    def test_31_reversed_date_range_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "start date"):
            self.result(created_from=date(2026, 8, 1), created_to=date(2026, 7, 1))

    def test_32_deadline_range_is_inclusive(self) -> None:
        self.write_note("deadline.md", **{"Deadline": "2026-08-31"})
        self.assertEqual(
            self.result(
                deadline_from=date(2026, 8, 31),
                deadline_to=date(2026, 8, 31),
            ).total_matches,
            1,
        )

    def test_33_has_deadline(self) -> None:
        self.write_note("with.md", **{"Deadline": "2026-08-31"})
        self.write_note("without.md")
        self.assertEqual(self.result(has_deadline=True).total_matches, 1)

    def test_34_missing_deadline(self) -> None:
        self.write_note("with.md", **{"Deadline": "2026-08-31"})
        self.write_note("without.md")
        self.assertEqual(self.result(missing_deadline=True).total_matches, 1)

    def test_35_related_project_substring(self) -> None:
        self.write_note("project.md", **{"Related Project": "14_New_Role_90_Day"})
        self.assertEqual(self.result(related_project="new_role").total_matches, 1)

    def test_36_related_area_substring(self) -> None:
        self.write_note("area.md", **{"Related Area": "New Role"})
        self.assertEqual(self.result(related_area="new role").total_matches, 1)

    def test_37_multiple_source_types_use_or(self) -> None:
        self.write_note("text.md", **{"Source Type": "text"})
        self.write_note("url.md", **{"Source Type": "url"})
        self.assertEqual(self.result(source_types=("text", "url")).total_matches, 2)

    def test_38_file_type_is_case_insensitive_exact(self) -> None:
        self.write_note("pdf.md", **{"File Type": "application/pdf"})
        self.assertEqual(self.result(file_types=("APPLICATION/PDF",)).total_matches, 1)

    def test_39_file_type_does_not_use_substring(self) -> None:
        self.write_note("pdf.md", **{"File Type": "application/pdf"})
        self.assertEqual(self.result(file_types=("pdf",)).total_matches, 0)

    def test_40_processing_status_filter(self) -> None:
        self.write_note("audio.md", **{"Processing Status": "awaiting_transcription"})
        self.assertEqual(
            self.result(processing_statuses=("AWAITING_TRANSCRIPTION",)).total_matches,
            1,
        )

    def test_41_duplicate_status_filter(self) -> None:
        self.write_note("dup.md", **{"Duplicate Status": "exact_duplicate_suggested"})
        self.assertEqual(
            self.result(duplicate_statuses=("exact_duplicate_suggested",)).total_matches,
            1,
        )

    def test_42_has_action(self) -> None:
        self.write_note("action.md", **{"Action Required": "Discuss with manager"})
        self.write_note("none.md")
        self.assertEqual(self.result(has_action=True).total_matches, 1)

    def test_43_missing_action(self) -> None:
        self.write_note("action.md", **{"Action Required": "Discuss"})
        self.write_note("none.md")
        self.assertEqual(self.result(missing_action=True).total_matches, 1)

    def test_44_zero_results_is_successful(self) -> None:
        self.write_note("note.md")
        self.assertEqual(self.result(title="not present").total_matches, 0)

    def record(
        self,
        path: str,
        title: str,
        created: object = date(2026, 7, 1),
        deadline: object = None,
    ) -> InboxSearchRecord:
        return InboxSearchRecord(
            title,
            created,
            "",
            deadline,
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            path,
        )

    def test_45_created_desc_is_default_with_missing_last(self) -> None:
        self.write_note("old.md", "Old", **{"Created": "2026-07-01"})
        self.write_note("new.md", "New", **{"Created": "2026-07-02"})
        self.write_note("missing.md", "Missing", **{"Created": ""})
        self.assertEqual([r.title for r in self.result().records], ["New", "Old", "Missing"])

    def test_46_created_ascending(self) -> None:
        records = [self.record("b", "B", date(2026, 7, 2)), self.record("a", "A")]
        self.assertEqual([r.title for r in sort_search_records(records, "created-asc")], ["A", "B"])

    def test_47_deadline_ascending_missing_last(self) -> None:
        records = [
            self.record("b", "B", deadline=None),
            self.record("a", "A", deadline=date(2026, 8, 1)),
        ]
        self.assertEqual([r.title for r in sort_search_records(records, "deadline-asc")], ["A", "B"])

    def test_48_deadline_descending_missing_last(self) -> None:
        records = [
            self.record("c", "C", deadline=None),
            self.record("a", "A", deadline=date(2026, 8, 1)),
            self.record("b", "B", deadline=date(2026, 9, 1)),
        ]
        self.assertEqual(
            [r.title for r in sort_search_records(records, "deadline-desc")],
            ["B", "A", "C"],
        )

    def test_49_title_ascending(self) -> None:
        records = [self.record("b", "beta"), self.record("a", "Alpha")]
        self.assertEqual([r.title for r in sort_search_records(records, "title-asc")], ["Alpha", "beta"])

    def test_50_title_descending(self) -> None:
        records = [self.record("b", "beta"), self.record("a", "Alpha")]
        self.assertEqual([r.title for r in sort_search_records(records, "title-desc")], ["beta", "Alpha"])

    def test_51_tie_breaker_is_relative_path_ascending(self) -> None:
        records = [self.record("z.md", "Same"), self.record("a.md", "Same")]
        self.assertEqual(
            [r.relative_path for r in sort_search_records(records, "title-asc")],
            ["a.md", "z.md"],
        )

    def test_52_default_limit_is_50(self) -> None:
        for index in range(51):
            self.write_note(f"{index:02}.md")
        result = self.result()
        self.assertEqual(result.total_matches, 51)
        self.assertEqual(len(result.records), 50)

    def test_53_custom_limit_and_invalid_limit(self) -> None:
        self.write_note("a.md")
        self.write_note("b.md")
        self.assertEqual(len(self.result(limit=1).records), 1)
        with self.assertRaisesRegex(ValueError, "between 1 and 200"):
            self.result(limit=201)

    def test_54_text_output_contains_only_permitted_record_fields(self) -> None:
        self.write_note("safe.md", "Safe")
        output = format_search_text(self.result())
        self.assertIn("Path: 00_Inbox/safe.md", output)
        self.assertNotIn("secret.example", output)
        self.assertNotIn("Content Hash", output)

    def test_55_json_is_valid_and_excludes_sensitive_fields(self) -> None:
        self.write_note("safe.md", "安全")
        output = format_search_json(self.result())
        payload = json.loads(output)
        self.assertEqual(payload["returned"], 1)
        self.assertEqual(payload["results"][0]["title"], "安全")
        for forbidden in ("Source URL", "Local File", "Content Hash", str(self.vault)):
            self.assertNotIn(forbidden, output)

    def test_56_cli_json_keeps_diagnostics_on_stderr(self) -> None:
        (self.vault / "00_Inbox" / "bad.md").write_text("# Bad", encoding="utf-8")
        stdout = StringIO()
        stderr = StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = main(["search", "--vault", str(self.vault), "--format", "json"])
        self.assertEqual(exit_code, 0)
        json.loads(stdout.getvalue())
        self.assertIn("WARNING:", stderr.getvalue())
        self.assertNotIn("WARNING:", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
