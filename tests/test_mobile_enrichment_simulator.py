from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from tools.mobile_enrichment_simulator import (
    EnrichmentContractError,
    simulate_enrichment,
    validate_enrichment_request,
    validate_success_response,
)


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "gemini_enrichment"
REPOSITORY_ROOT = Path(__file__).parent.parent


class MobileEnrichmentSimulatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.request = {
            "schema_version": "2",
            "source_type": "shared_text",
            "source": "",
            "raw_content": "A fictional observation about reducing setup steps.",
            "user_insight": "A visible result should appear earlier.",
            "user_context": "Use this in a fictional onboarding review.",
            "user_action": "Draft a smaller setup experiment.",
            "output_goal": "project_knowledge",
            "project": "Example Project",
            "allowed_projects": ["Example Project", "Demo Project"],
        }

    def test_success_response_is_deterministic_and_schema_compatible(self) -> None:
        first = simulate_enrichment(self.request, mode="success")
        second = simulate_enrichment(self.request, mode="success")
        self.assertEqual(first, second)
        validate_success_response(first, allowed_projects=self.request["allowed_projects"])
        self.assertTrue(first["ok"])
        self.assertEqual(first["schema_version"], "2")
        self.assertEqual(first["result"]["related_project"], "Example Project")

    def test_source_and_user_layers_are_not_modified_or_returned_as_confirmed(self) -> None:
        original = copy.deepcopy(self.request)
        response = simulate_enrichment(self.request, mode="success")
        self.assertEqual(self.request, original)
        result = response["result"]
        self.assertNotIn("raw_content", result)
        self.assertNotIn("user_insight", result)
        self.assertNotIn("user_context", result)
        self.assertNotIn("user_action", result)

    def test_failure_modes_use_bounded_user_safe_payloads(self) -> None:
        expected = {
            "ai_unavailable": "AI_UNAVAILABLE",
            "timeout": "AI_TIMEOUT",
        }
        for mode, error_code in expected.items():
            with self.subTest(mode=mode):
                response = simulate_enrichment(self.request, mode=mode)
                self.assertEqual(response["ok"], False)
                self.assertEqual(response["error_code"], error_code)
                self.assertEqual(set(response), {"ok", "error_code", "message"})

    def test_invalid_json_and_schema_mismatch_are_deliberately_invalid(self) -> None:
        invalid_json = simulate_enrichment(self.request, mode="invalid_json")
        self.assertIsInstance(invalid_json, str)
        with self.assertRaises(json.JSONDecodeError):
            json.loads(invalid_json)
        mismatch = simulate_enrichment(self.request, mode="schema_mismatch")
        with self.assertRaises(EnrichmentContractError):
            validate_success_response(
                mismatch,
                allowed_projects=self.request["allowed_projects"],
            )

    def test_unknown_mode_is_rejected(self) -> None:
        with self.assertRaises(EnrichmentContractError):
            simulate_enrichment(self.request, mode="real_ai")

    def test_malformed_oversized_and_unsupported_requests_are_rejected(self) -> None:
        cases = (
            {key: value for key, value in self.request.items() if key != "raw_content"},
            dict(self.request, raw_content="x" * 50_001),
            dict(self.request, source_type="pdf_bytes"),
            dict(self.request, extra="unknown"),
            dict(self.request, project="Unlisted Project"),
        )
        for request in cases:
            with self.subTest(request=request), self.assertRaises(
                EnrichmentContractError
            ):
                validate_enrichment_request(request)

    def test_url_requires_http_or_https_and_preserves_source(self) -> None:
        source = "https://example.com/path?q=a%20b#section"
        request = dict(
            self.request,
            source_type="url",
            source=source,
            raw_content=source,
        )
        self.assertEqual(validate_enrichment_request(request)["source"], source)
        with self.assertRaises(EnrichmentContractError):
            validate_enrichment_request(dict(request, source="file:///tmp/note"))

    def test_all_twelve_prompt_fixtures_define_expected_behavior(self) -> None:
        fixture_paths = sorted(FIXTURE_DIR.glob("*.json"))
        self.assertEqual(len(fixture_paths), 12)
        self.assertEqual(fixture_paths[0].stem, "01_product_management")
        self.assertEqual(fixture_paths[-1].stem, "12_no_project_match")
        for path in fixture_paths:
            with self.subTest(path=path.name):
                fixture = json.loads(path.read_text(encoding="utf-8"))
                request = validate_enrichment_request(fixture["request"])
                response = simulate_enrichment(request, mode="success")
                validate_success_response(
                    response,
                    allowed_projects=request["allowed_projects"],
                )
                expected = fixture["expected"]
                related_project = response["result"]["related_project"]
                self.assertEqual(
                    related_project is None,
                    expected["related_project_must_be_null"],
                )
                self.assertLessEqual(
                    len(response["result"]["supporting_points"]),
                    expected["max_supporting_points"],
                )

    def test_v2_schema_documents_match_the_simulator_contract(self) -> None:
        request_schema = json.loads(
            (REPOSITORY_ROOT / "schemas/mobile-insight-request-v2.schema.json").read_text(
                encoding="utf-8"
            )
        )
        response_schema = json.loads(
            (REPOSITORY_ROOT / "schemas/mobile-insight-response-v2.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertFalse(request_schema["additionalProperties"])
        self.assertEqual(request_schema["properties"]["schema_version"]["const"], "2")
        self.assertEqual(
            set(request_schema["required"]),
            set(self.request),
        )
        result_schema = response_schema["$defs"]["enrichment_result"]
        self.assertFalse(result_schema["additionalProperties"])
        self.assertEqual(
            set(result_schema["required"]),
            set(simulate_enrichment(self.request)["result"]),
        )
        self.assertEqual(
            result_schema["properties"]["supporting_points"]["maxItems"],
            3,
        )
        self.assertEqual(
            response_schema["$defs"]["failure"]["properties"]["error_code"]["enum"],
            [
                "INVALID_REQUEST",
                "AI_UNAVAILABLE",
                "AI_TIMEOUT",
                "INVALID_AI_JSON",
                "SCHEMA_MISMATCH",
                "INTERNAL_ERROR",
            ],
        )


if __name__ == "__main__":
    unittest.main()
