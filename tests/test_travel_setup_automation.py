from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.mobile_enrichment_simulator import (
    simulate_travel_enrichment,
    validate_travel_enrichment_request,
    validate_travel_success_response,
)
from tools.travel_readiness_check import check_repository, is_repository_path_excluded
from tools.validate_private_config_example import (
    PrivateConfigValidationError,
    validate_private_config,
)


ROOT = Path(__file__).parent.parent
REQUEST_DIR = ROOT / "samples" / "travel_ai_requests"
RESPONSE_DIR = ROOT / "samples" / "travel_ai_responses"


class PrivateConfigValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = {
            "obsidian_vault_id": "EXAMPLE_VAULT_ID",
            "active_projects": ["Project Alpha", "Project Beta"],
            "make_webhook_url": "SET_ON_DEVICE_ONLY",
            "ai_enabled": False,
        }

    def test_example_config_is_valid_and_placeholder_only(self) -> None:
        path = ROOT / "config" / "private-values.example.json"
        self.assertEqual(validate_private_config(json.loads(path.read_text(encoding="utf-8"))), self.config)

    def test_unknown_key_and_real_private_values_are_rejected(self) -> None:
        with self.assertRaisesRegex(PrivateConfigValidationError, "known keys"):
            validate_private_config(dict(self.config, token="secret"))
        with self.assertRaisesRegex(PrivateConfigValidationError, "EXAMPLE_VAULT_ID"):
            validate_private_config(dict(self.config, obsidian_vault_id="Personal Vault"))
        with self.assertRaisesRegex(PrivateConfigValidationError, "credential-like"):
            validate_private_config(
                dict(self.config, active_projects=["api_key=fictional-secret-value"])
            )

    def test_webhook_must_remain_the_on_device_placeholder(self) -> None:
        with self.assertRaisesRegex(PrivateConfigValidationError, "SET_ON_DEVICE_ONLY"):
            validate_private_config(
                dict(self.config, make_webhook_url="https://hook.example.invalid/private")
            )


class TravelIntegrationSampleTests(unittest.TestCase):
    def test_seven_requests_match_deterministic_expected_outputs(self) -> None:
        names = (
            "summary",
            "recommendation",
            "short_article",
            "project_knowledge",
            "task",
            "decision",
            "learning_note",
        )
        self.assertEqual(sorted(path.stem for path in REQUEST_DIR.glob("*.json")), sorted(names))
        for name in names:
            with self.subTest(name=name):
                request = json.loads((REQUEST_DIR / f"{name}.json").read_text(encoding="utf-8"))
                expected = json.loads((RESPONSE_DIR / f"{name}.json").read_text(encoding="utf-8"))
                validated = validate_travel_enrichment_request(request)
                actual = simulate_travel_enrichment(validated)
                validate_travel_success_response(
                    expected,
                    allowed_projects=request["allowed_projects"],
                    requested_output=request["requested_output"],
                )
                self.assertEqual(actual, expected)

    def test_failure_samples_are_safe_and_parseable(self) -> None:
        for name, code in (
            ("ai_unavailable", "AI_UNAVAILABLE"),
            ("timeout", "AI_TIMEOUT"),
            ("schema_mismatch", "SCHEMA_MISMATCH"),
        ):
            with self.subTest(name=name):
                response = json.loads((RESPONSE_DIR / f"{name}.json").read_text(encoding="utf-8"))
                self.assertFalse(response["ok"])
                self.assertEqual(response["error_code"], code)
                self.assertTrue(response["quick_save_available"])
        invalid_reference = (RESPONSE_DIR / "invalid_json_reference.md").read_text(encoding="utf-8")
        self.assertIn("not valid JSON", invalid_reference)
        self.assertIn("Quick Save", invalid_reference)


class TravelReadinessTests(unittest.TestCase):
    def test_protected_repository_paths_are_excluded_before_scanning(self) -> None:
        for value in (
            ".env",
            ".env.local",
            ".obsidian/plugins/example.json",
            "Private/example.md",
            "Credentials/example.txt",
            "20_Areas/25_Self_Management/example.md",
        ):
            with self.subTest(value=value):
                self.assertTrue(is_repository_path_excluded(Path(value)))
        self.assertFalse(is_repository_path_excluded(Path("docs/TRAVEL_QUICK_START.md")))

    def test_current_repository_passes_repository_only_checks(self) -> None:
        result = check_repository(ROOT)
        self.assertTrue(result.passed, "\n".join(result.failures))
        self.assertIn("Knowledge Shortcut", result.manual_only_pending)
        self.assertIn("Make/Gemini", result.manual_only_pending)

    def test_missing_required_doc_and_real_make_hook_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tracked = [Path("docs/private.md")]
            (root / "docs").mkdir()
            real_looking_hook = "https://hook.us1." + "make.com/real-looking-id"
            (root / tracked[0]).write_text(real_looking_hook + "\n", encoding="utf-8")
            result = check_repository(root, tracked_files=tracked)
        self.assertFalse(result.passed)
        self.assertTrue(any("Missing required" in failure for failure in result.failures))
        self.assertTrue(any("webhook" in failure.lower() for failure in result.failures))


class CurrentDocsMapTests(unittest.TestCase):
    def test_current_docs_map_points_to_existing_files(self) -> None:
        text = (ROOT / "docs" / "CURRENT_DOCS_MAP.md").read_text(encoding="utf-8")
        required = {
            "docs/SHORTCUT_BUILD_SHEET_KNOWLEDGE_CAPTURE.md": "CURRENT",
            "docs/SHORTCUT_BUILD_SHEET_PROJECT_UPDATE.md": "CURRENT",
            "docs/MAKE_GEMINI_TRAVEL_SETUP_CHECKLIST.md": "CURRENT",
            "docs/TRAVEL_E2E_ACCEPTANCE.md": "DEVICE_TEST",
            "docs/IPHONE_SHORTCUT_BUILD_SPEC_V2.md": "REFERENCE",
            "docs/IPHONE_SHORTCUT_BUILD_SPEC_V3.md": "REFERENCE",
            "docs/MAKE_GEMINI_ENRICHMENT_SPEC_V1.md": "REFERENCE",
            "docs/MAKE_GEMINI_ENRICHMENT_SPEC_V2.md": "REFERENCE",
        }
        for path, status in required.items():
            with self.subTest(path=path):
                self.assertTrue((ROOT / path).is_file())
                self.assertIn(path, text)
                self.assertRegex(text, rf"(?m)^\| `{path}` \| {status} \|")


if __name__ == "__main__":
    unittest.main()
