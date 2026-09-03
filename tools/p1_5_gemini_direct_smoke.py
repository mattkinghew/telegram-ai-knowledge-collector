#!/usr/bin/env python3
"""Run one bounded, fictional Gemini Interactions API diagnostic."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Mapping, Optional

import httpx

from backend.config import SUPPORTED_GEMINI_MODELS

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
                GEMINI_ENDPOINT,
                headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
                json=payload,
                follow_redirects=False,
            ) as response:
                body = bytearray()
                for chunk in response.iter_bytes():
                    if len(body) + len(chunk) > MAX_RESPONSE_BYTES:
                        return {"ok": False, "category": "PARSE", "http_status": response.status_code}
                    body.extend(chunk)
                status = response.status_code
                if status != 200:
                    return {"ok": False, "category": _category_for_status(status), "http_status": status}
    except httpx.TimeoutException:
        return {"ok": False, "category": "NETWORK", "http_status": None}
    except httpx.RequestError:
        return {"ok": False, "category": "NETWORK", "http_status": None}

    try:
        output = _output_text(json.loads(bytes(body).decode("utf-8")))
    except (UnicodeDecodeError, json.JSONDecodeError):
        output = None
    return {
        "ok": output == "GEMINI_OK",
        "category": None if output == "GEMINI_OK" else "PARSE",
        "http_status": 200,
        "output_match": output == "GEMINI_OK",
    }


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    result = run_direct_smoke()
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
