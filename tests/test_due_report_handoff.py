from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import date
from io import StringIO
from pathlib import Path

from business_knowledge_capture.cli import build_parser, main
from business_knowledge_capture.core import generate_progress_report, initialize_vault
from business_knowledge_capture.date_review import (
    DateReviewQuery,
    format_due_json,
    format_due_text,
    review_due_dates,
)
from business_knowledge_capture.due_selection import (
    DueSelection,
    parse_due_selection,
    validate_due_selections,
)


class DueReportHandoffTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.vault = self.root / "vault"
        (self.vault / "00_Inbox").mkdir(parents=True)
        (self.vault / "10_Work" / "11_Projects").mkdir(parents=True)
        (self.vault / "90_System").mkdir()
        initialize_vault(self.vault)
        self.as_of = date(2026, 8, 1)

    def tearDown(self) -> None:
        self.temp.cleanup()

    @property
    def reports_dir(self) -> Path:
        return (
            self.vault
            / "10_Work"
            / "11_Projects"
            / "14_New_Role_90_Day"
            / "03_Progress_Reports"
        )

    def write_note(
        self,
        name: str = "note.md",
        title: str = "Public AI Course",
        **overrides: str,
    ) -> Path:
        metadata = {
            "Source Type": "text",
            "Source URL": "https://secret.example/private",
            "Local File": "/private/source/file.pdf",
            "External File Link": "https://drive.example/private",
            "Suggested Category": "資源",
            "Action Required": "Submit application documents",
            "Deadline": "2026-08-15",
            "Resource Expiry": "2026-08-31",
            "Reminder Date": "2026-08-08",
            "Reminder Note": "Review documents one week before deadline",
            "Related Project": "14_New_Role_90_Day",
            "Related Area": "New Role",
            "Content Hash": "a" * 64,
        }
        metadata.update(overrides)
        body = "\n".join(f"- {key}: {value}" for key, value in metadata.items())
        path = self.vault / "00_Inbox" / name
        path.write_text(
            f"# {title}\n\n## Metadata\n\n{body}\n\n"
            "## One-line Summary\n\nBODY-SUMMARY-SECRET\n\n"
            "## Suggested Actions\n\nBODY-ACTION-SECRET\n\n"
            "## Source Notes\n\nBODY-SOURCE-NOTES-SECRET\n",
            encoding="utf-8",
        )
        return path

    def key(
        self,
        event_type: str = "deadline",
        event_date: str = "2026-08-15",
        name: str = "note.md",
    ) -> str:
        return f"{event_type}::{event_date}::00_Inbox/{name}"

    def selected(self, *values: str, window_days: int = 14):
        return validate_due_selections(
            vault=self.vault,
            values=values,
            as_of=self.as_of,
            window_days=window_days,
        )

    def create_report(self, *values: str, report_type: str = "daily") -> Path:
        selected = self.selected(*values)
        return generate_progress_report(
            vault=self.vault,
            completed_paths=[],
            in_progress_paths=[],
            period_label="2026-08-01",
            report_type=report_type,
            commitments=["Continue implementation."],
            due_events=selected.events,
        )

    def test_01_deadline_selection_key_generation(self) -> None:
        self.write_note()
        event = review_due_dates(
            vault=self.vault,
            query=DateReviewQuery(as_of=self.as_of, include_upcoming=True),
        ).events[1]
        self.assertEqual(event.selection_key, self.key())

    def test_02_resource_expiry_selection_key_generation(self) -> None:
        self.write_note()
        events = review_due_dates(
            vault=self.vault,
            query=DateReviewQuery(as_of=self.as_of, include_upcoming=True),
        ).events
        self.assertEqual(events[2].selection_key, self.key("resource_expiry", "2026-08-31"))

    def test_03_reminder_selection_key_generation(self) -> None:
        self.write_note()
        events = review_due_dates(
            vault=self.vault,
            query=DateReviewQuery(as_of=self.as_of, include_upcoming=True),
        ).events
        self.assertEqual(events[0].selection_key, self.key("reminder", "2026-08-08"))

    def test_04_due_text_contains_selection_key(self) -> None:
        self.write_note()
        result = review_due_dates(
            vault=self.vault,
            query=DateReviewQuery(as_of=self.as_of),
        )
        self.assertIn(f"Selection Key: {self.key()}", format_due_text(result))

    def test_05_due_json_contains_selection_key(self) -> None:
        self.write_note()
        result = review_due_dates(
            vault=self.vault,
            query=DateReviewQuery(as_of=self.as_of),
        )
        self.assertEqual(
            json.loads(format_due_json(result))["results"][1]["selection_key"],
            self.key(),
        )

    def test_06_due_json_excludes_absolute_path(self) -> None:
        self.write_note()
        result = review_due_dates(
            vault=self.vault,
            query=DateReviewQuery(as_of=self.as_of),
        )
        self.assertNotIn(str(self.vault), format_due_json(result))

    def test_07_invalid_selection_format_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Invalid due selection format"):
            parse_due_selection("deadline::2026-08-15")

    def test_08_invalid_event_type_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported due event type"):
            parse_due_selection("calendar::2026-08-15::00_Inbox/note.md")

    def test_09_invalid_selection_date_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "YYYY-MM-DD"):
            parse_due_selection("deadline::15/08/2026::00_Inbox/note.md")

    def test_09b_path_with_extra_separator_is_preserved(self) -> None:
        selection = parse_due_selection(
            "deadline::2026-08-15::00_Inbox/note::revision.md"
        )
        self.assertEqual(
            selection.relative_path,
            "00_Inbox/note::revision.md",
        )

    def test_10_absolute_selection_path_rejected(self) -> None:
        selection = f"deadline::2026-08-15::{self.vault}/00_Inbox/note.md"
        with self.assertRaisesRegex(ValueError, "Vault-relative"):
            self.selected(selection)

    def test_11_traversal_selection_path_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "traversal"):
            self.selected("deadline::2026-08-15::00_Inbox/../note.md")

    def test_12_nested_inbox_path_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "direct Inbox"):
            self.selected("deadline::2026-08-15::00_Inbox/nested/note.md")

    def test_13_vault_external_note_is_rejected(self) -> None:
        outside = self.root / "outside.md"
        outside.write_text("# Outside", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Vault-relative"):
            self.selected(f"deadline::2026-08-15::{outside}")

    def test_14_protected_path_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "protected-path"):
            self.selected("deadline::2026-08-15::Private/note.md")

    def test_15_symlink_note_is_rejected(self) -> None:
        target = self.root / "outside.md"
        target.write_text("# Outside", encoding="utf-8")
        (self.vault / "00_Inbox" / "link.md").symlink_to(target)
        with self.assertRaisesRegex(ValueError, "symbolic link"):
            self.selected(self.key(name="link.md"))

    def test_16_symlink_ancestor_is_rejected(self) -> None:
        alias = self.root / "vault-alias"
        alias.symlink_to(self.vault, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symbolic link"):
            validate_due_selections(
                vault=alias,
                values=(self.key(),),
                as_of=self.as_of,
                window_days=14,
            )

    def test_17_non_markdown_file_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "not a regular Markdown"):
            self.selected("deadline::2026-08-15::00_Inbox/note.txt")

    def test_18_missing_note_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "no longer exists"):
            self.selected(self.key())

    def test_19_due_selection_reader_excludes_source_notes(self) -> None:
        self.write_note()
        body = self.create_report(self.key()).read_text(encoding="utf-8")
        self.assertNotIn("BODY-SOURCE-NOTES-SECRET", body)

    def test_20_report_output_excludes_absolute_path(self) -> None:
        self.write_note()
        body = self.create_report(self.key()).read_text(encoding="utf-8")
        self.assertNotIn(str(self.vault), body)

    def test_21_matching_deadline_is_valid(self) -> None:
        self.write_note()
        self.assertEqual(self.selected(self.key()).events[0].event_type, "deadline")

    def test_22_changed_deadline_is_stale(self) -> None:
        self.write_note(Deadline="2026-08-20")
        with self.assertRaisesRegex(ValueError, "stale"):
            self.selected(self.key())

    def test_23_cleared_deadline_is_stale(self) -> None:
        self.write_note(Deadline="")
        with self.assertRaisesRegex(ValueError, "deadline no longer exists"):
            self.selected(self.key())

    def test_24_changed_resource_expiry_is_stale(self) -> None:
        self.write_note(**{"Resource Expiry": "2026-09-01"})
        with self.assertRaisesRegex(ValueError, "stale"):
            self.selected(self.key("resource_expiry", "2026-08-31"))

    def test_25_changed_reminder_is_stale(self) -> None:
        self.write_note(**{"Reminder Date": "2026-08-09"})
        with self.assertRaisesRegex(ValueError, "stale"):
            self.selected(self.key("reminder", "2026-08-08"))

    def test_26_stale_selection_creates_no_report(self) -> None:
        self.write_note(Deadline="2026-08-20")
        before = tuple(self.reports_dir.glob("*.md"))
        with self.assertRaises(ValueError):
            self.selected(self.key())
        self.assertEqual(tuple(self.reports_dir.glob("*.md")), before)

    def test_27_one_stale_of_multiple_creates_no_report(self) -> None:
        self.write_note()
        values = (self.key("reminder", "2026-08-08"), self.key("deadline", "2026-08-16"))
        before = tuple(self.reports_dir.glob("*.md"))
        with self.assertRaises(ValueError):
            self.selected(*values)
        self.assertEqual(tuple(self.reports_dir.glob("*.md")), before)

    def test_28_deadline_enters_report(self) -> None:
        self.write_note()
        self.assertIn("— Deadline —", self.create_report(self.key()).read_text(encoding="utf-8"))

    def test_29_resource_expiry_enters_report(self) -> None:
        self.write_note()
        body = self.create_report(
            self.key("resource_expiry", "2026-08-31")
        ).read_text(encoding="utf-8")
        self.assertIn("— Resource Expiry —", body)

    def test_30_reminder_enters_report(self) -> None:
        self.write_note()
        body = self.create_report(
            self.key("reminder", "2026-08-08")
        ).read_text(encoding="utf-8")
        self.assertIn("— Reminder —", body)

    def test_31_same_note_three_events_are_preserved(self) -> None:
        self.write_note()
        body = self.create_report(
            self.key("reminder", "2026-08-08"),
            self.key(),
            self.key("resource_expiry", "2026-08-31"),
        ).read_text(encoding="utf-8")
        self.assertEqual(body.count("Source Note: `00_Inbox/note.md`"), 3)

    def test_32_duplicate_selection_is_displayed_once(self) -> None:
        self.write_note()
        selected = self.selected(self.key(), self.key())
        self.assertEqual(len(selected.events), 1)
        self.assertEqual(len(selected.diagnostics), 1)

    def test_33_different_events_are_not_duplicates(self) -> None:
        self.write_note()
        selected = self.selected(
            self.key(),
            self.key("reminder", "2026-08-08"),
        )
        self.assertEqual(len(selected.events), 2)

    def test_34_more_than_fifty_selections_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "maximum 50"):
            self.selected(*(self.key() for _ in range(51)))

    def test_35_explicit_upcoming_event_enters_report(self) -> None:
        self.write_note()
        body = self.create_report(
            self.key("resource_expiry", "2026-08-31")
        ).read_text(encoding="utf-8")
        self.assertIn("- Status: upcoming", body)

    def test_36_overdue_uses_days_overdue(self) -> None:
        self.write_note(Deadline="2026-07-20")
        body = self.create_report(
            self.key("deadline", "2026-07-20")
        ).read_text(encoding="utf-8")
        self.assertIn("- Days Overdue: 12", body)
        self.assertNotIn("Days Until: -12", body)

    def test_37_due_today_status(self) -> None:
        self.write_note(Deadline="2026-08-01")
        body = self.create_report(
            self.key("deadline", "2026-08-01")
        ).read_text(encoding="utf-8")
        self.assertIn("- Status: due_today", body)
        self.assertIn("- Days Until: 0", body)

    def test_38_due_soon_status(self) -> None:
        self.write_note()
        body = self.create_report(self.key()).read_text(encoding="utf-8")
        self.assertIn("- Status: due_soon", body)
        self.assertIn("- Days Until: 14", body)

    def test_39_as_of_calculation_is_deterministic(self) -> None:
        self.write_note()
        first = self.selected(self.key()).events[0]
        second = self.selected(self.key()).events[0]
        self.assertEqual((first.days_until, first.status), (second.days_until, second.status))

    def test_40_custom_window_changes_status(self) -> None:
        self.write_note()
        event = self.selected(self.key(), window_days=7).events[0]
        self.assertEqual(event.status, "upcoming")

    def test_41_report_sorts_by_date_ascending(self) -> None:
        self.write_note()
        body = self.create_report(
            self.key("resource_expiry", "2026-08-31"),
            self.key(),
            self.key("reminder", "2026-08-08"),
        ).read_text(encoding="utf-8")
        self.assertLess(body.index("2026-08-08 —"), body.index("2026-08-15 —"))
        self.assertLess(body.index("2026-08-15 —"), body.index("2026-08-31 —"))

    def test_42_report_event_type_tie_breaker(self) -> None:
        self.write_note(
            Deadline="2026-08-08",
            **{"Resource Expiry": "2026-08-08", "Reminder Date": "2026-08-08"},
        )
        body = self.create_report(
            self.key("resource_expiry", "2026-08-08"),
            self.key("deadline", "2026-08-08"),
            self.key("reminder", "2026-08-08"),
        ).read_text(encoding="utf-8")
        self.assertLess(body.index("— Reminder —"), body.index("— Deadline —"))
        self.assertLess(body.index("— Deadline —"), body.index("— Resource Expiry —"))

    def test_43_report_title_tie_breaker(self) -> None:
        self.write_note("b.md", "beta", Deadline="2026-08-15")
        self.write_note("a.md", "Alpha", Deadline="2026-08-15")
        selected = self.selected(self.key(name="b.md"), self.key(name="a.md"))
        self.assertEqual([event.title for event in selected.events], ["Alpha", "beta"])

    def test_44_report_relative_path_tie_breaker(self) -> None:
        self.write_note("b.md", "Same", Deadline="2026-08-15")
        self.write_note("a.md", "Same", Deadline="2026-08-15")
        selected = self.selected(self.key(name="b.md"), self.key(name="a.md"))
        self.assertEqual(
            [event.relative_path for event in selected.events],
            ["00_Inbox/a.md", "00_Inbox/b.md"],
        )

    def test_45_date_review_section_exists(self) -> None:
        self.write_note()
        self.assertIn("## Date Review", self.create_report(self.key()).read_text(encoding="utf-8"))

    def test_46_no_selection_has_no_date_review_section(self) -> None:
        report = generate_progress_report(
            vault=self.vault,
            completed_paths=[],
            in_progress_paths=[],
            period_label="2026-08-01",
            report_type="daily",
        )
        self.assertNotIn("## Date Review", report.read_text(encoding="utf-8"))

    def test_47_source_note_is_relative(self) -> None:
        self.write_note()
        body = self.create_report(self.key()).read_text(encoding="utf-8")
        self.assertIn("- Source Note: `00_Inbox/note.md`", body)

    def test_48_reminder_note_only_on_reminder(self) -> None:
        self.write_note()
        deadline_body = self.create_report(self.key()).read_text(encoding="utf-8")
        reminder_body = self.create_report(
            self.key("reminder", "2026-08-08")
        ).read_text(encoding="utf-8")
        self.assertNotIn("- Reminder Note:", deadline_body)
        self.assertIn("- Reminder Note:", reminder_body)

    def test_49_missing_optional_metadata_does_not_crash(self) -> None:
        self.write_note(
            **{
                "Action Required": "",
                "Reminder Note": "",
                "Related Project": "",
                "Related Area": "",
            },
        )
        self.assertTrue(self.create_report(self.key()).is_file())

    def test_50_unicode_title_is_preserved(self) -> None:
        self.write_note(title="公開人工智能課程")
        body = self.create_report(self.key()).read_text(encoding="utf-8")
        self.assertIn("公開人工智能課程", body)

    def test_51_invalid_cli_selection_creates_no_report(self) -> None:
        before = tuple(self.reports_dir.glob("*.md"))
        stderr = StringIO()
        with redirect_stderr(stderr):
            code = main(
                [
                    "report",
                    "--vault",
                    str(self.vault),
                    "--type",
                    "daily",
                    "--period",
                    "2026-08-01",
                    "--due-selection",
                    "invalid",
                ]
            )
        self.assertEqual(code, 2)
        self.assertEqual(tuple(self.reports_dir.glob("*.md")), before)

    def test_52_partial_validation_failure_creates_no_report(self) -> None:
        self.write_note()
        before = tuple(self.reports_dir.glob("*.md"))
        with self.assertRaises(ValueError):
            self.selected(self.key(), self.key("deadline", "2026-08-16"))
        self.assertEqual(tuple(self.reports_dir.glob("*.md")), before)

    def test_53_selected_note_is_not_modified(self) -> None:
        note = self.write_note()
        before = hashlib.sha256(note.read_bytes()).hexdigest()
        self.create_report(self.key())
        self.assertEqual(hashlib.sha256(note.read_bytes()).hexdigest(), before)

    def test_54_due_command_remains_read_only(self) -> None:
        note = self.write_note()
        before = hashlib.sha256(note.read_bytes()).hexdigest()
        main(["due", "--vault", str(self.vault), "--as-of", "2026-08-01"])
        self.assertEqual(hashlib.sha256(note.read_bytes()).hexdigest(), before)

    def test_55_existing_daily_report_workflow_passes(self) -> None:
        note = self.write_note()
        report = generate_progress_report(
            vault=self.vault,
            completed_paths=[note],
            in_progress_paths=[],
            period_label="2026-08-01",
            report_type="daily",
        )
        self.assertIn("Public AI Course", report.read_text(encoding="utf-8"))

    def test_56_existing_weekly_report_workflow_passes(self) -> None:
        note = self.write_note()
        report = generate_progress_report(
            vault=self.vault,
            completed_paths=[],
            in_progress_paths=[note],
            period_label="2026-W31",
            report_type="weekly",
            commitments=["Continue implementation."],
        )
        self.assertIn("Continue implementation.", report.read_text(encoding="utf-8"))

    def test_57_report_write_leaves_no_temporary_file(self) -> None:
        self.write_note()
        self.create_report(self.key())
        self.assertEqual(list(self.reports_dir.glob("*.tmp")), [])

    def test_58_due_regression_returns_three_events(self) -> None:
        self.write_note()
        result = review_due_dates(
            vault=self.vault,
            query=DateReviewQuery(as_of=self.as_of, include_upcoming=True),
        )
        self.assertEqual(result.total_events, 3)

    def test_59_python_39_compatible_selection_import(self) -> None:
        selection = DueSelection("deadline", date(2026, 8, 15), "00_Inbox/note.md")
        self.assertEqual(selection.selection_key, self.key())

    def test_60_cli_help_exposes_due_handoff_arguments(self) -> None:
        parser = build_parser()
        args = parser.parse_args(
            [
                "report",
                "--vault",
                str(self.vault),
                "--type",
                "daily",
                "--period",
                "2026-08-01",
                "--as-of",
                "2026-08-01",
                "--window-days",
                "14",
                "--due-selection",
                self.key(),
            ]
        )
        self.assertEqual(args.due_selection, [self.key()])


if __name__ == "__main__":
    unittest.main()
