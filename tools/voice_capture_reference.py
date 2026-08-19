#!/usr/bin/env python3
"""Validate and render the offline Universal Voice Capture contract.

This module performs no AI, network, credential, or Vault access. Both the
dictated transcript and any model-produced structure are untrusted input.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping, Optional, Sequence


SCHEMA_VERSION = "1"
SOURCE_TYPE = "voice_transcript"
MAX_TRANSCRIPT_CHARS = 50_000
MAX_PROJECTS = 20
CAPTURE_TYPES = frozenset({"work", "knowledge", "idea", "learning", "mixed"})
CONFIDENCE_VALUES = frozenset({"low", "medium", "high"})
INPUT_FIELDS = frozenset(
    {
        "schema_version",
        "captured_at",
        "source_type",
        "raw_transcript",
        "allowed_projects",
    }
)
OUTPUT_LIST_FIELDS = (
    "completed",
    "in_progress",
    "next_actions",
    "blockers",
    "decisions",
    "knowledge",
    "content_ideas",
    "project_updates",
    "facts_to_verify",
    "related_projects",
)
OUTPUT_FIELDS = frozenset(
    {
        "suggested_title",
        "capture_type",
        "one_sentence_summary",
        "confidence",
        *OUTPUT_LIST_FIELDS,
    }
)


class VoiceCaptureContractError(ValueError):
    """Raised when voice input or structured output violates the contract."""


def _require_exact_fields(payload: Mapping[str, Any], fields: frozenset[str]) -> None:
    unknown = set(payload) - fields
    missing = fields - set(payload)
    if unknown:
        raise VoiceCaptureContractError("unexpected fields")
    if missing:
        raise VoiceCaptureContractError("missing fields")


def _single_line_string(value: Any, name: str, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise VoiceCaptureContractError(f"{name} must be a non-empty string")
    if len(value) > maximum or "\n" in value or "\r" in value:
        raise VoiceCaptureContractError(f"invalid {name}")
    return value


def _is_timezone_aware_iso8601(value: str) -> bool:
    candidate = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def _validate_allowed_projects(value: Any) -> list[str]:
    if not isinstance(value, list) or len(value) > MAX_PROJECTS:
        raise VoiceCaptureContractError(
            f"allowed_projects must be an array of at most {MAX_PROJECTS} items"
        )
    projects = [
        _single_line_string(item, "allowed project", 200)
        for item in value
    ]
    if len(projects) != len(set(projects)):
        raise VoiceCaptureContractError("allowed_projects must be unique")
    return projects


def validate_voice_input(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the strict voice request and preserve its transcript exactly."""

    if not isinstance(payload, Mapping):
        raise VoiceCaptureContractError("request must be an object")
    _require_exact_fields(payload, INPUT_FIELDS)
    if payload["schema_version"] != SCHEMA_VERSION:
        raise VoiceCaptureContractError("unsupported schema_version")
    if payload["source_type"] != SOURCE_TYPE:
        raise VoiceCaptureContractError("source_type must be voice_transcript")
    captured_at = _single_line_string(payload["captured_at"], "captured_at", 64)
    if not _is_timezone_aware_iso8601(captured_at):
        raise VoiceCaptureContractError("captured_at must be timezone-aware ISO-8601")
    transcript = payload["raw_transcript"]
    if not isinstance(transcript, str) or not transcript.strip():
        raise VoiceCaptureContractError("raw_transcript must be non-empty")
    if len(transcript) > MAX_TRANSCRIPT_CHARS:
        raise VoiceCaptureContractError(
            f"raw_transcript exceeds {MAX_TRANSCRIPT_CHARS} characters"
        )
    projects = _validate_allowed_projects(payload["allowed_projects"])
    return {
        "schema_version": SCHEMA_VERSION,
        "captured_at": captured_at,
        "source_type": SOURCE_TYPE,
        "raw_transcript": transcript,
        "allowed_projects": projects,
    }


def _validate_output_list(value: Any, name: str) -> list[str]:
    if not isinstance(value, list) or len(value) > 20:
        raise VoiceCaptureContractError(f"{name} must be an array of at most 20 items")
    items = []
    for item in value:
        if (
            not isinstance(item, str)
            or not item.strip()
            or len(item) > 1_000
            or "\n" in item
            or "\r" in item
        ):
            raise VoiceCaptureContractError(f"invalid {name} item")
        items.append(item)
    return items


def validate_structured_voice_output(
    payload: Mapping[str, Any],
    *,
    allowed_projects: Sequence[str],
) -> dict[str, Any]:
    """Validate untrusted structured output and enforce the project allowlist."""

    if not isinstance(payload, Mapping):
        raise VoiceCaptureContractError("structured output must be an object")
    _require_exact_fields(payload, OUTPUT_FIELDS)
    suggested_title = _single_line_string(
        payload["suggested_title"], "suggested_title", 200
    )
    summary = payload["one_sentence_summary"]
    if not isinstance(summary, str) or len(summary) > 500 or "\n" in summary or "\r" in summary:
        raise VoiceCaptureContractError("invalid one_sentence_summary")
    if payload["capture_type"] not in CAPTURE_TYPES:
        raise VoiceCaptureContractError("invalid capture_type")
    if payload["confidence"] not in CONFIDENCE_VALUES:
        raise VoiceCaptureContractError("invalid confidence")
    lists = {
        name: _validate_output_list(payload[name], name)
        for name in OUTPUT_LIST_FIELDS
    }
    allowed = set(_validate_allowed_projects(list(allowed_projects)))
    if any(project not in allowed for project in lists["related_projects"]):
        raise VoiceCaptureContractError("related_projects contains an unsupported project")
    if len(set(lists["related_projects"])) != len(lists["related_projects"]):
        raise VoiceCaptureContractError("related_projects must be unique")
    return {
        "suggested_title": suggested_title,
        "capture_type": payload["capture_type"],
        "one_sentence_summary": summary,
        **lists,
        "confidence": payload["confidence"],
    }


def _render_bullets(heading: str, values: Sequence[str], *, tasks: bool = False) -> str:
    if not values:
        return ""
    prefix = "- [ ] " if tasks else "- "
    return "\n".join([f"## {heading}", *[prefix + value for value in values]])


def render_voice_markdown(
    capture: Mapping[str, Any],
    structured_output: Optional[Mapping[str, Any]] = None,
) -> str:
    """Render a reviewable note; the original transcript is always retained."""

    request = validate_voice_input(capture)
    if structured_output is None:
        return (
            "---\n"
            "type: voice_capture\n"
            f"created: {request['captured_at']}\n"
            "source_type: voice_transcript\n"
            "ai_status: pending\n"
            "review_status: unreviewed\n"
            "---\n"
            "# Voice Capture\n\n"
            "## 原始語音轉錄\n"
            f"{request['raw_transcript']}\n"
        )

    output = validate_structured_voice_output(
        structured_output,
        allowed_projects=request["allowed_projects"],
    )
    sections = []
    if output["one_sentence_summary"]:
        sections.append(
            "## 一句摘要\n" + output["one_sentence_summary"]
        )
    for heading, name, tasks in (
        ("完成", "completed", False),
        ("進行中", "in_progress", False),
        ("下一步", "next_actions", True),
        ("Blockers / 待確認", "blockers", False),
        ("決策", "decisions", False),
        ("新知識 / 素材", "knowledge", False),
        ("可以轉化成內容", "content_ideas", False),
        ("專案進度", "project_updates", False),
        ("待核實", "facts_to_verify", False),
        ("相關專案", "related_projects", False),
    ):
        rendered = _render_bullets(heading, output[name], tasks=tasks)
        if rendered:
            sections.append(rendered)
    sections.append("## 原始語音轉錄\n" + request["raw_transcript"])
    body = "\n\n".join(sections)
    return (
        "---\n"
        "type: voice_capture\n"
        f"created: {request['captured_at']}\n"
        "source_type: voice_transcript\n"
        "ai_status: suggested\n"
        "review_status: unreviewed\n"
        "---\n"
        f"# {output['suggested_title']}\n\n"
        f"{body}\n"
    )
