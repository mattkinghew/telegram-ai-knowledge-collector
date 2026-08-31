from __future__ import annotations

import json
import io
import unittest
from contextlib import redirect_stderr
from unittest.mock import patch
from uuid import UUID

import httpx

from tools.p1_5_gemini_live_smoke import (
    LIVE_CASES,
    run_live_modes_smoke,
)
from tools.p1_5_staging_smoke import SmokeError


BASE_URL = "https://p1-5-staging.example"
TOKEN = "fictional-live-backend-token"


def provider_result(mode: str) -> dict:
    sections = {
        "voice_structure": {
            "completed": ["CSV mapping completed"],
            "in_progress": [],
            "next_actions": ["Test invalid URL"],
            "blockers": [],
            "decisions": [],
            "knowledge": [],
            "content_ideas": ["AI pricing short post"],
            "facts_to_verify": [],
            "related_projects": ["Project Alpha"],
        },
        "summary": {},
        "recommendation": {
            "situation": ["Two prototype paths"],
            "insight": ["One path lacks evidence"],
            "recommended_action": ["Validate the uncovered path"],
            "reason": ["It closes the largest evidence gap"],
            "verification_risk": ["Use synthetic records only"],
        },
        "short_article": {
            "draft": ["Record pricing units, limits, date, and source."],
        },
    }[mode]
    return {
        "processing_mode": mode,
        "title": f"Fictional {mode}",
        "summary": "Bounded fictional result.",
        "points": ["Fictional evidence point"],
        "why_it_matters": "This verifies the live response contract.",
        "sections": sections,
    }


class FictionalLiveBackend:
    def __init__(self, *, malformed_mode: str | None = None) -> None:
        self.requests: list[httpx.Request] = []
        self.records = {}
        self.malformed_mode = malformed_mode

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if request.headers.get("authorization") != f"Bearer {TOKEN}":
            return httpx.Response(
                401,
                json={"error": {"code": "AUTH_REQUIRED", "message": "Auth required."}},
            )
        if request.method == "POST" and request.url.path == "/api/v1/capture":
            payload = json.loads(request.content)
            mode = payload["requested_processing"]
            result = provider_result(mode)
            if mode == self.malformed_mode:
                result["unexpected"] = "must be rejected"
            index = len(self.records) + 1
            capture_id = f"{index:08d}-0000-4000-8000-{index:012d}"
            self.records[capture_id] = {
                "capture_id": capture_id,
                "status": "processed",
                "raw_content": payload["raw_content"],
                "requested_processing": mode,
                "result": result,
                "retry_count": 0,
                "created_at": f"2026-08-31T00:0{index}:00+00:00",
                "updated_at": f"2026-08-31T00:0{index}:00+00:00",
            }
            return httpx.Response(
                200,
                json={
                    "ok": True,
                    "capture_id": capture_id,
                    "status": "processed",
                    "result": {
                        "markdown": f"# Fictional {mode}",
                        "provider_result": result,
                        "extracted": None,
                    },
                    "error_code": None,
                    "message": None,
                },
            )
        if request.method == "GET" and request.url.path.startswith(
            "/api/v1/captures/"
        ):
            capture_id = request.url.path.rsplit("/", 1)[-1]
            return httpx.Response(200, json=self.records[capture_id])
        return httpx.Response(404, json={"error": "not found"})


class P15GeminiLiveSmokeTests(unittest.TestCase):
    def test_four_live_modes_use_fixed_payloads_and_return_sanitized_evidence(self) -> None:
        backend = FictionalLiveBackend()

        evidence = run_live_modes_smoke(
            base_url=BASE_URL,
            token=TOKEN,
            transport=httpx.MockTransport(backend),
        )

        self.assertTrue(evidence["ok"])
        self.assertEqual(
            list(evidence["modes"]),
            ["voice_structure", "summary", "recommendation", "short_article"],
        )
        for mode, result in evidence["modes"].items():
            with self.subTest(mode=mode):
                self.assertEqual(result["http_status"], 200)
                self.assertEqual(result["capture_status"], "processed")
                self.assertTrue(result["schema_valid"])
                self.assertTrue(result["markdown_generated"])
                self.assertTrue(result["raw_preserved"])
                self.assertGreaterEqual(result["duration_ms"], 0)
                UUID(result["capture_id"])
        self.assertEqual(
            evidence["operator_checks_pending"],
            ["runtime_gemini_config", "provider_trace", "server_logs"],
        )
        serialized = json.dumps(evidence, sort_keys=True)
        self.assertNotIn(TOKEN, serialized)
        for case in LIVE_CASES.values():
            self.assertNotIn(case["raw_content"], serialized)

        posts = [
            request
            for request in backend.requests
            if request.method == "POST" and request.url.path == "/api/v1/capture"
        ]
        self.assertEqual(len(posts), 4)
        for request, expected_mode in zip(posts, LIVE_CASES):
            payload = json.loads(request.content)
            self.assertEqual(payload["requested_processing"], expected_mode)
            self.assertEqual(payload["raw_content"], LIVE_CASES[expected_mode]["raw_content"])
            self.assertNotIn("provider", payload)
            self.assertNotIn("model", payload)
            self.assertNotIn("prompt", payload)

    def test_malformed_live_result_fails_without_echoing_response_or_secret(self) -> None:
        backend = FictionalLiveBackend(malformed_mode="short_article")

        with self.assertRaises(SmokeError) as caught:
            run_live_modes_smoke(
                base_url=BASE_URL,
                token=TOKEN,
                transport=httpx.MockTransport(backend),
            )

        message = str(caught.exception)
        self.assertIn("short_article", message)
        self.assertNotIn(TOKEN, message)
        self.assertNotIn("must be rejected", message)

    def test_cli_requires_explicit_four_write_confirmation(self) -> None:
        from tools.p1_5_gemini_live_smoke import main

        with patch(
            "tools.p1_5_gemini_live_smoke.run_live_modes_smoke"
        ) as runner, redirect_stderr(io.StringIO()):
            result = main(["--base-url", BASE_URL])

        self.assertEqual(result, 2)
        runner.assert_not_called()


if __name__ == "__main__":
    unittest.main()
