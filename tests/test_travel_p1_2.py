from __future__ import annotations

import json
import unittest
from pathlib import Path

from tools.mobile_enrichment_simulator import (
    EnrichmentContractError,
    simulate_travel_enrichment,
    validate_travel_enrichment_request,
    validate_travel_success_response,
)
from tools.mobile_capture_reference import (
    MobileCaptureValidationError,
    normalize_capture_input,
    render_mobile_markdown,
)
from tools.mobile_progress_report import (
    ProgressReportContractError,
    render_progress_report,
)
from tools.project_dashboard_reference import (
    DashboardContractError,
    render_project_dashboard,
)


ROOT = Path(__file__).parent.parent
TRAVEL_FIXTURES = Path(__file__).parent / "fixtures" / "travel_ai"


class TravelP12EnrichmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.request = {
            "schema_version": "3",
            "source_type": "article",
            "source": "https://example.com/public-article",
            "raw_content": "A fictional article says a smaller pilot can expose workflow gaps.",
            "user_insight": "Start with one bounded pilot.",
            "user_context": "Use this in Project Alpha planning.",
            "user_action": "Define the pilot acceptance criteria.",
            "output_goal": "project_knowledge",
            "requested_output": "summary",
            "project": "Project Alpha",
            "allowed_projects": ["Project Alpha", "Project Beta"],
        }

    def test_all_requested_output_modes_are_supported(self) -> None:
        modes = {
            "summary",
            "recommendation",
            "short_article",
            "project_knowledge",
            "task",
            "decision",
            "learning_note",
        }
        for mode in modes:
            with self.subTest(mode=mode):
                request = dict(self.request, requested_output=mode)
                result = simulate_travel_enrichment(request)["result"]
                self.assertEqual(result["recommended_output"], mode)
                self.assertLessEqual(len(result["core_points"]), 3)
                self.assertLessEqual(len(result["practical_applications"]), 3)
                self.assertLessEqual(len(result["facts_to_verify"]), 5)
                self.assertLessEqual(len(result["missing_information"]), 5)

    def test_short_article_is_only_emitted_for_short_article_mode(self) -> None:
        summary = simulate_travel_enrichment(self.request)["result"]
        article = simulate_travel_enrichment(
            dict(self.request, requested_output="short_article")
        )["result"]
        self.assertIsNone(summary["short_article_draft"])
        self.assertTrue(article["short_article_draft"].startswith("AI draft\n"))
        body = article["short_article_draft"].removeprefix("AI draft\n")
        self.assertGreaterEqual(len(body), 150)
        self.assertLessEqual(len(body), 300)

    def test_recommendation_has_bounded_operational_structure(self) -> None:
        result = simulate_travel_enrichment(
            dict(self.request, requested_output="recommendation")
        )["result"]
        joined = "\n".join(result["core_points"])
        for label in ("Situation:", "Insight:", "Reason:"):
            self.assertIn(label, joined)
        self.assertTrue(any(item.startswith("Risk:") for item in result["facts_to_verify"]))

    def test_video_url_uses_takeaway_without_claiming_transcript(self) -> None:
        request = dict(
            self.request,
            source_type="video_url",
            source="https://video.example/watch?v=fictional",
            raw_content="User takeaway only; no transcript was supplied.",
        )
        result = simulate_travel_enrichment(request)["result"]
        self.assertIn("No transcript", " ".join(result["missing_information"]))
        self.assertEqual(validate_travel_enrichment_request(request)["source"], request["source"])
        with self.assertRaises(EnrichmentContractError):
            validate_travel_enrichment_request(dict(request, source=""))

    def test_video_transcript_is_a_distinct_source_type(self) -> None:
        request = dict(
            self.request,
            source_type="video_transcript",
            source="https://video.example/watch?v=fictional",
            raw_content="Reviewed fictional transcript excerpt.",
        )
        self.assertEqual(
            validate_travel_enrichment_request(request)["source_type"],
            "video_transcript",
        )

    def test_invalid_requested_output_is_rejected(self) -> None:
        with self.assertRaisesRegex(EnrichmentContractError, "requested_output"):
            validate_travel_enrichment_request(
                dict(self.request, requested_output="generic_long_summary")
            )
        with self.assertRaisesRegex(EnrichmentContractError, "source must be blank"):
            validate_travel_enrichment_request(
                dict(self.request, source_type="shared_text", source="unexpected")
            )
        with self.assertRaisesRegex(EnrichmentContractError, "filename"):
            validate_travel_enrichment_request(
                dict(
                    self.request,
                    source_type="file_reference",
                    source="folder/example.pdf",
                )
            )

    def test_ai_failures_preserve_quick_save_boundary(self) -> None:
        for mode in (
            "timeout",
            "network_unavailable",
            "provider_unavailable",
            "invalid_json",
            "schema_mismatch",
            "offline",
        ):
            with self.subTest(mode=mode):
                response = simulate_travel_enrichment(self.request, mode=mode)
                if mode == "invalid_json":
                    self.assertIsInstance(response, str)
                elif mode == "schema_mismatch":
                    with self.assertRaises(EnrichmentContractError):
                        validate_travel_success_response(
                            response,
                            allowed_projects=self.request["allowed_projects"],
                            requested_output="summary",
                        )
                else:
                    self.assertFalse(response["ok"])
                    self.assertTrue(response["quick_save_available"])

    def test_source_user_and_ai_layers_remain_separate(self) -> None:
        result = simulate_travel_enrichment(self.request)["result"]
        forbidden = {"raw_content", "user_insight", "user_context", "user_action"}
        self.assertTrue(forbidden.isdisjoint(result))

    def test_fast_capture_preserves_video_url_without_ai(self) -> None:
        capture = {
            "schema_version": "1",
            "captured_at": "2026-08-19T09:00:00+08:00",
            "source_type": "video_url",
            "source": "https://video.example/watch?v=fictional",
            "raw_content": "我的快速重點；未提供 transcript。",
            "insight": "先保存重點。",
            "context": "",
            "action": "",
            "output_goal": "collect",
            "project": "",
        }
        normalized = normalize_capture_input(capture)
        markdown = render_mobile_markdown(capture)
        self.assertEqual(normalized["source"], capture["source"])
        self.assertIn("ai_status: none", markdown)
        self.assertNotIn("## AI 整理建議", markdown)

    def test_video_transcript_reference_is_distinct_from_voice_capture(self) -> None:
        capture = {
            "schema_version": "1",
            "captured_at": "2026-08-19T09:00:00+08:00",
            "source_type": "video_transcript",
            "source": "https://video.example/watch?v=fictional",
            "raw_content": "使用者另外複製並檢查的字幕片段。",
            "insight": "已提供文字證據。",
            "context": "學習筆記",
            "action": "核實來源",
            "output_goal": "collect",
            "project": "",
        }
        self.assertEqual(normalize_capture_input(capture)["source_type"], "video_transcript")
        with self.assertRaises(MobileCaptureValidationError):
            normalize_capture_input(dict(capture, source="file:///tmp/transcript.txt"))

    def test_deep_capture_renders_v3_ai_as_unconfirmed_layer(self) -> None:
        response = simulate_travel_enrichment(self.request)["result"]
        capture = {
            "schema_version": "1",
            "captured_at": "2026-08-19T09:00:00+08:00",
            "source_type": "shared_text",
            "source": "",
            "raw_content": "Fictional shared text.",
            "insight": "保留個人理解。",
            "context": "Project Alpha",
            "action": "人工審核",
            "output_goal": "project_knowledge",
            "project": "Project Alpha",
        }
        markdown = render_mobile_markdown(capture, ai_suggestions=response)
        self.assertIn("ai_status: suggested", markdown)
        self.assertIn("以下內容是未確認建議", markdown)
        self.assertIn("### 核心重點", markdown)
        self.assertIn(capture["raw_content"], markdown)
        self.assertIn(capture["insight"], markdown)

    def test_v3_schemas_match_the_travel_contract(self) -> None:
        request_schema = json.loads(
            (ROOT / "schemas/mobile-insight-request-v3.schema.json").read_text(
                encoding="utf-8"
            )
        )
        response_schema = json.loads(
            (ROOT / "schemas/mobile-insight-response-v3.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertIn("requested_output", request_schema["required"])
        self.assertIn("video_url", request_schema["properties"]["source_type"]["enum"])
        result_schema = response_schema["$defs"]["enrichment_result"]
        self.assertEqual(result_schema["properties"]["core_points"]["maxItems"], 3)
        self.assertEqual(result_schema["properties"]["facts_to_verify"]["maxItems"], 5)

    def test_all_travel_fixtures_are_fictional_and_valid(self) -> None:
        paths = sorted(TRAVEL_FIXTURES.glob("*.json"))
        self.assertEqual(len(paths), 12)
        for path in paths:
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertNotIn("/Users/", text)
                fixture = json.loads(text)
                request = validate_travel_enrichment_request(fixture["request"])
                response = simulate_travel_enrichment(request, mode=fixture["mode"])
                self.assertEqual(fixture["expected_kind"], "text" if isinstance(response, str) else "object")


class TravelP12ReportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = {
            "reporting_period": "2026-08-18 to 2026-08-19",
            "project": "Project Alpha",
            "selected_records": [
                {
                    "type": "progress_update",
                    "title": "Mobile workflow",
                    "status": "in_progress",
                    "detail": "Validated the fictional offline flow.",
                    "due_date": "",
                    "link": "",
                },
                {
                    "type": "task",
                    "title": "Run device acceptance",
                    "status": "next",
                    "detail": "Use the compact travel checklist.",
                    "due_date": "2026-08-20",
                    "link": "",
                },
                {
                    "type": "decision",
                    "title": "Keep Quick Save as default",
                    "status": "confirmed",
                    "detail": "AI remains optional.",
                    "due_date": "",
                    "link": "",
                },
                {
                    "type": "due_event",
                    "title": "Review travel setup",
                    "status": "pending",
                    "detail": "Manual verification required.",
                    "due_date": "2026-08-21",
                    "link": "",
                },
                {
                    "type": "evidence",
                    "title": "Offline test result",
                    "status": "verified",
                    "detail": "Fictional reference evidence.",
                    "due_date": "",
                    "link": "https://example.com/evidence",
                },
            ],
        }

    def test_report_renders_only_explicitly_selected_records(self) -> None:
        report = render_progress_report(self.payload)
        for record in self.payload["selected_records"]:
            self.assertIn(record["title"], report)
        self.assertNotIn("Inbox", report)
        self.assertIn("## Evidence", report)
        self.assertIn("## Decisions Required", report)

    def test_report_is_deterministic(self) -> None:
        self.assertEqual(
            render_progress_report(self.payload),
            render_progress_report(self.payload),
        )

    def test_report_rejects_unknown_types_and_unsafe_links(self) -> None:
        bad_type = json.loads(json.dumps(self.payload))
        bad_type["selected_records"][0]["type"] = "inbox_note"
        with self.assertRaises(ProgressReportContractError):
            render_progress_report(bad_type)
        bad_link = json.loads(json.dumps(self.payload))
        bad_link["selected_records"][-1]["link"] = "file:///private/example"
        with self.assertRaises(ProgressReportContractError):
            render_progress_report(bad_link)


class TravelP12DashboardTests(unittest.TestCase):
    def test_dashboard_renders_fictional_projects(self) -> None:
        payload = {
            "projects": [
                {
                    "name": "Project Alpha",
                    "status": "active",
                    "latest_update": "Offline reference flow complete.",
                    "next_action": "Run device acceptance.",
                    "blocker": "Device evidence pending.",
                    "next_review": "2026-08-20",
                }
            ]
        }
        dashboard = render_project_dashboard(payload)
        self.assertIn("### Project Alpha", dashboard)
        self.assertIn("Next action: Run device acceptance.", dashboard)

    def test_dashboard_rejects_unknown_fields(self) -> None:
        with self.assertRaises(DashboardContractError):
            render_project_dashboard(
                {
                    "projects": [
                        {
                            "name": "Project Alpha",
                            "status": "active",
                            "latest_update": "",
                            "next_action": "",
                            "blocker": "",
                            "next_review": "",
                            "private_client": "Example",
                        }
                    ]
                }
            )


class TravelP12ArtifactTests(unittest.TestCase):
    def test_required_templates_exist_with_operational_sections(self) -> None:
        required = {
            "project-status-v1.md": ("type: project_status", "## Next Actions", "## Evidence / Links"),
            "mobile-progress-update-v1.md": ("type: progress_update", "## 今日完成", "## 下一步"),
            "travel-daily-report-v1.md": ("## Completed Today", "## Tomorrow / Next Session"),
            "project-progress-report-v2.md": ("## Reporting Period", "## Outstanding Follow-ups"),
            "knowledge-processed-v1.md": ("type: knowledge", "## 原始內容", "## 待核實"),
            "project-dashboard-v1.md": ("# Project Dashboard", "## Active", "Next action:"),
        }
        for name, markers in required.items():
            with self.subTest(name=name):
                text = (ROOT / "templates" / name).read_text(encoding="utf-8")
                for marker in markers:
                    self.assertIn(marker, text)

    def test_required_travel_docs_cover_offline_privacy_and_acceptance(self) -> None:
        required = {
            "TRAVEL_PROJECT_OPERATIONS_CONTRACT_V1.md": ("Next Action", "Report Item", "Markdown only"),
            "IPHONE_SHORTCUT_PROJECT_UPDATE_ACTION_MAP.md": ("更新專案進度", "60 seconds", "No AI"),
            "KNOWLEDGE_OUTPUT_CONTRACT_V1.md": ("short_article", "video_url", "video_transcript"),
            "TRAVEL_OFFLINE_MODE.md": ("Quick Save", "Remotely Save", "URI"),
            "TRAVEL_PROJECT_REVIEW_ROUTINE.md": ("Morning", "2 minutes", "send manually"),
            "MAKE_GEMINI_TRAVEL_SETUP_CHECKLIST.md": ("Field mapping", "Error handling", "Expected response"),
            "TRAVEL_DEVICE_FINAL_ACCEPTANCE.md": ("Safari URL", "Project update Shortcut", "MANUAL_ACCEPTANCE_PENDING"),
            "TRAVEL_READINESS_STATUS.md": ("Device tested", "Travel-ready", "AI short article"),
        }
        for name, markers in required.items():
            with self.subTest(name=name):
                text = (ROOT / "docs" / name).read_text(encoding="utf-8")
                for marker in markers:
                    self.assertIn(marker, text)

    def test_active_project_example_is_fictional_and_bounded(self) -> None:
        payload = json.loads(
            (ROOT / "config/example-active-projects.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            payload["projects"],
            ["Project Alpha", "Project Beta", "Professional Learning", "Consulting Pipeline"],
        )

    def test_v3_prompt_preserves_layer_and_output_bounds(self) -> None:
        text = (ROOT / "prompts/gemini-mobile-enrichment-v3.md").read_text(encoding="utf-8")
        for marker in (
            "Source layer",
            "User layer",
            "AI Suggestions layer",
            "core_points <= 3",
            "short_article_draft",
            "AI draft",
            "Do not fetch",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
