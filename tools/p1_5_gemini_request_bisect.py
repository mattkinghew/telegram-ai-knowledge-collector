#!/usr/bin/env python3
"""Run one fictional, redacted Gemini request-contract bisection."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Mapping, Optional

import httpx

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from backend.config import SUPPORTED_GEMINI_MODELS
from backend.models import CaptureRequest
from backend.providers.gemini import GEMINI_ENDPOINT, GeminiProvider
from tools.p1_5_gemini_credential import credential_shape, load_gemini_key


TIMEOUT = httpx.Timeout(connect=5.0, read=60.0, write=10.0, pool=5.0)
MAX_SANITIZED_MESSAGE = 240


def _credential_metadata(api_key: str) -> dict[str, object]:
    """Return key metadata only; never return any key characters."""
    return {
        "exists": bool(api_key),
        "length": len(api_key),
        "whitespace": bool(api_key and (api_key != api_key.strip() or any(c.isspace() for c in api_key))),
        "prefix_shape": bool(re.fullmatch(r"AIza[0-9A-Za-z_-]+", api_key)),
        "source": "environment" if api_key else "unavailable",
    }


def _safe_text(value: object) -> str:
    text = " ".join(str(value).split())
    text = re.sub(r"(?i)(AIza[0-9A-Za-z_-]{8,})", "[REDACTED]", text)
    text = re.sub(
        r"(?i)(?:x-goog-)?api[-_ ]?key\s*[:=]\s*[^,; ]+",
        "[REDACTED]",
        text,
    )
    text = re.sub(r"(?i)(?:authorization|bearer)\s*[:=]\s*[^,; ]+", "[REDACTED]", text)
    return text[:MAX_SANITIZED_MESSAGE]


def _sanitized_http_error(body: bytes) -> dict[str, str]:
    """Extract only bounded provider status/message/reason metadata."""
    try:
        envelope = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {"status": "UNKNOWN", "message": "non_json_error", "reason": ""}
    error = envelope.get("error") if isinstance(envelope, dict) else None
    if not isinstance(error, dict):
        return {"status": "UNKNOWN", "message": "unrecognized_error", "reason": ""}
    status = error.get("status")
    safe_status = re.sub(r"[^A-Za-z0-9_].*", "", str(status or "UNKNOWN")).upper()[:64]
    reason = ""
    details = error.get("details")
    if isinstance(details, list):
        for detail in details:
            if isinstance(detail, dict) and isinstance(detail.get("reason"), str):
                reason = _safe_text(detail["reason"])
                break
    return {
        "status": safe_status or "UNKNOWN",
        "message": _safe_text(error.get("message", "provider_error")),
        "reason": reason,
    }


def _fictional_request() -> CaptureRequest:
    return CaptureRequest(
        schema_version="1",
        capture_type="voice",
        source_type="voice_transcript",
        raw_content="Fictional Project Alpha capture for contract testing.",
        requested_processing="voice_structure",
        allowed_projects=["Project Alpha"],
    )


def _variants(provider: GeminiProvider) -> list[tuple[str, dict[str, Any]]]:
    full = provider._payload(_fictional_request())
    schema = full["response_format"][0]["schema"]
    simple_schema = {
        "type": "object",
        "properties": {"processing_mode": {"type": "string"}},
        "required": ["processing_mode"],
    }
    return [
        ("A_direct_minimal", {"model": provider._model, "input": "Fictional smoke input."}),
        (
            "B_plus_system_instruction",
            {
                "model": provider._model,
                "input": "Fictional smoke input.",
                "system_instruction": full["system_instruction"],
            },
        ),
        (
            "C_plus_structured_output",
            {
                "model": provider._model,
                "input": "Fictional smoke input.",
                "response_format": [{"type": "text", "mime_type": "application/json", "schema": simple_schema}],
            },
        ),
        (
            "D_plus_full_schema",
            {
                "model": provider._model,
                "input": "Fictional smoke input.",
                "response_format": [{"type": "text", "mime_type": "application/json", "schema": schema}],
            },
        ),
        ("E_application_prompt_envelope", full),
    ]


def run(environ: Optional[Mapping[str, str]] = None) -> int:
    values = os.environ if environ is None else environ
    api_key, credential_source = load_gemini_key() if environ is None else load_gemini_key(values)
    model = values.get("GEMINI_MODEL", "")
    shape = credential_shape(api_key)
    if shape not in {"valid_shape", "missing"}:
        print("LIVE BISECTION BLOCKED: Gemini credential is invalid or a placeholder")
        print(f"CREDENTIAL_EXISTS={'yes' if api_key else 'no'}")
        print(f"CREDENTIAL_LENGTH={len(api_key)}")
        print(f"CREDENTIAL_WHITESPACE={'yes' if shape == 'whitespace' else 'no'}")
        print(f"CREDENTIAL_PREFIX_SHAPE={'match' if shape == 'valid_shape' else 'no-match'}")
        print(f"CREDENTIAL_SOURCE={credential_source}")
        return 2
    if not api_key or model not in SUPPORTED_GEMINI_MODELS:
        print("LIVE BISECTION BLOCKED: explicit GEMINI_API_KEY and allowlisted GEMINI_MODEL are required")
        metadata = _credential_metadata(api_key)
        print(f"CREDENTIAL_EXISTS={'yes' if metadata['exists'] else 'no'}")
        print(f"CREDENTIAL_LENGTH={metadata['length']}")
        print(f"CREDENTIAL_WHITESPACE={'yes' if metadata['whitespace'] else 'no'}")
        print(f"CREDENTIAL_PREFIX_SHAPE={'match' if metadata['prefix_shape'] else 'no-match'}")
        print(f"CREDENTIAL_SOURCE={credential_source}")
        return 2
    metadata = _credential_metadata(api_key)
    print(f"CREDENTIAL_EXISTS={'yes' if metadata['exists'] else 'no'}")
    print(f"CREDENTIAL_LENGTH={metadata['length']}")
    print(f"CREDENTIAL_WHITESPACE={'yes' if metadata['whitespace'] else 'no'}")
    print(f"CREDENTIAL_PREFIX_SHAPE={'match' if metadata['prefix_shape'] else 'no-match'}")
    print(f"CREDENTIAL_SOURCE={credential_source}")
    provider = GeminiProvider(api_key=api_key, model=model)
    try:
        for name, payload in _variants(provider):
            try:
                response_context = provider._client.stream(
                    "POST",
                    GEMINI_ENDPOINT,
                    headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
                    json=payload,
                    timeout=TIMEOUT,
                    follow_redirects=False,
                )
                response = response_context.__enter__()
            except httpx.TimeoutException:
                print(f"{name} status=none request_bytes={len(json.dumps(payload, ensure_ascii=False).encode())} response_bytes=0 error_category=timeout")
                return 1
            except httpx.RequestError as error:
                category = "dns" if type(getattr(error, "__cause__", None)).__name__ in {"gaierror", "NameResolutionError"} else "connect"
                print(f"{name} status=none request_bytes={len(json.dumps(payload, ensure_ascii=False).encode())} response_bytes=0 error_category={category}")
                return 1
            try:
                body = bytearray()
                size = 0
                for chunk in response.iter_bytes():
                    size += len(chunk)
                    if len(body) < 8192:
                        body.extend(chunk[: 8192 - len(body)])
                request_bytes = len(json.dumps(payload, ensure_ascii=False).encode())
                line = f"{name} status={response.status_code} request_bytes={request_bytes} response_bytes={size}"
                if response.status_code >= 400:
                    error = _sanitized_http_error(bytes(body))
                    line += (
                        f" gemini_status={error['status']}"
                        f" message={json.dumps(error['message'], ensure_ascii=False)}"
                    )
                    if error["reason"]:
                        line += f" reason={json.dumps(error['reason'], ensure_ascii=False)}"
                print(line)
            finally:
                response_context.__exit__(None, None, None)
    finally:
        provider._client.close()
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    argparse.ArgumentParser(description=__doc__).parse_args(argv)
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
