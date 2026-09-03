#!/usr/bin/env python3
"""Run one fictional, redacted Gemini request-contract bisection."""

from __future__ import annotations

import argparse
import json
import os
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


TIMEOUT = httpx.Timeout(connect=5.0, read=60.0, write=10.0, pool=5.0)


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
    api_key = values.get("GEMINI_API_KEY", "")
    model = values.get("GEMINI_MODEL", "")
    if not api_key or model not in SUPPORTED_GEMINI_MODELS:
        print("LIVE BISECTION BLOCKED: explicit GEMINI_API_KEY and allowlisted GEMINI_MODEL are required")
        return 2
    provider = GeminiProvider(api_key=api_key, model=model)
    try:
        for name, payload in _variants(provider):
            with provider._client.stream(
                "POST",
                GEMINI_ENDPOINT,
                headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
                json=payload,
                timeout=TIMEOUT,
                follow_redirects=False,
            ) as response:
                size = sum(len(chunk) for chunk in response.iter_bytes())
                print(f"{name} status={response.status_code} request_bytes={len(json.dumps(payload, ensure_ascii=False).encode())} response_bytes={size}")
    finally:
        provider._client.close()
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    argparse.ArgumentParser(description=__doc__).parse_args(argv)
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
