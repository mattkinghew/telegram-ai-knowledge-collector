#!/bin/zsh

# Manual operator-run fictional online smoke test. Never prints the bearer token
# or response bodies containing capture content.
set -euo pipefail

ACCOUNT="ob-editor"
BASE_URL="https://capture.lamlab.cc"
cleanup() { unset OB_EDITOR_TOKEN; }
trap cleanup EXIT

OB_EDITOR_TOKEN="$(/usr/bin/security find-generic-password -a "$ACCOUNT" -s API_AUTH_TOKEN -w 2>/dev/null)" || {
  print -u2 "KEYCHAIN: FAIL (API_AUTH_TOKEN unavailable)"; exit 78
}
[[ -n "$OB_EDITOR_TOKEN" ]] || { print -u2 "KEYCHAIN: FAIL (API_AUTH_TOKEN empty)"; exit 78; }
print "KEYCHAIN: PASS"

BASE_URL="$BASE_URL" OB_EDITOR_TOKEN="$OB_EDITOR_TOKEN" /usr/bin/python3 - <<'PY'
import json
import os
import subprocess
import sys
import time
from uuid import uuid4

base = os.environ["BASE_URL"].rstrip("/")
token = os.environ["OB_EDITOR_TOKEN"]
headers = {"Accept": "application/json"}
auth_headers = {**headers, "Authorization": "Bearer " + token, "Content-Type": "application/json"}

def config_value(value):
    return str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\r", "\\r").replace("\n", "\\n")

def request(path, *, method="GET", body=None, authenticated=False):
    request_headers = auth_headers if authenticated else headers
    config = [
        "silent",
        "show-error",
        "max-time = 15",
        f'request = "{config_value(method)}"',
        f'url = "{config_value(base + path)}"',
    ]
    config.extend(f'header = "{config_value(name + ": " + value)}"' for name, value in request_headers.items())
    if body is not None:
        config.append(f'data = "{config_value(json.dumps(body, separators=(",", ":")))}"')
    config.append('write-out = "__OB_EDITOR_HTTP_STATUS__%{http_code}"')
    try:
        completed = subprocess.run(
            ["/usr/bin/curl", "--config", "-"],
            input=("\n".join(config) + "\n").encode("utf-8"),
            capture_output=True,
            timeout=20,
            check=False,
        )
        output = completed.stdout.decode("utf-8")
        body_text, marker, status_text = output.rpartition("__OB_EDITOR_HTTP_STATUS__")
        if not marker:
            return 0, {}
        try:
            status = int(status_text)
            payload = json.loads(body_text)
        except (ValueError, json.JSONDecodeError):
            return 0, {}
        return status, payload
    except Exception:
        return 0, {}

status, payload = request("/health")
if (
    status != 200
    or not isinstance(payload, dict)
    or payload.get("ok") is not True
    or payload.get("status") != "healthy"
):
    sys.exit("HEALTH: FAIL")
print("HEALTH: PASS")

status, _ = request("/api/v1/captures")
if status != 401: sys.exit("AUTH_GUARD: FAIL")
print("AUTH_GUARD: PASS")

raw = "ob-editor-v01-fictional-smoke-" + str(uuid4())
body = {
    "schema_version": "1", "capture_type": "content", "source_type": "selected_text",
    "raw_content": raw, "requested_processing": "summary",
}
status, created = request("/api/v1/capture", method="POST", body=body, authenticated=True)
if status not in (200, 202) or not isinstance(created, dict): sys.exit("POST_CAPTURE: FAIL")
capture_id = created.get("id")
if not capture_id or created.get("capture_id") != capture_id: sys.exit("ID_COMPATIBILITY: FAIL")
if created.get("status") not in {"pending", "processing", "processed", "failed"}: sys.exit("STATUS: FAIL")
print("POST_CAPTURE: PASS")
print("ID_COMPATIBILITY: PASS")

for _ in range(20):
    status, current = request("/api/v1/captures/" + capture_id, authenticated=True)
    if status != 200: sys.exit("GET_CAPTURE: FAIL")
    if current.get("id") != capture_id or current.get("capture_id") != capture_id: sys.exit("ID_COMPATIBILITY: FAIL")
    if current.get("raw_content") != raw: sys.exit("RAW_RECOVERY: FAIL")
    if current.get("status") in {"processed", "failed"}: break
    if current.get("status") not in {"pending", "processing"}: sys.exit("STATUS: FAIL")
    time.sleep(2)
else:
    sys.exit("PROCESSING_TIMEOUT: FAIL")

print("GET_CAPTURE: PASS")
print("RAW_RECOVERY: PASS")
if current["status"] == "processed":
    if "result" not in current: sys.exit("RESULT: FAIL")
    print("RESULT: PASS")
else:
    error = current.get("error", {})
    if not error.get("code") or not error.get("message"): sys.exit("FAILED_ERROR: FAIL")
    print("FAILED_ERROR: PASS")

status, _ = request("/api/v1/captures/00000000-0000-4000-8000-000000000000", authenticated=True)
if status != 404: sys.exit("UNKNOWN_CAPTURE: FAIL")
print("UNKNOWN_CAPTURE: PASS")
PY
