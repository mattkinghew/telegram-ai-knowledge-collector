from __future__ import annotations

import json
import io
import sys
import unittest
from contextlib import redirect_stderr
from unittest.mock import patch
from uuid import UUID

import httpx

from tools.p1_5_staging_smoke import (
    FICTIONAL_RAW_CONTENT,
    SmokeError,
    run_mock_staging_smoke,
)


BASE_URL = "https://p1-5-staging.example"
ORIGIN = "https://p1-5-staging.example"
TOKEN = "fictional-staging-acceptance-token"
PROCESSED_ID = "11111111-1111-4111-8111-111111111111"
PENDING_ID = "22222222-2222-4222-8222-222222222222"


class FictionalStagingAPI:
    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.processed = None
        self.pending = None

    @staticmethod
    def _headers(request: httpx.Request) -> dict[str, str]:
        headers = {
            "cache-control": "no-store",
            "content-security-policy": "default-src 'self'; frame-ancestors 'none'",
            "referrer-policy": "no-referrer",
            "x-content-type-options": "nosniff",
            "x-frame-options": "DENY",
        }
        if request.headers.get("origin") == ORIGIN:
            headers["access-control-allow-origin"] = ORIGIN
        return headers

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path
        headers = self._headers(request)

        if path == "/health":
            return httpx.Response(200, headers=headers, json={"ok": True, "status": "healthy"})
        if path in {"/openapi.json", "/docs", "/redoc"}:
            return httpx.Response(404, headers=headers, json={"error": "not found"})
        if path == "/app/":
            return httpx.Response(
                200,
                headers={**headers, "content-type": "text/html; charset=utf-8"},
                text="<!doctype html><title>P1.5</title>",
            )

        authorization = request.headers.get("authorization")
        if authorization != f"Bearer {TOKEN}":
            return httpx.Response(
                401,
                headers=headers,
                json={"error": {"code": "AUTH_REQUIRED", "message": "Auth required."}},
            )

        if request.method == "POST" and path == "/api/v1/capture":
            payload = json.loads(request.content)
            if payload["capture_type"] == "voice":
                self.processed = {
                    "capture_id": PROCESSED_ID,
                    "status": "processed",
                    "raw_content": payload["raw_content"],
                    "retry_count": 0,
                    "reviewed": False,
                    "assigned_project": None,
                    "created_at": "2026-08-31T00:00:00+00:00",
                    "updated_at": "2026-08-31T00:00:00+00:00",
                }
                return httpx.Response(
                    200,
                    headers=headers,
                    json={
                        "ok": True,
                        "capture_id": PROCESSED_ID,
                        "status": "processed",
                        "result": {"markdown": "# Fictional\n\n" + payload["raw_content"]},
                        "error_code": None,
                        "message": None,
                    },
                )
            self.pending = {
                "capture_id": PENDING_ID,
                "status": "pending",
                "raw_content": "",
                "retry_count": 0,
                "reviewed": False,
                "assigned_project": None,
                "created_at": "2026-08-31T00:01:00+00:00",
                "updated_at": "2026-08-31T00:01:00+00:00",
            }
            return httpx.Response(
                202,
                headers=headers,
                json={
                    "ok": False,
                    "capture_id": PENDING_ID,
                    "status": "pending",
                    "result": None,
                    "error_code": "URL_FETCH_FAILED",
                    "message": "Source content is unavailable.",
                },
            )

        if request.method == "GET" and path == f"/api/v1/captures/{PROCESSED_ID}":
            return httpx.Response(200, headers=headers, json=self.processed)
        if request.method == "GET" and path == f"/api/v1/captures/{PENDING_ID}":
            return httpx.Response(200, headers=headers, json=self.pending)
        if request.method == "PATCH" and path == f"/api/v1/captures/{PROCESSED_ID}":
            self.processed.update(json.loads(request.content))
            self.processed["updated_at"] = "2026-08-31T00:02:00+00:00"
            return httpx.Response(200, headers=headers, json=self.processed)
        if request.method == "POST" and path == f"/api/v1/captures/{PENDING_ID}/retry":
            self.pending["retry_count"] = 1
            return httpx.Response(
                202,
                headers=headers,
                json={
                    "ok": False,
                    "capture_id": PENDING_ID,
                    "status": "pending",
                    "result": None,
                    "error_code": "URL_FETCH_FAILED",
                    "message": "Source content is unavailable.",
                },
            )
        if request.method == "GET" and path == "/api/v1/captures":
            items = [self.processed, self.pending] if self.processed and self.pending else []
            status = request.url.params.get("status")
            if status:
                items = [item for item in items if item["status"] == status]
            redacted = [
                {key: value for key, value in item.items() if key != "raw_content"}
                for item in items
            ]
            return httpx.Response(
                200,
                headers=headers,
                json={
                    "data": redacted,
                    "pagination": {
                        "page": 1,
                        "page_size": 10,
                        "total_items": len(redacted),
                        "total_pages": 1,
                    },
                },
            )
        if request.method == "GET" and path == "/api/v1/dashboard/today":
            return httpx.Response(
                200,
                headers=headers,
                json={
                    "recent_captures": [
                        {"capture_id": PROCESSED_ID},
                        {"capture_id": PENDING_ID},
                    ],
                    "recent_project_progress": [],
                    "next_actions": [],
                    "pending_count": 1,
                    "failed_count": 0,
                },
            )
        if request.method == "GET" and path == "/api/v1/projects":
            return httpx.Response(
                200,
                headers=headers,
                json={"data": [{"project": "Project Alpha"}], "limit": 100},
            )
        if request.method == "POST" and path == "/api/v1/reports/preview":
            return httpx.Response(
                200,
                headers=headers,
                json={
                    "report_type": "daily",
                    "period": "Fictional staging smoke",
                    "selected_capture_ids": [PROCESSED_ID],
                    "markdown": "# Fictional staging report",
                    "sent": False,
                    "published": False,
                },
            )
        return httpx.Response(404, headers=headers, json={"error": "not found"})


class P15StagingSmokeTests(unittest.TestCase):
    def test_mock_staging_flow_returns_sanitized_evidence(self) -> None:
        api = FictionalStagingAPI()

        evidence = run_mock_staging_smoke(
            base_url=BASE_URL,
            expected_origin=ORIGIN,
            token=TOKEN,
            transport=httpx.MockTransport(api),
        )

        self.assertTrue(evidence["ok"])
        self.assertEqual(evidence["capture_id"], PROCESSED_ID)
        self.assertEqual(evidence["pending_capture_id"], PENDING_ID)
        self.assertEqual(evidence["capture_status"], "processed")
        self.assertEqual(evidence["retry_status"], "pending")
        self.assertTrue(evidence["raw_preserved"])
        self.assertTrue(evidence["markdown_returned"])
        self.assertTrue(evidence["auth_fails_closed"])
        self.assertTrue(evidence["cors_explicit"])
        self.assertTrue(evidence["security_headers"])
        self.assertTrue(evidence["today_api"])
        self.assertTrue(evidence["inbox_api"])
        self.assertTrue(evidence["projects_api"])
        self.assertTrue(evidence["pending_api"])
        self.assertTrue(evidence["reports_api"])
        self.assertTrue(evidence["web_shell"])
        self.assertEqual(
            evidence["operator_checks_pending"],
            [
                "runtime_config",
                "server_logs",
                "service_restart",
                "persistent_disk",
                "rate_limits",
                "device",
                "p1_4_fallback",
            ],
        )
        serialized = json.dumps(evidence, sort_keys=True)
        self.assertNotIn(TOKEN, serialized)
        self.assertNotIn(FICTIONAL_RAW_CONTENT, serialized)
        UUID(evidence["capture_id"])

        capture_requests = [
            request
            for request in api.requests
            if request.method == "POST" and request.url.path == "/api/v1/capture"
        ]
        self.assertEqual(len(capture_requests), 2)
        voice_payload = json.loads(capture_requests[0].content)
        self.assertEqual(voice_payload["raw_content"], FICTIONAL_RAW_CONTENT)
        self.assertNotIn("provider", voice_payload)
        self.assertNotIn("model", voice_payload)

    def test_invalid_target_or_token_fails_before_transport_call(self) -> None:
        calls = []

        def unexpected(request: httpx.Request) -> httpx.Response:
            calls.append(request)
            return httpx.Response(500)

        transport = httpx.MockTransport(unexpected)
        invalid_cases = (
            {"base_url": "http://staging.example", "expected_origin": ORIGIN, "token": TOKEN},
            {
                "base_url": "https://user@staging.example",
                "expected_origin": ORIGIN,
                "token": TOKEN,
            },
            {"base_url": BASE_URL + "/api", "expected_origin": ORIGIN, "token": TOKEN},
            {"base_url": BASE_URL, "expected_origin": "*", "token": TOKEN},
            {"base_url": BASE_URL, "expected_origin": ORIGIN, "token": "short"},
            {"base_url": BASE_URL, "expected_origin": ORIGIN, "token": TOKEN + "\n"},
        )
        for case in invalid_cases:
            with self.subTest(case=case):
                with self.assertRaises(SmokeError):
                    run_mock_staging_smoke(**case, transport=transport)
        self.assertEqual(calls, [])

    def test_response_contract_failure_does_not_echo_secret_or_raw_content(self) -> None:
        def malformed(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/health":
                return httpx.Response(
                    200,
                    json={
                        "ok": False,
                        "leak": TOKEN + FICTIONAL_RAW_CONTENT,
                    },
                )
            raise AssertionError("health failure must stop the smoke flow")

        with self.assertRaises(SmokeError) as caught:
            run_mock_staging_smoke(
                base_url=BASE_URL,
                expected_origin=ORIGIN,
                token=TOKEN,
                transport=httpx.MockTransport(malformed),
            )
        message = str(caught.exception)
        self.assertNotIn(TOKEN, message)
        self.assertNotIn(FICTIONAL_RAW_CONTENT, message)

    def test_redirect_is_rejected_without_following_location(self) -> None:
        requests = []

        def redirect(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(
                307,
                headers={"location": "https://not-the-staging-host.example/health"},
            )

        with self.assertRaisesRegex(SmokeError, "redirects are not accepted"):
            run_mock_staging_smoke(
                base_url=BASE_URL,
                expected_origin=ORIGIN,
                token=TOKEN,
                transport=httpx.MockTransport(redirect),
            )
        self.assertEqual(len(requests), 1)

    def test_cli_requires_explicit_write_confirmation_before_runner_call(self) -> None:
        argv = [
            "p1_5_staging_smoke.py",
            "--base-url",
            BASE_URL,
            "--expected-origin",
            ORIGIN,
        ]
        with patch.object(sys, "argv", argv), patch(
            "tools.p1_5_staging_smoke.run_mock_staging_smoke"
        ) as runner:
            from tools.p1_5_staging_smoke import main

            with redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as caught:
                    main()
        self.assertEqual(caught.exception.code, 2)
        runner.assert_not_called()


if __name__ == "__main__":
    unittest.main()
