#!/usr/bin/env python3
"""Run one bounded fictional authenticated deployment smoke test.

This script is intentionally user-run only.  It reads the API token from the
macOS Keychain for the current account, never prints it, and never reads a
Gemini key.  The backend LaunchAgent owns the Gemini runtime secret.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Optional


BASE_URL = "https://capture.lamlab.cc"
KEYCHAIN_SERVICE = "com.business-knowledge-capture.p1-5.api-auth-token"
POLL_INTERVAL_SECONDS = 2
MAX_POLL_ATTEMPTS = 15
HANDOFF_FIELDS = {
    "markdown",
    "suggested_filename",
    "suggested_date",
    "record_type",
    "title",
    "folder_key",
}


def fictional_payload() -> dict[str, Any]:
    """Return the fixed public-safe payload used by this acceptance test."""
    return {
        "schema_version": "1",
        "capture_type": "voice",
        "source_type": "voice_transcript",
        "source": None,
        "raw_content": (
            "Fictional Project Aurora completed CSV mapping; next action is to "
            "test an invalid URL; idea: write a short AI pricing post."
        ),
        "requested_processing": "voice_structure",
        "record_type": "free",
        "allowed_projects": [],
    }


def handoff_is_complete(result: object) -> bool:
    if not isinstance(result, dict):
        return False
    handoff = result.get("obsidian_handoff")
    return isinstance(handoff, dict) and HANDOFF_FIELDS.issubset(handoff)


def _keychain_token() -> str:
    account = subprocess.check_output(["/usr/bin/id", "-un"], text=True).strip()
    return subprocess.check_output(
        [
            "/usr/bin/security",
            "find-generic-password",
            "-s",
            KEYCHAIN_SERVICE,
            "-a",
            account,
            "-w",
        ],
        text=True,
        stderr=subprocess.DEVNULL,
    ).strip()


def _request(
    path: str,
    method: str,
    token: str,
    body: Optional[dict[str, Any]] = None,
) -> tuple[int, dict[str, Any]]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
    }
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        f"{BASE_URL}{path}", data=data, headers=headers, method=method
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            payload = json.loads(response.read())
            return response.status, payload if isinstance(payload, dict) else {}
    except urllib.error.HTTPError as error:
        try:
            payload = json.loads(error.read())
        except (ValueError, TypeError):
            payload = {}
        return error.code, payload if isinstance(payload, dict) else {}


def run() -> int:
    try:
        token = _keychain_token()
    except (OSError, subprocess.SubprocessError):
        print("ERROR_CODE=KEYCHAIN_UNAVAILABLE")
        print("AUTHENTICATED_SMOKE=FAIL")
        return 1
    if len(token) < 16:
        print("ERROR_CODE=AUTH_CONFIG_INVALID")
        print("AUTHENTICATED_SMOKE=FAIL")
        return 1

    try:
        post_status, initial = _request(
            "/api/v1/capture", "POST", token, fictional_payload()
        )
    except (OSError, urllib.error.URLError):
        print("ERROR_CODE=NETWORK_ERROR")
        print("AUTHENTICATED_SMOKE=FAIL")
        return 1

    capture_id = initial.get("capture_id")
    print(f"POST_HTTP_STATUS={post_status}")
    print(f"CAPTURE_ID={capture_id if isinstance(capture_id, str) else 'MISSING'}")
    print(f"INITIAL_STATUS={initial.get('status', 'unknown')}")
    if post_status != 202 or not isinstance(capture_id, str):
        print(f"ERROR_CODE={initial.get('error_code', 'CAPTURE_REJECTED')}")
        print("AUTHENTICATED_SMOKE=FAIL")
        return 1

    for attempt in range(1, MAX_POLL_ATTEMPTS + 1):
        time.sleep(POLL_INTERVAL_SECONDS)
        try:
            status, payload = _request(
                f"/api/v1/captures/{capture_id}", "GET", token
            )
        except (OSError, urllib.error.URLError):
            print(f"POLL_ATTEMPTS={attempt}")
            print("FINAL_STATUS=failed")
            print("ERROR_CODE=NETWORK_ERROR")
            print("AUTHENTICATED_SMOKE=FAIL")
            return 1
        state = payload.get("status", "unknown")
        if state not in {"processed", "failed"}:
            continue

        result = payload.get("result")
        markdown_present = isinstance(result, dict) and bool(result.get("markdown"))
        handoff_present = isinstance(result, dict) and isinstance(
            result.get("obsidian_handoff"), dict
        )
        print(f"POLL_ATTEMPTS={attempt}")
        print(f"FINAL_STATUS={state}")
        print(f"ERROR_CODE={payload.get('error_code')}")
        print("PROVIDER=gemini")
        print(f"MARKDOWN_PRESENT={'PASS' if markdown_present else 'FAIL'}")
        print(f"OBSIDIAN_HANDOFF_PRESENT={'PASS' if handoff_present else 'FAIL'}")
        print(f"HANDOFF_FIELDS={'PASS' if handoff_is_complete(result) else 'FAIL'}")
        passed = state == "processed" and markdown_present and handoff_is_complete(result)
        print(f"AUTHENTICATED_SMOKE={'PASS' if passed else 'FAIL'}")
        return 0 if passed else 1

    print(f"POLL_ATTEMPTS={MAX_POLL_ATTEMPTS}")
    print("FINAL_STATUS=timeout")
    print("ERROR_CODE=AI_TIMEOUT")
    return 1


if __name__ == "__main__":
    sys.exit(run())
