#!/usr/bin/env python3
"""NOT AI — DEVELOPMENT ONLY deterministic voice-capture simulator.

The simulator performs no network, credential, AI, or Vault access.
"""

from __future__ import annotations

import argparse
import json
from typing import Any, Mapping, Optional, Sequence, Union

try:
    from tools.voice_capture_reference import (
        VoiceCaptureContractError,
        render_voice_markdown,
        validate_structured_voice_output,
        validate_voice_input,
    )
except ModuleNotFoundError:  # Direct ``python3 tools/...`` execution.
    from voice_capture_reference import (  # type: ignore[no-redef]
        VoiceCaptureContractError,
        render_voice_markdown,
        validate_structured_voice_output,
        validate_voice_input,
    )


MODES = (
    "work",
    "knowledge",
    "mixed",
    "offline",
    "ai_unavailable",
    "invalid_json",
    "schema_mismatch",
)


def _structured_payload(mode: str) -> dict[str, Any]:
    if mode == "work":
        return {
            "suggested_title": "Fictional work update",
            "capture_type": "work",
            "one_sentence_summary": "A fictional work update is ready for review.",
            "completed": ["Reviewed the fictional draft"],
            "in_progress": ["Testing the fictional workflow"],
            "next_actions": ["Review the fictional evidence"],
            "blockers": [],
            "decisions": [],
            "knowledge": [],
            "content_ideas": [],
            "project_updates": ["Fictional workflow remains in progress"],
            "facts_to_verify": [],
            "related_projects": [],
            "confidence": "medium",
        }
    if mode == "knowledge":
        return {
            "suggested_title": "Fictional learning note",
            "capture_type": "knowledge",
            "one_sentence_summary": "A fictional observation may support future learning.",
            "completed": [],
            "in_progress": [],
            "next_actions": [],
            "blockers": [],
            "decisions": [],
            "knowledge": ["Small examples can make a workflow easier to review"],
            "content_ideas": ["This observation could become a short article"],
            "project_updates": [],
            "facts_to_verify": [],
            "related_projects": [],
            "confidence": "medium",
        }
    return {
        "suggested_title": "Fictional mixed capture",
        "capture_type": "mixed",
        "one_sentence_summary": "A fictional work update and learning point need review.",
        "completed": ["Reviewed a fictional note"],
        "in_progress": [],
        "next_actions": ["Check the fictional acceptance criteria"],
        "blockers": [],
        "decisions": [],
        "knowledge": ["A smaller review step can expose missing information"],
        "content_ideas": [],
        "project_updates": [],
        "facts_to_verify": ["Confirm the fictional result before reuse"],
        "related_projects": [],
        "confidence": "medium",
    }


def simulate_voice_capture(
    capture: Mapping[str, Any],
    *,
    mode: str = "mixed",
) -> Union[dict[str, Any], str]:
    """Return deterministic development data for one supported mode."""

    request = validate_voice_input(capture)
    if mode not in MODES:
        raise VoiceCaptureContractError("unsupported simulator mode")
    if mode == "offline":
        return render_voice_markdown(request)
    if mode == "ai_unavailable":
        return {
            "ok": False,
            "error_code": "AI_UNAVAILABLE",
            "message": "Structured processing is unavailable; the transcript remains saved.",
            "fallback_markdown": render_voice_markdown(request),
        }
    if mode == "invalid_json":
        return {
            "ok": False,
            "error_code": "INVALID_AI_JSON",
            "message": "The provider returned invalid JSON; the transcript remains saved.",
            "provider_payload": '{"suggested_title": "deliberately incomplete"',
            "fallback_markdown": render_voice_markdown(request),
        }
    if mode == "schema_mismatch":
        return {
            "ok": False,
            "error_code": "SCHEMA_MISMATCH",
            "message": "The provider response failed validation; the transcript remains saved.",
            "provider_payload": {"suggested_title": "Missing required fields"},
            "fallback_markdown": render_voice_markdown(request),
        }
    result = _structured_payload(mode)
    return validate_structured_voice_output(
        result,
        allowed_projects=request["allowed_projects"],
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=MODES, default="mixed")
    args = parser.parse_args(argv)
    capture = {
        "schema_version": "1",
        "captured_at": "2026-08-20T09:30:00+08:00",
        "source_type": "voice_transcript",
        "raw_transcript": "Fictional transcript for offline development only.",
        "allowed_projects": ["Project Alpha", "Project Beta"],
    }
    result = simulate_voice_capture(capture, mode=args.mode)
    if isinstance(result, str):
        print(result)
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
