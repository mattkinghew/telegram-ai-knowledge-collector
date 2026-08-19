from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from tools.voice_capture_reference import (
    VoiceCaptureContractError,
    render_voice_markdown,
    validate_structured_voice_output,
    validate_voice_input,
)
from tools.voice_capture_simulator import simulate_voice_capture


ROOT = Path(__file__).parent.parent
FIXTURE_DIR = Path(__file__).parent / "fixtures" / "voice_capture"


class VoiceCaptureContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.capture = {
            "schema_version": "1",
            "captured_at": "2026-08-20T09:30:00+08:00",
            "source_type": "voice_transcript",
            "raw_transcript": "完成咗訪談筆記。Next step: draft proposal — 保留 **Markdown**。",
            "allowed_projects": ["Project Alpha", "Project Beta"],
        }
        self.output = {
            "suggested_title": "訪談後續記錄",
            "capture_type": "mixed",
            "one_sentence_summary": "完成訪談筆記，下一步草擬 proposal。",
            "completed": ["完成訪談筆記"],
            "in_progress": [],
            "next_actions": ["Draft proposal"],
            "blockers": [],
            "decisions": [],
            "knowledge": ["保留 **Markdown**"],
            "content_ideas": [],
            "project_updates": [],
            "facts_to_verify": [],
            "related_projects": ["Project Alpha"],
            "confidence": "medium",
        }

    def test_input_is_strict_and_preserves_transcript_exactly(self) -> None:
        original = copy.deepcopy(self.capture)
        validated = validate_voice_input(self.capture)
        self.assertEqual(validated["raw_transcript"], self.capture["raw_transcript"])
        self.assertEqual(self.capture, original)
        with self.assertRaises(VoiceCaptureContractError):
            validate_voice_input(dict(self.capture, extra="not allowed"))
        with self.assertRaises(VoiceCaptureContractError):
            validate_voice_input(dict(self.capture, raw_transcript="   "))

    def test_output_rejects_unsupported_or_uncertain_project(self) -> None:
        validated = validate_structured_voice_output(
            self.output,
            allowed_projects=self.capture["allowed_projects"],
        )
        self.assertEqual(validated["related_projects"], ["Project Alpha"])
        with self.assertRaises(VoiceCaptureContractError):
            validate_structured_voice_output(
                dict(self.output, related_projects=["Invented Project"]),
                allowed_projects=self.capture["allowed_projects"],
            )
        uncertain = dict(self.output, related_projects=[])
        self.assertEqual(
            validate_structured_voice_output(
                uncertain,
                allowed_projects=self.capture["allowed_projects"],
            )["related_projects"],
            [],
        )

    def test_renderer_omits_empty_sections_and_preserves_source(self) -> None:
        markdown = render_voice_markdown(self.capture, self.output)
        self.assertIn("ai_status: suggested", markdown)
        self.assertIn("## 完成", markdown)
        self.assertIn("- [ ] Draft proposal", markdown)
        self.assertNotIn("## 進行中", markdown)
        self.assertNotIn("## Blockers / 待確認", markdown)
        self.assertIn("## 原始語音轉錄\n" + self.capture["raw_transcript"], markdown)
        self.assertIn("**Markdown**", markdown)

    def test_absent_blockers_remain_empty(self) -> None:
        result = simulate_voice_capture(self.capture, mode="knowledge")
        self.assertEqual(result["blockers"], [])
        self.assertNotIn("## Blockers / 待確認", render_voice_markdown(self.capture, result))

    def test_content_idea_is_not_converted_to_a_task(self) -> None:
        result = simulate_voice_capture(self.capture, mode="knowledge")
        self.assertTrue(result["content_ideas"])
        self.assertEqual(result["next_actions"], [])

    def test_offline_and_ai_failure_cannot_lose_transcript(self) -> None:
        offline = simulate_voice_capture(self.capture, mode="offline")
        unavailable = simulate_voice_capture(self.capture, mode="ai_unavailable")
        for result in (offline, unavailable["fallback_markdown"]):
            self.assertIn("ai_status: pending", result)
            self.assertIn(self.capture["raw_transcript"], result)
        self.assertFalse(unavailable["ok"])

    def test_chinese_cantonese_english_and_punctuation_are_preserved(self) -> None:
        transcript = "我聽日要 follow up：『方案 A』— keep `raw_text` & check #1。"
        capture = dict(self.capture, raw_transcript=transcript)
        markdown = render_voice_markdown(capture)
        self.assertIn(transcript, markdown)

    def test_failure_modes_are_deterministic_and_deliberately_invalid(self) -> None:
        first = simulate_voice_capture(self.capture, mode="mixed")
        second = simulate_voice_capture(self.capture, mode="mixed")
        self.assertEqual(first, second)
        invalid_json = simulate_voice_capture(self.capture, mode="invalid_json")
        with self.assertRaises(json.JSONDecodeError):
            json.loads(invalid_json["provider_payload"])
        self.assertIn(self.capture["raw_transcript"], invalid_json["fallback_markdown"])
        mismatch = simulate_voice_capture(self.capture, mode="schema_mismatch")
        with self.assertRaises(VoiceCaptureContractError):
            validate_structured_voice_output(
                mismatch["provider_payload"],
                allowed_projects=self.capture["allowed_projects"],
            )
        self.assertIn(self.capture["raw_transcript"], mismatch["fallback_markdown"])

    def test_structured_list_items_cannot_inject_new_sections(self) -> None:
        with self.assertRaises(VoiceCaptureContractError):
            validate_structured_voice_output(
                dict(self.output, knowledge=["Supported point\n## Invented section"]),
                allowed_projects=self.capture["allowed_projects"],
            )


class VoiceCaptureArtifactTests(unittest.TestCase):
    def test_fourteen_fictional_fixtures_are_valid(self) -> None:
        expected_names = {
            "pure_work_update",
            "pure_knowledge",
            "idea_capture",
            "learning_note",
            "mixed_work_and_knowledge",
            "project_blocker",
            "decision",
            "content_idea",
            "ambiguous_action",
            "no_project_match",
            "cantonese_transcript",
            "mixed_cantonese_english",
            "long_transcript",
            "offline_capture",
        }
        paths = sorted(FIXTURE_DIR.glob("*.json"))
        self.assertEqual({path.stem for path in paths}, expected_names)
        for path in paths:
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertNotIn("/Users/", text)
                fixture = json.loads(text)
                request = validate_voice_input(fixture["request"])
                if fixture["mode"] == "offline":
                    self.assertIn(
                        request["raw_transcript"],
                        simulate_voice_capture(request, mode="offline"),
                    )
                else:
                    validate_structured_voice_output(
                        fixture["response"],
                        allowed_projects=request["allowed_projects"],
                    )

    def test_schemas_prompt_template_and_docs_define_required_boundaries(self) -> None:
        request_schema = json.loads(
            (ROOT / "schemas/voice-capture-request-v1.schema.json").read_text(encoding="utf-8")
        )
        response_schema = json.loads(
            (ROOT / "schemas/voice-capture-response-v1.schema.json").read_text(encoding="utf-8")
        )
        self.assertFalse(request_schema["additionalProperties"])
        self.assertEqual(request_schema["properties"]["source_type"]["const"], "voice_transcript")
        self.assertFalse(response_schema["additionalProperties"])
        self.assertEqual(
            response_schema["properties"]["capture_type"]["enum"],
            ["work", "knowledge", "idea", "learning", "mixed"],
        )
        prompt = (ROOT / "prompts/gemini-voice-structured-capture-v1.md").read_text(encoding="utf-8")
        self.assertIn("Structured Capture Processor", prompt)
        self.assertIn("allowed_projects", prompt)
        self.assertIn("facts_to_verify", prompt)
        template = (ROOT / "templates/universal-voice-capture-v1.md").read_text(encoding="utf-8")
        self.assertIn("## 原始語音轉錄", template)
        build_sheet = (ROOT / "docs/SHORTCUT_BUILD_SHEET_VOICE_CAPTURE.md").read_text(encoding="utf-8")
        self.assertIn("語音快速記錄", build_sheet)
        self.assertIn("Siri", build_sheet)
        self.assertIn("未經裝置驗證", build_sheet)
        acceptance = (ROOT / "docs/VOICE_CAPTURE_DEVICE_ACCEPTANCE.md").read_text(encoding="utf-8")
        self.assertEqual(acceptance.count("### Test "), 5)
        for field in (
            "Pass / Fail",
            "Capture time",
            "Transcript correction needed",
            "Structure useful",
            "Wrong classification",
            "Missing information",
            "Remotely Save result",
        ):
            self.assertIn(f"| {field} |", acceptance)
        self.assertNotIn("| Note created locally |", acceptance)
        self.assertNotIn("| Sync observed |", acceptance)

    def test_voice_build_sheet_is_literal_and_has_no_extra_questions(self) -> None:
        build_sheet = (ROOT / "docs/SHORTCUT_BUILD_SHEET_VOICE_CAPTURE.md").read_text(
            encoding="utf-8"
        )
        self.assertEqual(build_sheet.count("### Step "), 17)
        for step in build_sheet.split("### Step ")[1:]:
            for label in (
                "- Action:",
                "- Input:",
                "- Output variable:",
                "- Prompt text:",
                "- Branch condition:",
                "- Expected result:",
                "- Failure behavior:",
            ):
                self.assertIn(label, step)
        self.assertIn("Dictate Text", build_sheet)
        self.assertIn("editable transcript", build_sheet.lower())
        self.assertIn("ai_status: pending", build_sheet)
        self.assertIn("Show Result", build_sheet)
        self.assertIn("obsidian://new", build_sheet)
        self.assertIn("No title, classification, project, tag, Insight, Context, or Action prompt", build_sheet)


if __name__ == "__main__":
    unittest.main()
