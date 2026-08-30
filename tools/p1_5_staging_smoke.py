#!/usr/bin/env python3
"""Run one explicit, fictional P1.5 MockProvider staging smoke flow."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Dict, Optional
from urllib.parse import urlsplit
from uuid import UUID

import httpx


FICTIONAL_RAW_CONTENT = (
    "今日完成 Project Alpha 嘅 CSV mapping，\n"
    "下一步要測 invalid URL，\n"
    "另外想到可以寫一篇 AI pricing short post。"
)
INVALID_TOKEN = "fictional-invalid-acceptance-token"
TIMEOUT_SECONDS = 15.0
SECURITY_HEADERS = {
    "cache-control": "no-store",
    "content-security-policy": "default-src 'self'; frame-ancestors 'none'",
    "referrer-policy": "no-referrer",
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
}


class SmokeError(RuntimeError):
    """Raised with a bounded message that excludes response bodies and secrets."""


def _origin(value: str, *, label: str) -> str:
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        raise SmokeError(
            f"{label} must be an exact HTTPS origin without credentials or path"
        )
    return value.rstrip("/")


def _token(value: str) -> str:
    if (
        len(value) < 16
        or value != value.strip()
        or any(char.isspace() for char in value)
    ):
        raise SmokeError("acceptance token must be at least 16 non-whitespace characters")
    return value


def _request(
    client: httpx.Client,
    method: str,
    path: str,
    *,
    step: str,
    headers: Optional[Dict[str, str]] = None,
    payload: Optional[dict] = None,
) -> httpx.Response:
    try:
        response = client.request(method, path, headers=headers, json=payload)
    except httpx.TimeoutException as exc:
        raise SmokeError(f"{step}: request timed out") from exc
    except httpx.RequestError as exc:
        raise SmokeError(f"{step}: network request failed") from exc
    if response.is_redirect:
        raise SmokeError(f"{step}: redirects are not accepted")
    return response


def _expect_status(response: httpx.Response, expected: int, *, step: str) -> None:
    if response.status_code != expected:
        raise SmokeError(
            f"{step}: expected HTTP {expected}, received {response.status_code}"
        )


def _json_object(response: httpx.Response, *, step: str) -> dict:
    try:
        payload = response.json()
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SmokeError(f"{step}: response was not valid JSON") from exc
    if not isinstance(payload, dict):
        raise SmokeError(f"{step}: response JSON must be an object")
    return payload


def _uuid(value: object, *, step: str) -> str:
    if not isinstance(value, str):
        raise SmokeError(f"{step}: capture_id was missing")
    try:
        parsed = UUID(value)
    except ValueError as exc:
        raise SmokeError(f"{step}: capture_id was not a UUID") from exc
    if str(parsed) != value:
        raise SmokeError(f"{step}: capture_id was not canonical")
    return value


def _check_security_headers(response: httpx.Response) -> bool:
    return all(
        response.headers.get(name) == value
        for name, value in SECURITY_HEADERS.items()
    )


def run_mock_staging_smoke(
    *,
    base_url: str,
    expected_origin: str,
    token: str,
    transport: Optional[httpx.BaseTransport] = None,
) -> dict:
    """Create two fictional records and return sanitized staging evidence.

    Calling this function performs external writes when ``transport`` is not a
    test double. The CLI therefore requires an explicit confirmation flag.
    """

    accepted_base = _origin(base_url, label="base URL")
    accepted_origin = _origin(expected_origin, label="expected origin")
    accepted_token = _token(token)
    authorization = {"Authorization": f"Bearer {accepted_token}"}
    with httpx.Client(
        base_url=accepted_base,
        timeout=TIMEOUT_SECONDS,
        follow_redirects=False,
        transport=transport,
    ) as client:
        health_response = _request(client, "GET", "/health", step="health")
        _expect_status(health_response, 200, step="health")
        health = _json_object(health_response, step="health")
        if health != {"ok": True, "status": "healthy"}:
            raise SmokeError("health: response contract mismatch")

        missing_auth = _request(
            client, "GET", "/api/v1/captures", step="missing auth"
        )
        _expect_status(missing_auth, 401, step="missing auth")
        missing_auth_body = _json_object(missing_auth, step="missing auth")
        if missing_auth_body.get("error", {}).get("code") != "AUTH_REQUIRED":
            raise SmokeError("missing auth: response contract mismatch")
        invalid_value = (
            "fictional-second-invalid-token"
            if accepted_token == INVALID_TOKEN
            else INVALID_TOKEN
        )
        invalid_auth = _request(
            client,
            "GET",
            "/api/v1/captures",
            step="invalid auth",
            headers={"Authorization": f"Bearer {invalid_value}"},
        )
        _expect_status(invalid_auth, 401, step="invalid auth")
        invalid_auth_body = _json_object(invalid_auth, step="invalid auth")
        if invalid_auth_body.get("error", {}).get("code") != "AUTH_REQUIRED":
            raise SmokeError("invalid auth: response contract mismatch")

        voice_payload = {
            "schema_version": "1",
            "capture_type": "voice",
            "source_type": "voice_transcript",
            "source": None,
            "raw_content": FICTIONAL_RAW_CONTENT,
            "requested_processing": "voice_structure",
            "allowed_projects": ["Project Alpha"],
        }
        capture_response = _request(
            client,
            "POST",
            "/api/v1/capture",
            step="processed capture",
            headers={**authorization, "Origin": accepted_origin},
            payload=voice_payload,
        )
        _expect_status(capture_response, 200, step="processed capture")
        capture = _json_object(capture_response, step="processed capture")
        capture_id = _uuid(capture.get("capture_id"), step="processed capture")
        if capture.get("status") != "processed" or capture.get("ok") is not True:
            raise SmokeError("processed capture: response contract mismatch")
        result = capture.get("result")
        markdown = result.get("markdown") if isinstance(result, dict) else None
        if not isinstance(markdown, str) or not markdown.strip():
            raise SmokeError("processed capture: Markdown was missing")
        cors_explicit = (
            capture_response.headers.get("access-control-allow-origin")
            == accepted_origin
        )
        if not cors_explicit:
            raise SmokeError("processed capture: expected CORS origin was not allowed")
        security_headers = _check_security_headers(capture_response)
        if not security_headers:
            raise SmokeError("processed capture: required security headers were missing")

        stored_response = _request(
            client,
            "GET",
            f"/api/v1/captures/{capture_id}",
            step="stored capture",
            headers=authorization,
        )
        _expect_status(stored_response, 200, step="stored capture")
        stored = _json_object(stored_response, step="stored capture")
        if stored.get("raw_content") != FICTIONAL_RAW_CONTENT:
            raise SmokeError("stored capture: raw content was not preserved")

        review_response = _request(
            client,
            "PATCH",
            f"/api/v1/captures/{capture_id}",
            step="review",
            headers=authorization,
            payload={"reviewed": True, "assigned_project": "Project Alpha"},
        )
        _expect_status(review_response, 200, step="review")
        reviewed = _json_object(review_response, step="review")
        if (
            reviewed.get("reviewed") is not True
            or reviewed.get("assigned_project") != "Project Alpha"
        ):
            raise SmokeError("review: response contract mismatch")

        pending_response = _request(
            client,
            "POST",
            "/api/v1/capture",
            step="pending capture",
            headers=authorization,
            payload={
                "schema_version": "1",
                "capture_type": "content",
                "source_type": "video_url",
                "source": "https://example.com/fictional-video",
                "raw_content": "",
                "requested_processing": "summary",
                "allowed_projects": [],
            },
        )
        _expect_status(pending_response, 202, step="pending capture")
        pending = _json_object(pending_response, step="pending capture")
        pending_id = _uuid(pending.get("capture_id"), step="pending capture")
        if pending.get("status") != "pending":
            raise SmokeError("pending capture: response contract mismatch")

        retry_response = _request(
            client,
            "POST",
            f"/api/v1/captures/{pending_id}/retry",
            step="manual retry",
            headers=authorization,
        )
        _expect_status(retry_response, 202, step="manual retry")
        retry = _json_object(retry_response, step="manual retry")
        if retry.get("status") != "pending":
            raise SmokeError("manual retry: response contract mismatch")

        list_response = _request(
            client,
            "GET",
            "/api/v1/captures?page=1&page_size=10",
            step="inbox list",
            headers=authorization,
        )
        _expect_status(list_response, 200, step="inbox list")
        listing = _json_object(list_response, step="inbox list")
        items = listing.get("data")
        listed_ids = (
            [item.get("capture_id") for item in items if isinstance(item, dict)]
            if isinstance(items, list)
            else []
        )
        if listed_ids.count(capture_id) != 1:
            raise SmokeError("inbox list: processed capture was missing")
        if any("raw_content" in item for item in items if isinstance(item, dict)):
            raise SmokeError("inbox list: raw content was unexpectedly exposed")

        disallowed_cors = _request(
            client,
            "GET",
            "/api/v1/captures?page=1&page_size=10",
            step="disallowed CORS",
            headers={**authorization, "Origin": "https://not-allowed.example"},
        )
        _expect_status(disallowed_cors, 200, step="disallowed CORS")
        if disallowed_cors.headers.get("access-control-allow-origin"):
            raise SmokeError("disallowed CORS: unexpected origin was allowed")

        pending_list_response = _request(
            client,
            "GET",
            "/api/v1/captures?page=1&page_size=10&status=pending",
            step="pending list",
            headers=authorization,
        )
        _expect_status(pending_list_response, 200, step="pending list")
        pending_list = _json_object(pending_list_response, step="pending list")
        pending_items = pending_list.get("data")
        if not isinstance(pending_items, list) or pending_id not in {
            item.get("capture_id") for item in pending_items if isinstance(item, dict)
        }:
            raise SmokeError("pending list: pending capture was missing")

        today_response = _request(
            client,
            "GET",
            "/api/v1/dashboard/today",
            step="today",
            headers=authorization,
        )
        _expect_status(today_response, 200, step="today")
        today = _json_object(today_response, step="today")
        recent = today.get("recent_captures")
        if not isinstance(recent, list) or capture_id not in {
            item.get("capture_id") for item in recent if isinstance(item, dict)
        }:
            raise SmokeError("today: response contract mismatch")

        projects_response = _request(
            client,
            "GET",
            "/api/v1/projects",
            step="projects",
            headers=authorization,
        )
        _expect_status(projects_response, 200, step="projects")
        projects = _json_object(projects_response, step="projects")
        project_items = projects.get("data")
        if not isinstance(project_items, list) or "Project Alpha" not in {
            item.get("project") for item in project_items if isinstance(item, dict)
        }:
            raise SmokeError("projects: response contract mismatch")

        report_response = _request(
            client,
            "POST",
            "/api/v1/reports/preview",
            step="report preview",
            headers=authorization,
            payload={
                "report_type": "daily",
                "period": "Fictional staging smoke",
                "capture_ids": [capture_id],
            },
        )
        _expect_status(report_response, 200, step="report preview")
        report = _json_object(report_response, step="report preview")
        if (
            not isinstance(report.get("markdown"), str)
            or report.get("sent") is not False
            or report.get("published") is not False
        ):
            raise SmokeError("report preview: response contract mismatch")

        web_response = _request(client, "GET", "/app/", step="Web shell")
        _expect_status(web_response, 200, step="Web shell")
        if "text/html" not in web_response.headers.get("content-type", ""):
            raise SmokeError("Web shell: HTML content type was missing")

        for disabled_path in ("/openapi.json", "/docs", "/redoc"):
            disabled_response = _request(
                client, "GET", disabled_path, step="disabled API documentation"
            )
            _expect_status(disabled_response, 404, step="disabled API documentation")

        pending_stored_response = _request(
            client,
            "GET",
            f"/api/v1/captures/{pending_id}",
            step="stored pending capture",
            headers=authorization,
        )
        _expect_status(pending_stored_response, 200, step="stored pending capture")
        pending_stored = _json_object(
            pending_stored_response, step="stored pending capture"
        )
        if pending_stored.get("retry_count") != 1:
            raise SmokeError("stored pending capture: retry count mismatch")

    return {
        "ok": True,
        "suite": "p1_5_mock_staging_smoke",
        "base_origin": accepted_base,
        "health_http": health_response.status_code,
        "auth_fails_closed": True,
        "capture_http": capture_response.status_code,
        "capture_id": capture_id,
        "capture_status": capture["status"],
        "markdown_returned": True,
        "raw_preserved": True,
        "pending_capture_id": pending_id,
        "retry_http": retry_response.status_code,
        "retry_status": retry["status"],
        "cors_explicit": cors_explicit,
        "security_headers": security_headers,
        "today_api": True,
        "inbox_api": True,
        "projects_api": True,
        "pending_api": True,
        "reports_api": True,
        "web_shell": True,
        "api_docs_disabled": True,
        "restart_reference": {
            "processed_capture_id": capture_id,
            "processed_created_at": stored.get("created_at"),
            "processed_updated_at": reviewed.get("updated_at"),
            "pending_capture_id": pending_id,
            "pending_created_at": pending_stored.get("created_at"),
            "pending_updated_at": pending_stored.get("updated_at"),
            "pending_retry_count": pending_stored.get("retry_count"),
        },
        "operator_checks_pending": [
            "runtime_config",
            "server_logs",
            "service_restart",
            "persistent_disk",
            "rate_limits",
            "device",
            "p1_4_fallback",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Create two fixed fictional records and verify the P1.5 Mock staging API."
        )
    )
    parser.add_argument(
        "--base-url", required=True, help="Exact HTTPS staging origin."
    )
    parser.add_argument(
        "--expected-origin",
        required=True,
        help="Exact HTTPS origin that staging CORS must allow.",
    )
    parser.add_argument(
        "--confirm-fictional-write",
        action="store_true",
        help="Required acknowledgement that the smoke creates two fictional records.",
    )
    args = parser.parse_args()
    if not args.confirm_fictional_write:
        parser.error("--confirm-fictional-write is required")
    token = os.environ.get("P1_5_ACCEPTANCE_TOKEN", "")
    try:
        evidence = run_mock_staging_smoke(
            base_url=args.base_url,
            expected_origin=args.expected_origin,
            token=token,
        )
    except SmokeError as exc:
        print(f"Staging smoke failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(evidence, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
