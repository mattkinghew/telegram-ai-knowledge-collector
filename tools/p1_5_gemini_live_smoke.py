#!/usr/bin/env python3
"""Run the four explicit, fictional P1.5 live-Gemini staging smokes."""

from __future__ import annotations

import argparse
import json
import os
import sys
from time import monotonic
from typing import Dict, Optional

import httpx
from pydantic import ValidationError

from backend.models import ProviderResult

try:
    from tools.p1_5_staging_smoke import (
        SmokeError,
        TIMEOUT_SECONDS,
        _expect_status,
        _json_object,
        _origin,
        _request,
        _token,
        _uuid,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from p1_5_staging_smoke import (  # type: ignore[no-redef]
        SmokeError,
        TIMEOUT_SECONDS,
        _expect_status,
        _json_object,
        _origin,
        _request,
        _token,
        _uuid,
    )


LIVE_CASES: Dict[str, dict] = {
    "voice_structure": {
        "capture_type": "voice",
        "source_type": "voice_transcript",
        "raw_content": (
            "今日完成 Project Alpha 嘅 CSV mapping，\n"
            "下一步要測 invalid URL，\n"
            "另外想到可以寫一篇 AI pricing short post。"
        ),
        "allowed_projects": ["Project Alpha"],
    },
    "summary": {
        "capture_type": "content",
        "source_type": "selected_text",
        "raw_content": (
            "Project Lantern is a fictional school workshop pilot. The team "
            "tested one CSV mapping with synthetic records. The pilot has not "
            "been deployed. The next review will compare invalid-row handling "
            "with the documented acceptance rules."
        ),
        "allowed_projects": [],
    },
    "recommendation": {
        "capture_type": "content",
        "source_type": "selected_text",
        "raw_content": (
            "Project Cedar is fictional. The team has two prototype import "
            "paths and only three hours for validation. One path is already "
            "covered by synthetic tests; the other has no evidence. Recommend "
            "the smallest next validation step."
        ),
        "allowed_projects": [],
    },
    "short_article": {
        "capture_type": "content",
        "source_type": "selected_text",
        "raw_content": (
            "Fictional source note: AI pricing comparisons are easier to review "
            "when the author records the unit, included limits, date checked, "
            "and source link. Prices can change, so the draft must avoid "
            "claiming that a snapshot is permanent."
        ),
        "allowed_projects": [],
    },
}
FAILURE_RAW_CONTENT = (
    "FICTIONAL-LIVE-FAILURE-01: Project Harbor uses synthetic records only. "
    "Summarize the recorded validation boundary."
)
SAFE_LIVE_FAILURE_CODES = frozenset(
    {"AI_TIMEOUT", "AI_UNAVAILABLE", "AI_RATE_LIMITED", "AI_AUTH_FAILED"}
)


def _strict_provider_result(value: object, *, mode: str) -> ProviderResult:
    if not isinstance(value, dict):
        raise SmokeError(f"{mode}: provider result was missing")
    try:
        parsed = ProviderResult.model_validate(value)
    except ValidationError as exc:
        raise SmokeError(f"{mode}: provider result failed strict validation") from exc
    if parsed.processing_mode != mode:
        raise SmokeError(f"{mode}: provider result mode mismatch")
    return parsed


def run_live_modes_smoke(
    *,
    base_url: str,
    token: str,
    transport: Optional[httpx.BaseTransport] = None,
) -> dict:
    """Write four fixed fictional captures and return sanitized evidence."""

    accepted_base = _origin(base_url, label="base URL")
    accepted_token = _token(token)
    authorization = {"Authorization": f"Bearer {accepted_token}"}
    evidence: Dict[str, dict] = {}

    with httpx.Client(
        base_url=accepted_base,
        timeout=TIMEOUT_SECONDS,
        follow_redirects=False,
        transport=transport,
    ) as client:
        for mode, case in LIVE_CASES.items():
            payload = {
                "schema_version": "1",
                "capture_type": case["capture_type"],
                "source_type": case["source_type"],
                "source": None,
                "raw_content": case["raw_content"],
                "requested_processing": mode,
                "allowed_projects": case["allowed_projects"],
            }
            started = monotonic()
            response = _request(
                client,
                "POST",
                "/api/v1/capture",
                step=mode,
                headers=authorization,
                payload=payload,
            )
            duration_ms = round((monotonic() - started) * 1_000)
            _expect_status(response, 200, step=mode)
            body = _json_object(response, step=mode)
            capture_id = _uuid(body.get("capture_id"), step=mode)
            if body.get("ok") is not True or body.get("status") != "processed":
                raise SmokeError(f"{mode}: processed response contract mismatch")
            result = body.get("result")
            if not isinstance(result, dict):
                raise SmokeError(f"{mode}: result was missing")
            markdown = result.get("markdown")
            if not isinstance(markdown, str) or not markdown.strip():
                raise SmokeError(f"{mode}: Markdown was missing")
            _strict_provider_result(result.get("provider_result"), mode=mode)

            stored_response = _request(
                client,
                "GET",
                f"/api/v1/captures/{capture_id}",
                step=f"{mode} stored capture",
                headers=authorization,
            )
            _expect_status(stored_response, 200, step=f"{mode} stored capture")
            stored = _json_object(stored_response, step=f"{mode} stored capture")
            if (
                stored.get("status") != "processed"
                or stored.get("requested_processing") != mode
            ):
                raise SmokeError(f"{mode}: stored capture contract mismatch")
            if stored.get("raw_content") != case["raw_content"]:
                raise SmokeError(f"{mode}: raw content was not preserved")
            stored_result = stored.get("result")
            if isinstance(stored_result, dict) and "provider_result" in stored_result:
                stored_result = stored_result["provider_result"]
            _strict_provider_result(stored_result, mode=mode)

            evidence[mode] = {
                "http_status": response.status_code,
                "capture_id": capture_id,
                "capture_status": "processed",
                "schema_valid": True,
                "markdown_generated": True,
                "raw_preserved": True,
                "duration_ms": duration_ms,
            }

    return {
        "ok": True,
        "modes": evidence,
        "operator_checks_pending": [
            "runtime_gemini_config",
            "provider_trace",
            "server_logs",
        ],
    }


def run_live_failure_smoke(
    *,
    base_url: str,
    token: str,
    transport: Optional[httpx.BaseTransport] = None,
) -> dict:
    """Create one fixed fictional capture while failure is operator-controlled."""

    accepted_base = _origin(base_url, label="base URL")
    accepted_token = _token(token)
    authorization = {"Authorization": f"Bearer {accepted_token}"}
    payload = {
        "schema_version": "1",
        "capture_type": "content",
        "source_type": "selected_text",
        "source": None,
        "raw_content": FAILURE_RAW_CONTENT,
        "requested_processing": "summary",
        "allowed_projects": [],
    }
    with httpx.Client(
        base_url=accepted_base,
        timeout=TIMEOUT_SECONDS,
        follow_redirects=False,
        transport=transport,
    ) as client:
        response = _request(
            client,
            "POST",
            "/api/v1/capture",
            step="controlled failure",
            headers=authorization,
            payload=payload,
        )
        _expect_status(response, 202, step="controlled failure")
        body = _json_object(response, step="controlled failure")
        capture_id = _uuid(body.get("capture_id"), step="controlled failure")
        error_code = body.get("error_code")
        if (
            body.get("ok") is not False
            or body.get("status") != "pending"
            or body.get("result") is not None
            or error_code not in SAFE_LIVE_FAILURE_CODES
        ):
            raise SmokeError("controlled failure: pending response contract mismatch")

        stored_response = _request(
            client,
            "GET",
            f"/api/v1/captures/{capture_id}",
            step="stored controlled failure",
            headers=authorization,
        )
        _expect_status(stored_response, 200, step="stored controlled failure")
        stored = _json_object(stored_response, step="stored controlled failure")
        if (
            stored.get("status") != "pending"
            or stored.get("requested_processing") != "summary"
            or stored.get("raw_content") != FAILURE_RAW_CONTENT
            or stored.get("result") is not None
            or stored.get("markdown") is not None
            or stored.get("error_code") != error_code
            or stored.get("retry_count") != 0
        ):
            raise SmokeError("controlled failure: stored capture contract mismatch")

    return {
        "ok": True,
        "http_status": response.status_code,
        "capture_id": capture_id,
        "capture_status": "pending",
        "error_code": error_code,
        "raw_preserved": True,
        "manual_retry_available": True,
        "retry_count": 0,
        "operator_checks_pending": ["provider_restored", "server_logs"],
    }


def run_live_retry_smoke(
    *,
    base_url: str,
    token: str,
    capture_id: str,
    transport: Optional[httpx.BaseTransport] = None,
) -> dict:
    """Perform exactly one manual retry of the fixed fictional failure capture."""

    accepted_base = _origin(base_url, label="base URL")
    accepted_token = _token(token)
    accepted_capture_id = _uuid(capture_id, step="manual retry")
    authorization = {"Authorization": f"Bearer {accepted_token}"}
    with httpx.Client(
        base_url=accepted_base,
        timeout=TIMEOUT_SECONDS,
        follow_redirects=False,
        transport=transport,
    ) as client:
        response = _request(
            client,
            "POST",
            f"/api/v1/captures/{accepted_capture_id}/retry",
            step="manual retry",
            headers=authorization,
        )
        _expect_status(response, 200, step="manual retry")
        body = _json_object(response, step="manual retry")
        response_id = _uuid(body.get("capture_id"), step="manual retry")
        if response_id != accepted_capture_id:
            raise SmokeError("manual retry: capture_id changed")
        if body.get("ok") is not True or body.get("status") != "processed":
            raise SmokeError("manual retry: processed response contract mismatch")
        result = body.get("result")
        if not isinstance(result, dict):
            raise SmokeError("manual retry: result was missing")
        markdown = result.get("markdown")
        if not isinstance(markdown, str) or not markdown.strip():
            raise SmokeError("manual retry: Markdown was missing")
        _strict_provider_result(result.get("provider_result"), mode="summary")

        stored_response = _request(
            client,
            "GET",
            f"/api/v1/captures/{accepted_capture_id}",
            step="stored manual retry",
            headers=authorization,
        )
        _expect_status(stored_response, 200, step="stored manual retry")
        stored = _json_object(stored_response, step="stored manual retry")
        if (
            stored.get("status") != "processed"
            or stored.get("requested_processing") != "summary"
            or stored.get("raw_content") != FAILURE_RAW_CONTENT
            or stored.get("retry_count") != 1
        ):
            raise SmokeError("manual retry: stored capture contract mismatch")
        stored_result = stored.get("result")
        if isinstance(stored_result, dict) and "provider_result" in stored_result:
            stored_result = stored_result["provider_result"]
        _strict_provider_result(stored_result, mode="summary")

    return {
        "ok": True,
        "http_status": response.status_code,
        "capture_id": accepted_capture_id,
        "capture_status": "processed",
        "schema_valid": True,
        "markdown_generated": True,
        "raw_preserved": True,
        "retry_count": 1,
        "operator_checks_pending": ["server_logs"],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Write exactly four fixed fictional captures to an already-enabled "
            "P1.5 live-Gemini staging service."
        )
    )
    parser.add_argument("--base-url", required=True, help="Exact staging HTTPS origin")
    parser.add_argument(
        "--confirm-four-fictional-writes",
        action="store_true",
        help="Confirm the four fixed fictional staging writes",
    )
    parser.add_argument(
        "--controlled-failure",
        action="store_true",
        help="Create only the fixed fictional provider-failure capture",
    )
    parser.add_argument(
        "--confirm-fictional-failure-write",
        action="store_true",
        help="Confirm the single fixed fictional failure write",
    )
    parser.add_argument(
        "--retry-capture-id",
        help="Retry only a UUID returned by the controlled failure phase",
    )
    parser.add_argument(
        "--confirm-manual-retry",
        action="store_true",
        help="Confirm exactly one manual retry of the supplied capture UUID",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = _parser().parse_args(argv)
    if args.retry_capture_id:
        if args.controlled_failure or not args.confirm_manual_retry:
            print(
                "Refusing retry without an exclusive --retry-capture-id and "
                "--confirm-manual-retry.",
                file=sys.stderr,
            )
            return 2
        runner = lambda token: run_live_retry_smoke(
            base_url=args.base_url,
            token=token,
            capture_id=args.retry_capture_id,
        )
    elif args.controlled_failure:
        if not args.confirm_fictional_failure_write:
            print(
                "Refusing failure write without "
                "--confirm-fictional-failure-write.",
                file=sys.stderr,
            )
            return 2
        runner = lambda token: run_live_failure_smoke(
            base_url=args.base_url,
            token=token,
        )
    elif not args.confirm_four_fictional_writes:
        print(
            "Refusing writes without --confirm-four-fictional-writes.",
            file=sys.stderr,
        )
        return 2
    else:
        runner = lambda token: run_live_modes_smoke(
            base_url=args.base_url,
            token=token,
        )
    token = os.environ.get("P1_5_ACCEPTANCE_TOKEN", "")
    try:
        evidence = runner(token)
    except SmokeError as exc:
        print(f"Live Gemini smoke failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(evidence, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
