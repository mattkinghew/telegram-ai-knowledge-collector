#!/usr/bin/env python3
"""Run one bounded, fictional Gemini Interactions API diagnostic."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Mapping, Optional

import httpx

# Keep the diagnostic runnable from the repository root without requiring a
# caller-specific PYTHONPATH.  This only adds the checked-in source tree.
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from backend.config import SUPPORTED_GEMINI_MODELS
from tools.p1_5_gemini_credential import credential_shape, load_gemini_key

GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/interactions"
TIMEOUT_SECONDS = 20.0
MAX_RESPONSE_BYTES = 64 * 1024


def _category_for_status(status: int) -> str:
    if status == 400:
        return "PARSE"
    if status == 401:
        return "AUTH"
    if status == 403:
        return "PERMISSION"
    if status == 404:
        return "MODEL"
    if status == 429:
        return "QUOTA"
    if 500 <= status <= 599:
        return "HTTP"
    return "HTTP"


def _error_code_for_status(status: int) -> str:
    return {
        400: "PROVIDER_BAD_REQUEST",
        401: "PROVIDER_AUTH",
        403: "PROVIDER_PERMISSION",
        404: "PROVIDER_MODEL",
        429: "PROVIDER_QUOTA",
    }.get(status, "PROVIDER_HTTP")


def _network_error_code(error: httpx.RequestError) -> str:
    """Return a stable, content-free code for transport diagnostics."""
    if isinstance(error, httpx.TimeoutException):
        return "PROVIDER_TIMEOUT"
    if isinstance(error, (httpx.InvalidURL, httpx.UnsupportedProtocol, httpx.LocalProtocolError)):
        return "MALFORMED_REQUEST"
    cause_names = set()
    cause = error.__cause__
    for _ in range(4):
        if cause is None:
            break
        cause_names.add(type(cause).__name__)
        cause = getattr(cause, "__cause__", None)
    if cause_names & {"gaierror", "NameResolutionError"}:
        return "PROVIDER_DNS"
    if cause_names & {"SSLError", "CertificateError"}:
        return "PROVIDER_TLS"
    if cause_names & {"ConnectionResetError", "BrokenPipeError"}:
        return "PROVIDER_RESET"
    if cause_names & {"ConnectionRefusedError", "ConnectionAbortedError"}:
        return "PROVIDER_CONNECT"
    return "PROVIDER_NETWORK"


def _output_text(envelope: object) -> Optional[str]:
    if not isinstance(envelope, dict) or not isinstance(envelope.get("steps"), list):
        return None
    for step in reversed(envelope["steps"]):
        if not isinstance(step, dict) or step.get("type") != "model_output":
            continue
        if "status" in step and step.get("status") not in {"done", "completed"}:
            return None
        content = step.get("content")
        if not isinstance(content, list):
            return None
        texts = [
            item.get("text")
            for item in content
            if isinstance(item, dict) and item.get("type") == "text"
        ]
        if len(texts) == 1 and isinstance(texts[0], str):
            return texts[0]
        return None
    return None


def run_direct_smoke(
    *,
    environ: Optional[Mapping[str, str]] = None,
    transport: Optional[httpx.BaseTransport] = None,
    endpoint: str = GEMINI_ENDPOINT,
) -> dict:
    values = os.environ if environ is None else environ
    api_key = values.get("GEMINI_API_KEY", "")
    model = values.get("GEMINI_MODEL", "")
    if not api_key:
        return {"ok": False, "blocked": True, "category": "CONFIG", "http_status": None}
    if api_key != api_key.strip() or any(character.isspace() for character in api_key):
        return {"ok": False, "category": "UNKNOWN", "http_status": None}
    if model not in SUPPORTED_GEMINI_MODELS:
        return {"ok": False, "category": "MODEL", "http_status": None}

    payload = {"model": model, "input": "Reply with exactly: GEMINI_OK"}
    try:
        with httpx.Client(transport=transport, trust_env=False, timeout=TIMEOUT_SECONDS) as client:
            with client.stream(
                "POST",
                endpoint,
                headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
                json=payload,
                follow_redirects=False,
            ) as response:
                body = bytearray()
                for chunk in response.iter_bytes():
                    if len(body) + len(chunk) > MAX_RESPONSE_BYTES:
                        return {
                            "ok": False,
                            "category": "PARSE",
                            "error_code": "RESPONSE_TOO_LARGE",
                            "http_status": response.status_code,
                        }
                    body.extend(chunk)
                status = response.status_code
                if status != 200:
                    return {
                        "ok": False,
                        "category": _category_for_status(status),
                        "error_code": _error_code_for_status(status),
                        "http_status": status,
                    }
    except (httpx.InvalidURL, httpx.UnsupportedProtocol, httpx.LocalProtocolError) as error:
        return {
            "ok": False,
            "category": "REQUEST",
            "error_code": _network_error_code(error),
            "http_status": None,
        }
    except httpx.RequestError as error:
        return {
            "ok": False,
            "category": "NETWORK",
            "error_code": _network_error_code(error),
            "http_status": None,
        }

    try:
        output = _output_text(json.loads(bytes(body).decode("utf-8")))
    except (UnicodeDecodeError, json.JSONDecodeError):
        output = None
    return {
        "ok": output == "GEMINI_OK",
        "category": None if output == "GEMINI_OK" else "PARSE",
        **({} if output == "GEMINI_OK" else {"error_code": "INVALID_RESPONSE"}),
        "http_status": 200,
        "output_match": output == "GEMINI_OK",
    }


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    diagnostic_environment = dict(os.environ)
    if not diagnostic_environment.get("GEMINI_API_KEY"):
        key, source = load_gemini_key()
        if key:
            diagnostic_environment["GEMINI_API_KEY"] = key
            diagnostic_environment["GEMINI_CREDENTIAL_SOURCE"] = source
    key = diagnostic_environment.get("GEMINI_API_KEY", "")
    shape = credential_shape(key)
    if shape in {"too_short", "whitespace"}:
        print("GEMINI_DIRECT_SMOKE=BLOCKED")
        print("CATEGORY=CONFIG")
        print(f"CREDENTIAL_EXISTS={'yes' if key else 'no'}")
        print(f"CREDENTIAL_LENGTH={len(key)}")
        print(f"CREDENTIAL_SHAPE={shape}")
        print(f"CREDENTIAL_SOURCE={diagnostic_environment.get('GEMINI_CREDENTIAL_SOURCE', 'environment' if key else 'unavailable')}")
        return 2
    result = run_direct_smoke(environ=diagnostic_environment)
    if result.get("blocked"):
        print("LIVE CALL BLOCKED: GEMINI_API_KEY not available in current runtime")
        return 2
    if result["ok"]:
        print("GEMINI_DIRECT_SMOKE=PASS")
        print(f"MODEL={os.environ.get('GEMINI_MODEL')}")
        print(f"HTTP_STATUS={result['http_status']}")
        print("OUTPUT_MATCH=PASS")
        return 0
    print("GEMINI_DIRECT_SMOKE=FAIL")
    print(f"CATEGORY={result['category']}")
    print(f"HTTP_STATUS={result['http_status'] or 'none'}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
