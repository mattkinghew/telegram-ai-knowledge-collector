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
from business_knowledge_capture.core import (
    DisabledSummarizer,
    ExtractedSource,
    create_inbox_note,
    initialize_vault,
    review_note,
)
from business_knowledge_capture.date_review import (
    DateReviewEvent,
    DateReviewQuery,
    calculate_date_status,
    format_date_diagnostics,
    format_due_json,
    format_due_text,
    review_due_dates,
    sort_date_events,
)
from business_knowledge_capture.search import InboxSearchQuery, search_inbox


class DateReviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.vault = self.root / "vault"
        (self.vault / "00_Inbox").mkdir(parents=True)
        (self.vault / "10_Work" / "11_Projects").mkdir(parents=True)
        (self.vault / "90_System").mkdir()
        initialize_vault(self.vault)
        self.as_of = date(2026, 7, 26)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_note(self, name: str, title: str = "Note", **overrides: str) -> Path:
        metadata = {
            "Created": "2026-07-26T12:00:00+08:00",
            "Source Type": "text",
            "Source URL": "https://secret.example/private",
            "Local File": "/private/source/file.pdf",
            "External File Link": "https://drive.example/private",
            "Processing Status": "registered",
            "Suggested Category": "資源",
            "Action Required": "Review",
            "Deadline": "",
            "Resource Expiry": "",
            "Reminder Date": "",
            "Reminder Note": "",
            "Related Project": "14_New_Role_90_Day",
            "Related Area": "New Role",
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
            "## Source Notes\n\nBODY-ONLY-SECRET\n\n"
            "## Manual Review\n\n- [ ] Summary reviewed\n",
            encoding="utf-8",
        )
        return path

    def query(self, **values: object):
        return review_due_dates(
            vault=self.vault,
            query=DateReviewQuery(as_of=self.as_of, **values),
        )

    def test_capture_schema_and_valid_date_fields(self) -> None:
        note = create_inbox_note(
            vault=self.vault,
            source=ExtractedSource(source_type="text", readable_text="Example"),
            title="Captured",
            summarizer=DisabledSummarizer(),
            deadline="2026-08-31",
            resource_expiry="2026-09-15",
            reminder_date="2026-08-24",
            reminder_note="Review documents",
        )
        text = note.read_text(encoding="utf-8")
        self.assertIn("- Deadline: 2026-08-31", text)
        self.assertIn("- Resource Expiry: 2026-09-15", text)
        self.assertIn("- Reminder Date: 2026-08-24", text)
        self.assertIn("- Reminder Note: Review documents", text)
        self.assertIn("- [ ] Date and reminder fields reviewed", text)

    def test_capture_invalid_dates_are_rejected_without_note(self) -> None:
        before = tuple((self.vault / "00_Inbox").iterdir())
        for field, value in (
            ("deadline", "31/08/2026"),
            ("resource_expiry", "next Friday"),
            ("reminder_date", "2026-02-30"),
        ):
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    create_inbox_note(
                        vault=self.vault,
                        source=ExtractedSource(
                            source_type="text", readable_text="Example"
                        ),
                        **{field: value},
                    )
                self.assertEqual(tuple((self.vault / "00_Inbox").iterdir()), before)

    def test_capture_cli_validates_before_creating_note(self) -> None:
        stderr = StringIO()
        with redirect_stderr(stderr):
            code = main(
                [
                    "capture",
                    "--vault",
                    str(self.vault),
                    "--text",
                    "Example",
                    "--deadline",
                    "tomorrow",
                ]
            )
        self.assertEqual(code, 2)
        self.assertIn("YYYY-MM-DD", stderr.getvalue())
        self.assertEqual(list((self.vault / "00_Inbox").glob("*.md")), [])

    def test_reminder_note_newline_is_sanitized(self) -> None:
        note = create_inbox_note(
            vault=self.vault,
            source=ExtractedSource(source_type="text", readable_text="Example"),
            reminder_note="Review\n## Injected",
        )
        text = note.read_text(encoding="utf-8")
        self.assertIn("- Reminder Note: Review ## Injected", text)
        self.assertNotIn("\n## Injected", text)

    def test_review_sets_and_clears_dates_atomically(self) -> None:
        note = self.write_note("review.md")
        review_note(
            vault=self.vault,
            note_path=note,
            deadline="2026-08-15",
            resource_expiry="2026-08-31",
            reminder_date="2026-08-08",
            reminder_note="Review first",
        )
        text = note.read_text(encoding="utf-8")
        self.assertIn("- Deadline: 2026-08-15", text)
        self.assertIn("- Resource Expiry: 2026-08-31", text)
        self.assertIn("- Reminder Date: 2026-08-08", text)
        review_note(
            vault=self.vault,
            note_path=note,
            clear_deadline=True,
            clear_resource_expiry=True,
            clear_reminder=True,
        )
        text = note.read_text(encoding="utf-8")
        self.assertIn("- Deadline: \n", text)
        self.assertIn("- Resource Expiry: \n", text)
        self.assertIn("- Reminder Date: \n", text)
        self.assertIn("- Reminder Note: \n", text)

    def test_review_set_clear_conflicts_and_invalid_date_do_not_modify(self) -> None:
        note = self.write_note("atomic.md", **{"Deadline": "2026-08-15"})
        before = note.read_bytes()
        with self.assertRaises(ValueError):
            review_note(
                vault=self.vault,
                note_path=note,
                deadline="2026-08-20",
                clear_deadline=True,
            )
        self.assertEqual(note.read_bytes(), before)
        with self.assertRaises(ValueError):
            review_note(
                vault=self.vault,
                note_path=note,
                deadline="invalid",
                resource_expiry="2026-09-01",
            )
        self.assertEqual(note.read_bytes(), before)
        with self.assertRaises(ValueError):
            review_note(
                vault=self.vault,
                note_path=note,
                reminder_date="2026-08-01",
                clear_reminder=True,
            )
        self.assertEqual(note.read_bytes(), before)

    def test_mark_dates_updates_new_and_old_notes(self) -> None:
        new_note = self.write_note("new.md")
        review_note(vault=self.vault, note_path=new_note, mark=("dates",))
        self.assertIn(
            "- [x] Date and reminder fields reviewed",
            new_note.read_text(encoding="utf-8"),
        )
        old_note = self.vault / "00_Inbox" / "old.md"
        old_note.write_text(
            "# Old\n\n## Metadata\n\n- Deadline:\n- Related Project:\n\n"
            "## Manual Review\n\n- [ ] Summary reviewed\n",
            encoding="utf-8",
        )
        review_note(vault=self.vault, note_path=old_note, mark=("dates",))
        text = old_note.read_text(encoding="utf-8")
        self.assertIn("- [x] Date and reminder fields reviewed", text)
        self.assertIn("- [ ] Summary reviewed", text)

    def test_date_status_boundaries_and_custom_window(self) -> None:
        cases = (
            (date(2026, 7, 20), 14, (-6, "overdue")),
            (date(2026, 7, 26), 14, (0, "due_today")),
            (date(2026, 7, 27), 14, (1, "due_soon")),
            (date(2026, 8, 9), 14, (14, "due_soon")),
            (date(2026, 8, 10), 14, (15, "upcoming")),
            (date(2026, 8, 25), 30, (30, "due_soon")),
        )
        for event_date, window, expected in cases:
            self.assertEqual(
                calculate_date_status(event_date, self.as_of, window), expected
            )

    def test_one_note_creates_three_distinct_events(self) -> None:
        self.write_note(
            "three.md",
            Deadline="2026-07-31",
            **{
                "Resource Expiry": "2026-08-05",
                "Reminder Date": "2026-07-28",
            },
        )
        result = self.query(include_upcoming=True)
        self.assertEqual(
            [event.event_type for event in result.events],
            ["reminder", "deadline", "resource_expiry"],
        )
        self.assertEqual(result.total_events, 3)

    def test_note_without_dates_and_legacy_notes_do_not_crash(self) -> None:
        self.write_note("none.md")
        old = self.vault / "00_Inbox" / "legacy.md"
        old.write_text("# Legacy\n\n## Metadata\n\n- Deadline:\n", encoding="utf-8")
        self.assertEqual(self.query().total_events, 0)

    def test_default_scope_include_upcoming_and_explicit_status(self) -> None:
        self.write_note("soon.md", Deadline="2026-07-31")
        self.write_note("later.md", Deadline="2026-09-30")
        self.assertEqual([e.title for e in self.query().events], ["Note"])
        self.assertEqual(self.query(include_upcoming=True).total_events, 2)
        self.assertEqual(
            self.query(statuses=("upcoming",)).events[0].event_date,
            date(2026, 9, 30),
        )

    def test_same_field_or_and_different_field_and_filters(self) -> None:
        self.write_note(
            "a.md",
            "A",
            Deadline="2026-07-31",
            **{"Related Project": "Alpha", "Suggested Category": "資源"},
        )
        self.write_note(
            "b.md",
            "B",
            **{
                "Reminder Date": "2026-07-28",
                "Related Project": "Beta",
                "Suggested Category": "重要知識",
            },
        )
        result = self.query(
            event_types=("deadline", "reminder"),
            statuses=("due_today", "due_soon"),
        )
        self.assertEqual({event.title for event in result.events}, {"A", "B"})
        self.assertEqual(
            [event.title for event in self.query(
                categories=("資源",), related_project="alp"
            ).events],
            ["A"],
        )
        self.assertEqual(
            [event.title for event in self.query(related_area="new").events],
            ["B", "A"],
        )

    def make_event(
        self,
        title: str,
        event_type: str,
        event_date: date,
        path: str,
    ) -> DateReviewEvent:
        days_until, status = calculate_date_status(event_date, self.as_of, 14)
        return DateReviewEvent(
            event_type,
            event_date,
            days_until,
            status,
            title,
            "",
            "",
            "",
            "",
            "",
            "",
            path,
        )

    def test_all_sort_modes_and_tie_breakers(self) -> None:
        events = [
            self.make_event("B", "resource_expiry", date(2026, 8, 1), "z.md"),
            self.make_event("A", "deadline", date(2026, 7, 28), "b.md"),
            self.make_event("A", "reminder", date(2026, 7, 28), "c.md"),
            self.make_event("A", "reminder", date(2026, 7, 28), "a.md"),
        ]
        self.assertEqual(
            [e.event_date for e in sort_date_events(events, "date-asc")],
            sorted(e.event_date for e in events),
        )
        self.assertEqual(
            [e.event_date for e in sort_date_events(events, "date-desc")],
            sorted((e.event_date for e in events), reverse=True),
        )
        self.assertEqual(
            [e.days_until for e in sort_date_events(events, "days-until-asc")],
            sorted(e.days_until for e in events),
        )
        self.assertEqual(sort_date_events(events, "title-asc")[0].title, "A")
        self.assertEqual(sort_date_events(events, "title-desc")[0].title, "B")
        tied = sort_date_events(events[1:], "date-asc")
        self.assertEqual(
            [(e.event_type, e.relative_path) for e in tied],
            [("reminder", "a.md"), ("reminder", "c.md"), ("deadline", "b.md")],
        )

    def test_malformed_dates_skip_only_invalid_fields(self) -> None:
        self.write_note(
            "bad.md",
            Deadline="tomorrow",
            **{
                "Resource Expiry": "2026/08/31",
                "Reminder Date": "2026-07-28",
            },
        )
        result = self.query()
        self.assertEqual([event.event_type for event in result.events], ["reminder"])
        self.assertTrue(any("invalid Deadline" in item for item in result.diagnostics))
        self.assertTrue(
            any("invalid Resource Expiry" in item for item in result.diagnostics)
        )

    def test_diagnostic_limit_and_relationship_warnings(self) -> None:
        for index in range(21):
            self.write_note(f"bad-{index:02}.md", Deadline="bad")
        result = self.query()
        diagnostics = format_date_diagnostics(result)
        self.assertEqual(len(diagnostics), 21)
        self.assertIn("suppressed: 1", diagnostics[-1])
        other = self.root / "relationship-vault"
        (other / "00_Inbox").mkdir(parents=True)
        (other / "10_Work" / "11_Projects").mkdir(parents=True)
        (other / "90_System").mkdir()
        initialize_vault(other)
        self.vault = other
        self.write_note(
            "relation.md",
            Deadline="2026-08-01",
            **{
                "Resource Expiry": "2026-08-02",
                "Reminder Date": "2026-08-03",
            },
        )
        result = self.query(include_upcoming=True)
        self.assertEqual(result.total_events, 3)
        self.assertTrue(any("later than Deadline" in item for item in result.diagnostics))
        self.assertTrue(
            any("later than Resource Expiry" in item for item in result.diagnostics)
        )

    def test_text_output_is_redacted_and_overdue_is_human_readable(self) -> None:
        self.write_note("overdue.md", Deadline="2026-07-20")
        text = format_due_text(self.query())
        self.assertIn("Days Overdue: 6", text)
        self.assertNotIn("Days Until: -6", text)
        self.assertNotIn(str(self.vault), text)
        for forbidden in (
            "secret.example",
            "/private/source",
            "drive.example",
            "a" * 64,
            "BODY-ONLY-SECRET",
        ):
            self.assertNotIn(forbidden, text)

    def test_json_is_valid_allowlisted_and_diagnostics_stay_on_stderr(self) -> None:
        self.write_note(
            "valid.md",
            Deadline="2026-07-31",
            **{"Reminder Note": "Allowed metadata"},
        )
        self.write_note("invalid.md", Deadline="invalid")
        result = self.query()
        payload = json.loads(format_due_json(result))
        self.assertEqual(payload["as_of"], "2026-07-26")
        self.assertEqual(payload["returned"], 1)
        serialized = json.dumps(payload)
        for forbidden in ("source_url", "local_file", "content_hash", str(self.vault)):
            self.assertNotIn(forbidden, serialized)
        stdout, stderr = StringIO(), StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = main(
                [
                    "due",
                    "--vault",
                    str(self.vault),
                    "--as-of",
                    "2026-07-26",
                    "--format",
                    "json",
                ]
            )
        self.assertEqual(code, 0)
        json.loads(stdout.getvalue())
        self.assertIn("invalid Deadline", stderr.getvalue())

    def test_zero_results_limit_and_window_validation(self) -> None:
        self.assertEqual(self.query().total_events, 0)
        for values in ({"limit": 0}, {"limit": 201}, {"window_days": 0}, {"window_days": 366}):
            with self.assertRaises(ValueError):
                self.query(**values)

    def test_candidate_limit_and_nested_note_scope(self) -> None:
        self.write_note("direct.md", Deadline="2026-07-31")
        nested = self.vault / "00_Inbox" / "nested"
        nested.mkdir()
        (nested / "hidden.md").write_text(
            "# Hidden\n\n## Metadata\n\n- Deadline: 2026-07-20\n",
            encoding="utf-8",
        )
        self.assertEqual(self.query().total_events, 1)
        with self.assertRaises(ValueError):
            review_due_dates(
                vault=self.vault,
                query=DateReviewQuery(as_of=self.as_of),
                max_candidates=0,
            )

    def test_due_is_read_only(self) -> None:
        note = self.write_note("readonly.md", Deadline="2026-07-31")
        before = hashlib.sha256(note.read_bytes()).hexdigest()
        self.query()
        after = hashlib.sha256(note.read_bytes()).hexdigest()
        self.assertEqual(before, after)

    def test_search_resource_expiry_and_reminder_filters(self) -> None:
        self.write_note(
            "dated.md",
            "Dated",
            **{
                "Resource Expiry": "2026-08-05",
                "Reminder Date": "2026-07-28",
                "Reminder Note": "Review application requirements",
            },
        )
        self.write_note("missing.md", "Missing")
        self.assertEqual(
            search_inbox(
                vault=self.vault,
                query=InboxSearchQuery(
                    resource_expiry_from=date(2026, 8, 5),
                    resource_expiry_to=date(2026, 8, 5),
                ),
            ).total_matches,
            1,
        )
        self.assertEqual(
            search_inbox(
                vault=self.vault,
                query=InboxSearchQuery(
                    reminder_from=date(2026, 7, 28),
                    reminder_to=date(2026, 7, 28),
                ),
            ).total_matches,
            1,
        )
        self.assertEqual(
            search_inbox(
                vault=self.vault,
                query=InboxSearchQuery(has_resource_expiry=True),
            ).total_matches,
            1,
        )
        self.assertEqual(
            search_inbox(
                vault=self.vault,
                query=InboxSearchQuery(missing_resource_expiry=True),
            ).total_matches,
            1,
        )
        self.assertEqual(
            search_inbox(
                vault=self.vault,
                query=InboxSearchQuery(has_reminder=True),
            ).total_matches,
            1,
        )
        self.assertEqual(
            search_inbox(
                vault=self.vault,
                query=InboxSearchQuery(missing_reminder=True),
            ).total_matches,
            1,
        )
        self.assertEqual(
            search_inbox(
                vault=self.vault,
                query=InboxSearchQuery(keyword="application requirements"),
            ).records[0].title,
            "Dated",
        )

    def test_search_presence_pairs_are_mutually_exclusive(self) -> None:
        for query in (
            InboxSearchQuery(
                has_resource_expiry=True, missing_resource_expiry=True
            ),
            InboxSearchQuery(has_reminder=True, missing_reminder=True),
        ):
            with self.assertRaises(ValueError):
                search_inbox(vault=self.vault, query=query)

    def test_due_cli_invalid_as_of_and_help(self) -> None:
        stderr = StringIO()
        with redirect_stderr(stderr):
            code = main(
                ["due", "--vault", str(self.vault), "--as-of", "next Friday"]
            )
        self.assertEqual(code, 2)
        self.assertIn("YYYY-MM-DD", stderr.getvalue())
        with self.assertRaises(SystemExit) as help_exit:
            main(["due", "--help"])
        self.assertEqual(help_exit.exception.code, 0)
