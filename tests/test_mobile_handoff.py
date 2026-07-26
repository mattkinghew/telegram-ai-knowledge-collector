from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

from business_knowledge_capture.cli import build_parser, main
from business_knowledge_capture.core import (
    ProtectedPathError,
    extract_source,
    initialize_vault,
    load_protected_patterns,
    review_note,
)
from business_knowledge_capture.mobile_handoff import (
    HANDOFF_SCHEMA_VERSION,
    MAX_HANDOFF_BYTES,
    HandoffFileSafetyError,
    HandoffValidationError,
    format_handoff_preview,
    import_handoff,
    load_handoff,
    parse_handoff_bytes,
    validate_handoff_payload,
)
from business_knowledge_capture.search import InboxSearchQuery, search_inbox


class MobileHandoffTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(dir="/private/tmp")
        self.root = Path(self.temp.name)
        self.vault = self.root / "vault"
        (self.vault / "00_Inbox").mkdir(parents=True)
        (self.vault / "10_Work" / "11_Projects").mkdir(parents=True)
        (self.vault / "90_System").mkdir()
        initialize_vault(self.vault)
        self.payload = {
            "schema_version": 1,
            "handoff_id": "20260726T210000Z-iphone-001",
            "source_type": "text",
            "title": "Mobile capture",
            "content": "Review the onboarding workflow.",
            "source_url": "",
            "captured_at": "2026-07-26T19:00:00Z",
            "action_required": "Review and classify.",
            "deadline": "",
            "resource_expiry": "",
            "reminder_date": "",
            "reminder_note": "",
            "related_project": "14_New_Role_90_Day",
            "related_area": "New Role",
        }

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_payload(
        self,
        payload: object = None,
        *,
        name: str = "handoff.json",
    ) -> Path:
        path = self.root / name
        value = self.payload if payload is None else payload
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def copy_payload(self, **changes: object) -> dict[str, object]:
        payload = dict(self.payload)
        payload.update(changes)
        return payload

    def run_cli(self, arguments: list[str]) -> tuple[int, str, str]:
        stdout = StringIO()
        stderr = StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            result = main(arguments)
        return result, stdout.getvalue(), stderr.getvalue()

    def import_payload(self, **changes: object) -> tuple[Path, object, Path]:
        path = self.write_payload(self.copy_payload(**changes))
        note, duplicate = import_handoff(vault=self.vault, file_path=path)
        return note, duplicate, path

    # File safety: 1-9
    def test_01_valid_regular_json_file(self) -> None:
        self.assertEqual(load_handoff(self.write_payload()).schema_version, 1)

    def test_02_missing_file_rejected(self) -> None:
        with self.assertRaises(HandoffFileSafetyError):
            load_handoff(self.root / "missing.json")

    def test_03_directory_rejected(self) -> None:
        directory = self.root / "directory.json"
        directory.mkdir()
        with self.assertRaises(HandoffFileSafetyError):
            load_handoff(directory)

    def test_04_symlink_file_rejected(self) -> None:
        target = self.write_payload()
        link = self.root / "link.json"
        link.symlink_to(target)
        with self.assertRaises(HandoffFileSafetyError):
            load_handoff(link)

    def test_05_symlink_ancestor_rejected(self) -> None:
        target = self.root / "target"
        target.mkdir()
        (target / "handoff.json").write_text(
            json.dumps(self.payload), encoding="utf-8"
        )
        link = self.root / "linked"
        link.symlink_to(target, target_is_directory=True)
        with self.assertRaises(HandoffFileSafetyError):
            load_handoff(link / "handoff.json")

    def test_06_non_json_extension_rejected(self) -> None:
        with self.assertRaises(HandoffFileSafetyError):
            load_handoff(self.write_payload(name="handoff.txt"))

    def test_07_file_over_256kb_rejected(self) -> None:
        path = self.root / "large.json"
        path.write_bytes(b"x" * (MAX_HANDOFF_BYTES + 1))
        with self.assertRaises(HandoffFileSafetyError):
            load_handoff(path)

    def test_08_invalid_utf8_rejected(self) -> None:
        path = self.root / "invalid.json"
        path.write_bytes(b"\xff\xfe")
        with self.assertRaises(HandoffFileSafetyError):
            load_handoff(path)

    def test_09_special_file_rejected(self) -> None:
        if not hasattr(os, "mkfifo"):
            self.skipTest("FIFO fixture is unavailable.")
        path = self.root / "pipe.json"
        os.mkfifo(path)
        with self.assertRaises(HandoffFileSafetyError):
            load_handoff(path)

    # Strict JSON: 10-22
    def test_10_valid_object(self) -> None:
        self.assertEqual(validate_handoff_payload(self.payload).title, "Mobile capture")

    def test_11_top_level_array_rejected(self) -> None:
        with self.assertRaises(HandoffValidationError):
            validate_handoff_payload([])

    def test_12_malformed_json_rejected(self) -> None:
        with self.assertRaises(HandoffValidationError):
            parse_handoff_bytes(b'{"schema_version": 1')

    def test_13_duplicate_key_rejected(self) -> None:
        raw = json.dumps(self.payload)[:-1] + ',"title":"second"}'
        with self.assertRaisesRegex(HandoffValidationError, "duplicate key"):
            parse_handoff_bytes(raw.encode())

    def test_14_unknown_field_rejected(self) -> None:
        payload = self.copy_payload(attachment="x")
        with self.assertRaisesRegex(HandoffValidationError, "Unknown"):
            validate_handoff_payload(payload)

    def test_15_missing_field_rejected(self) -> None:
        payload = self.copy_payload()
        del payload["source_type"]
        with self.assertRaisesRegex(HandoffValidationError, "Missing"):
            validate_handoff_payload(payload)

    def test_16_null_rejected(self) -> None:
        with self.assertRaises(HandoffValidationError):
            validate_handoff_payload(self.copy_payload(title=None))

    def test_17_number_instead_of_string_rejected(self) -> None:
        with self.assertRaises(HandoffValidationError):
            validate_handoff_payload(self.copy_payload(title=7))

    def test_18_boolean_instead_of_string_rejected(self) -> None:
        with self.assertRaises(HandoffValidationError):
            validate_handoff_payload(self.copy_payload(title=True))

    def test_19_nested_object_rejected(self) -> None:
        with self.assertRaises(HandoffValidationError):
            validate_handoff_payload(self.copy_payload(content={"text": "x"}))

    def test_20_nested_array_rejected(self) -> None:
        with self.assertRaises(HandoffValidationError):
            validate_handoff_payload(self.copy_payload(content=["x"]))

    def test_21_unsupported_schema_version_rejected(self) -> None:
        with self.assertRaisesRegex(HandoffValidationError, "version: 2"):
            validate_handoff_payload(self.copy_payload(schema_version=2))

    def test_22_trailing_content_rejected(self) -> None:
        raw = json.dumps(self.payload).encode() + b"\n{}"
        with self.assertRaises(HandoffValidationError):
            parse_handoff_bytes(raw)

    def test_22b_nonfinite_numbers_rejected(self) -> None:
        for value in (b"NaN", b"Infinity", b"-Infinity"):
            raw = json.dumps(self.payload).replace(
                '"schema_version": 1',
                '"schema_version": ' + value.decode(),
            )
            with self.subTest(value=value), self.assertRaises(
                HandoffValidationError
            ):
                parse_handoff_bytes(raw.encode())

    # Field validation: 23-37
    def test_23_valid_handoff_id(self) -> None:
        value = validate_handoff_payload(
            self.copy_payload(handoff_id="A-z_0.1:ok")
        )
        self.assertEqual(value.handoff_id, "A-z_0.1:ok")

    def test_24_handoff_id_slash_rejected(self) -> None:
        with self.assertRaises(HandoffValidationError):
            validate_handoff_payload(self.copy_payload(handoff_id="bad/id"))

    def test_25_handoff_id_whitespace_rejected(self) -> None:
        with self.assertRaises(HandoffValidationError):
            validate_handoff_payload(self.copy_payload(handoff_id="bad id"))

    def test_26_empty_title_rejected(self) -> None:
        with self.assertRaises(HandoffValidationError):
            validate_handoff_payload(self.copy_payload(title=""))

    def test_27_overlong_title_rejected(self) -> None:
        with self.assertRaises(HandoffValidationError):
            validate_handoff_payload(self.copy_payload(title="x" * 201))

    def test_28_overlong_content_rejected(self) -> None:
        with self.assertRaises(HandoffValidationError):
            validate_handoff_payload(self.copy_payload(content="x" * 50_001))

    def test_29_newline_title_rejected(self) -> None:
        with self.assertRaisesRegex(HandoffValidationError, "newlines"):
            validate_handoff_payload(self.copy_payload(title="a\nb"))

    def test_30_newline_action_rejected(self) -> None:
        with self.assertRaisesRegex(HandoffValidationError, "newlines"):
            validate_handoff_payload(
                self.copy_payload(action_required="a\nb")
            )

    def test_31_multiline_content_accepted(self) -> None:
        result = validate_handoff_payload(
            self.copy_payload(content="line one\nline two")
        )
        self.assertIn("\n", result.content)

    def test_32_invalid_deadline_rejected(self) -> None:
        with self.assertRaises(HandoffValidationError):
            validate_handoff_payload(self.copy_payload(deadline="2026-02-30"))

    def test_33_invalid_resource_expiry_rejected(self) -> None:
        with self.assertRaises(HandoffValidationError):
            validate_handoff_payload(
                self.copy_payload(resource_expiry="2026-13-01")
            )

    def test_34_invalid_reminder_date_rejected(self) -> None:
        with self.assertRaises(HandoffValidationError):
            validate_handoff_payload(
                self.copy_payload(reminder_date="26-07-2026")
            )

    def test_35_captured_at_without_timezone_rejected(self) -> None:
        with self.assertRaisesRegex(HandoffValidationError, "timezone"):
            validate_handoff_payload(
                self.copy_payload(captured_at="2026-07-26T19:00:00")
            )

    def test_36_captured_at_with_z_accepted(self) -> None:
        result = validate_handoff_payload(
            self.copy_payload(captured_at="2026-07-26T19:00:00Z")
        )
        self.assertTrue(result.captured_at.endswith("Z"))

    def test_37_captured_at_with_offset_accepted(self) -> None:
        result = validate_handoff_payload(
            self.copy_payload(captured_at="2026-07-26T21:00:00+02:00")
        )
        self.assertTrue(result.captured_at.endswith("+02:00"))

    # Source types: 38-47
    def test_38_valid_text(self) -> None:
        self.assertEqual(validate_handoff_payload(self.payload).source_type, "text")

    def test_39_text_without_content_rejected(self) -> None:
        with self.assertRaises(HandoffValidationError):
            validate_handoff_payload(self.copy_payload(content=" "))

    def test_40_text_with_source_url_rejected(self) -> None:
        with self.assertRaises(HandoffValidationError):
            validate_handoff_payload(
                self.copy_payload(source_url="https://example.com")
            )

    def test_41_valid_url(self) -> None:
        result = validate_handoff_payload(
            self.copy_payload(
                source_type="url",
                content="Optional note",
                source_url="https://example.com/path?token=redacted",
            )
        )
        self.assertEqual(result.source_type, "url")

    def test_42_url_without_source_url_rejected(self) -> None:
        with self.assertRaises(HandoffValidationError):
            validate_handoff_payload(
                self.copy_payload(source_type="url", content="")
            )

    def test_43_unsupported_url_scheme_rejected(self) -> None:
        for value in (
            "file:///tmp/a",
            "ftp://example.com/a",
            "data:text/plain,x",
            "javascript:alert(1)",
            "mailto:a@example.com",
        ):
            with self.subTest(value=value), self.assertRaises(
                HandoffValidationError
            ):
                validate_handoff_payload(
                    self.copy_payload(
                        source_type="url",
                        content="",
                        source_url=value,
                    )
                )

    def test_44_url_embedded_credentials_rejected(self) -> None:
        with self.assertRaises(HandoffValidationError):
            validate_handoff_payload(
                self.copy_payload(
                    source_type="url",
                    content="",
                    source_url="https://user:pass@example.com",
                )
            )

    def test_45_valid_voice_transcript(self) -> None:
        result = validate_handoff_payload(
            self.copy_payload(source_type="voice_transcript")
        )
        self.assertEqual(result.source_type, "voice_transcript")

    def test_46_voice_transcript_without_content_rejected(self) -> None:
        with self.assertRaises(HandoffValidationError):
            validate_handoff_payload(
                self.copy_payload(source_type="voice_transcript", content="")
            )

    def test_47_unsupported_source_type_rejected(self) -> None:
        with self.assertRaises(HandoffValidationError):
            validate_handoff_payload(self.copy_payload(source_type="audio"))

    # Validate and preview: 48-55
    def test_48_validate_does_not_read_vault(self) -> None:
        path = self.write_payload()
        result, stdout, _ = self.run_cli(
            ["handoff", "validate", "--file", str(path)]
        )
        self.assertEqual((result, stdout.strip()), (0, "Handoff is valid."))

    def test_49_validate_does_not_modify_file(self) -> None:
        path = self.write_payload()
        before = hashlib.sha256(path.read_bytes()).digest()
        self.run_cli(["handoff", "validate", "--file", str(path)])
        self.assertEqual(hashlib.sha256(path.read_bytes()).digest(), before)

    def test_50_preview_does_not_modify_file(self) -> None:
        path = self.write_payload()
        before = path.read_bytes()
        self.run_cli(["handoff", "preview", "--file", str(path)])
        self.assertEqual(path.read_bytes(), before)

    def test_51_preview_hides_content_by_default(self) -> None:
        result = format_handoff_preview(validate_handoff_payload(self.payload))
        self.assertNotIn(self.payload["content"], result)

    def test_52_preview_show_content_is_explicit(self) -> None:
        result = format_handoff_preview(
            validate_handoff_payload(self.payload),
            show_content=True,
        )
        self.assertIn(self.payload["content"], result)

    def test_53_preview_truncates_after_2000_characters(self) -> None:
        handoff = validate_handoff_payload(self.copy_payload(content="x" * 2_001))
        result = format_handoff_preview(handoff, show_content=True)
        self.assertIn("truncated after 2000", result)
        self.assertNotIn("x" * 2_001, result)

    def test_54_preview_does_not_expose_vault_path(self) -> None:
        result = format_handoff_preview(validate_handoff_payload(self.payload))
        self.assertNotIn(str(self.vault), result)

    def test_55_invalid_preview_returns_nonzero(self) -> None:
        path = self.write_payload(self.copy_payload(title=""))
        result, _, stderr = self.run_cli(
            ["handoff", "preview", "--file", str(path)]
        )
        self.assertEqual(result, 1)
        self.assertTrue(stderr.startswith("ERROR:"))

    # Import: 56-68
    def test_56_text_import_creates_flat_inbox_note(self) -> None:
        note, _, _ = self.import_payload()
        self.assertEqual(note.parent, self.vault / "00_Inbox")

    def test_57_url_import_creates_note_without_network(self) -> None:
        with mock.patch(
            "business_knowledge_capture.core.socket.getaddrinfo",
            side_effect=AssertionError("network used"),
        ), mock.patch(
            "business_knowledge_capture.core.urllib.request.build_opener",
            side_effect=AssertionError("network used"),
        ):
            note, _, _ = self.import_payload(
                source_type="url",
                content="Optional note",
                source_url="https://example.com/path",
            )
        self.assertIn(
            "- Source URL: https://example.com/path",
            note.read_text(encoding="utf-8"),
        )

    def test_58_voice_import_creates_transcript_metadata(self) -> None:
        note, _, _ = self.import_payload(source_type="voice_transcript")
        body = note.read_text(encoding="utf-8")
        self.assertIn("- Processing Status: transcript_registered", body)
        self.assertIn("- Transcript Review Status: pending", body)

    def test_59_handoff_metadata_appears(self) -> None:
        note, _, _ = self.import_payload()
        body = note.read_text(encoding="utf-8")
        self.assertIn(f"- Handoff Schema Version: {HANDOFF_SCHEMA_VERSION}", body)
        self.assertIn(f"- Handoff ID: {self.payload['handoff_id']}", body)
        self.assertIn("- Handoff Source Type: text", body)
        self.assertIn(f"- Handoff Captured At: {self.payload['captured_at']}", body)

    def test_60_handoff_absolute_file_path_does_not_appear(self) -> None:
        note, _, handoff = self.import_payload()
        self.assertNotIn(str(handoff), note.read_text(encoding="utf-8"))

    def test_61_existing_duplicate_detection_runs(self) -> None:
        _, first, _ = self.import_payload()
        _, second, _ = self.import_payload()
        self.assertEqual(first.status, "unique")
        self.assertEqual(second.status, "exact_duplicate_suggested")

    def test_62_reimport_creates_duplicate_suggestion(self) -> None:
        note_one, _, _ = self.import_payload(source_type="voice_transcript")
        note_two, duplicate, _ = self.import_payload(
            source_type="voice_transcript"
        )
        self.assertNotEqual(note_one, note_two)
        self.assertEqual(duplicate.status, "exact_duplicate_suggested")

    def test_63_invalid_handoff_creates_no_note(self) -> None:
        before = tuple((self.vault / "00_Inbox").glob("*.md"))
        path = self.write_payload(self.copy_payload(deadline="bad"))
        with self.assertRaises(HandoffValidationError):
            import_handoff(vault=self.vault, file_path=path)
        self.assertEqual(tuple((self.vault / "00_Inbox").glob("*.md")), before)

    def test_64_import_failure_leaves_handoff_unchanged(self) -> None:
        path = self.write_payload()
        before = path.read_bytes()
        bad_vault = self.root / "bad-vault"
        bad_vault.mkdir()
        with self.assertRaises(Exception):
            import_handoff(vault=bad_vault, file_path=path)
        self.assertEqual(path.read_bytes(), before)

    def test_65_no_automatic_deletion(self) -> None:
        _, _, path = self.import_payload()
        self.assertTrue(path.is_file())

    def test_66_no_automatic_movement(self) -> None:
        _, _, path = self.import_payload()
        self.assertEqual(path.parent, self.root)

    def test_67_import_uses_atomic_note_write(self) -> None:
        path = self.write_payload()
        with mock.patch(
            "business_knowledge_capture.core.os.replace",
            wraps=os.replace,
        ) as replace:
            import_handoff(vault=self.vault, file_path=path)
        replace.assert_called_once()

    def test_68_existing_capture_remains_compatible(self) -> None:
        source = extract_source(
            vault=self.vault,
            patterns=load_protected_patterns(self.vault),
            text="Existing capture flow",
        )
        from business_knowledge_capture.core import create_inbox_note

        note = create_inbox_note(vault=self.vault, source=source)
        self.assertTrue(note.is_file())

    # Review: 69-74
    def test_69_mark_handoff(self) -> None:
        note, _, _ = self.import_payload()
        review_note(vault=self.vault, note_path=note, mark=["handoff"])
        self.assertIn(
            "- [x] Mobile handoff reviewed",
            note.read_text(encoding="utf-8"),
        )

    def test_70_mark_transcript(self) -> None:
        note, _, _ = self.import_payload(source_type="voice_transcript")
        review_note(vault=self.vault, note_path=note, mark=["transcript"])
        self.assertIn(
            "- [x] Voice transcript checked",
            note.read_text(encoding="utf-8"),
        )

    def test_71_mark_transcript_updates_metadata_status(self) -> None:
        note, _, _ = self.import_payload(source_type="voice_transcript")
        review_note(vault=self.vault, note_path=note, mark=["transcript"])
        self.assertIn(
            "- Transcript Review Status: reviewed",
            note.read_text(encoding="utf-8"),
        )

    def test_72_mark_transcript_on_nonvoice_rejected(self) -> None:
        note, _, _ = self.import_payload()
        with self.assertRaisesRegex(ValueError, "not applicable"):
            review_note(vault=self.vault, note_path=note, mark=["transcript"])

    def test_73_invalid_review_does_not_partially_modify(self) -> None:
        note, _, _ = self.import_payload()
        before = note.read_bytes()
        with self.assertRaises(ValueError):
            review_note(
                vault=self.vault,
                note_path=note,
                action_required="changed",
                mark=["transcript"],
            )
        self.assertEqual(note.read_bytes(), before)

    def test_74_existing_review_checkboxes_remain_compatible(self) -> None:
        note, _, _ = self.import_payload()
        review_note(
            vault=self.vault,
            note_path=note,
            mark=["summary", "dates", "handoff"],
        )
        body = note.read_text(encoding="utf-8")
        self.assertIn("- [x] Summary reviewed", body)
        self.assertIn("- [x] Date and reminder fields reviewed", body)

    # Security and regression: 75-82
    def test_75_protected_vault_path_remains_blocked(self) -> None:
        protected = self.vault / "Private" / "note.md"
        with self.assertRaises(ProtectedPathError):
            review_note(vault=self.vault, note_path=protected, mark=["handoff"])

    def test_76_vault_wide_scan_not_used(self) -> None:
        path = self.write_payload()
        with mock.patch(
            "pathlib.Path.rglob",
            side_effect=AssertionError("Vault-wide scan used"),
        ):
            import_handoff(vault=self.vault, file_path=path)

    def test_77_no_network_function_called_during_url_import(self) -> None:
        path = self.write_payload(
            self.copy_payload(
                source_type="url",
                content="",
                source_url="https://example.com",
            )
        )
        with mock.patch(
            "socket.create_connection",
            side_effect=AssertionError("network used"),
        ), mock.patch(
            "urllib.request.urlopen",
            side_effect=AssertionError("network used"),
        ):
            import_handoff(vault=self.vault, file_path=path)

    def test_78_no_external_ai_is_used(self) -> None:
        note, _, _ = self.import_payload()
        body = note.read_text(encoding="utf-8")
        self.assertIn("- Summary Status: pending", body)
        self.assertIn("No approved AI provider", body)

    def test_79_no_database_is_created(self) -> None:
        self.import_payload()
        self.assertEqual(list(self.root.rglob("*.db")), [])
        self.assertEqual(list(self.root.rglob("*.sqlite")), [])

    def test_80_python_39_import(self) -> None:
        self.assertEqual(HANDOFF_SCHEMA_VERSION, 1)
        self.assertTrue(callable(load_handoff))

    def test_81_search_accepts_voice_transcript_source_type(self) -> None:
        self.import_payload(source_type="voice_transcript")
        result = search_inbox(
            vault=self.vault,
            query=InboxSearchQuery(source_types=("voice_transcript",)),
        )
        self.assertEqual(result.total_matches, 1)

    def test_82_main_and_handoff_help_parse(self) -> None:
        parser = build_parser()
        args = parser.parse_args(
            ["handoff", "validate", "--file", "/private/tmp/example.json"]
        )
        self.assertEqual((args.command, args.handoff_command), ("handoff", "validate"))


if __name__ == "__main__":
    unittest.main()
