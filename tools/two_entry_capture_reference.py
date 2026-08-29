#!/usr/bin/env python3
"""Offline P1.4 reference contract for the two primary mobile entries.

This module performs no AI, network, credential, file-content, or Vault access.
All content and structured suggestions are untrusted input.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Mapping, Optional, Sequence
from urllib.parse import urlparse

try:
    from tools.voice_capture_reference import (
        render_voice_markdown,
        validate_structured_voice_output,
        validate_voice_input,
    )
except ModuleNotFoundError:  # Direct ``python3 tools/...`` execution.
    from voice_capture_reference import (  # type: ignore[no-redef]
        render_voice_markdown,
        validate_structured_voice_output,
        validate_voice_input,
    )


SCHEMA_VERSION = "1"
MAX_RAW_CONTENT_CHARS = 50_000
INPUT_KINDS = frozenset(
    {"url", "shared_text", "selected_text", "clipboard", "image", "file"}
)
PROCESSING_MODES = frozenset(
    {"raw_save", "summary", "recommendation", "short_article", "project_knowledge"}
)
CONTENT_FIELDS = frozenset(
    {
        "schema_version",
        "created",
        "input_kind",
        "source",
        "raw_content",
        "requested_processing",
    }
)
SUGGESTION_LIST_FIELDS = (
    "core_points",
    "immediate_uses",
    "convertible_material",
    "facts_to_verify",
)
SUGGESTION_FIELDS = frozenset(
    {
        "processing_mode",
        "suggested_title",
        "thirty_second_summary",
        "core_points",
        "why_worth_saving",
        "immediate_uses",
        "convertible_material",
        "facts_to_verify",
        "recommendation",
        "short_article_draft",
    }
)

VIDEO_HOSTS = frozenset(
    {"youtube.com", "youtu.be", "vimeo.com", "tiktok.com", "twitch.tv"}
)
SOCIAL_HOSTS = frozenset(
    {
        "x.com",
        "twitter.com",
        "threads.net",
        "instagram.com",
        "facebook.com",
        "linkedin.com",
        "reddit.com",
    }
)


class TwoEntryCaptureError(ValueError):
    """Raised when a P1.4 capture or suggestion violates the contract."""


def _require_exact_fields(payload: Mapping[str, Any], fields: frozenset[str]) -> None:
    if set(payload) - fields:
        raise TwoEntryCaptureError("unexpected fields")
    if fields - set(payload):
        raise TwoEntryCaptureError("missing fields")


def _string(
    value: Any,
    name: str,
    maximum: int,
    *,
    required: bool = False,
    single_line: bool = False,
) -> str:
    if not isinstance(value, str):
        raise TwoEntryCaptureError(f"{name} must be a string")
    normalized = value.replace("\r\n", "\n").replace("\r", "\n")
    if len(normalized) > maximum:
        raise TwoEntryCaptureError(f"{name} exceeds {maximum} characters")
    if required and not normalized.strip():
        raise TwoEntryCaptureError(f"{name} is required")
    if single_line and "\n" in normalized:
        raise TwoEntryCaptureError(f"{name} must be one line")
    return normalized


def _is_timezone_aware_iso8601(value: str) -> bool:
    candidate = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def _host_matches(hostname: str, candidates: Sequence[str]) -> bool:
    return any(
        hostname == candidate or hostname.endswith("." + candidate)
        for candidate in candidates
    )


def _validate_public_reference_url(source: str) -> str:
    parsed = urlparse(source)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.hostname is None
        or parsed.username is not None
        or parsed.password is not None
        or any(character.isspace() for character in source)
    ):
        raise TwoEntryCaptureError("source must be an HTTP or HTTPS URL")
    return parsed.hostname.lower().rstrip(".")


def classify_content_source(input_kind: str, source: str) -> str:
    """Classify one Shortcut input without a user-facing category question."""

    if not isinstance(input_kind, str) or not isinstance(source, str):
        raise TwoEntryCaptureError("input_kind and source must be strings")
    if input_kind not in INPUT_KINDS:
        raise TwoEntryCaptureError("unsupported input_kind")
    if input_kind == "url":
        hostname = _validate_public_reference_url(source)
        if _host_matches(hostname, VIDEO_HOSTS):
            return "video_url"
        if _host_matches(hostname, SOCIAL_HOSTS):
            return "social_post"
        return "article_url"
    if input_kind in {"shared_text", "selected_text"}:
        return "selected_text"
    if input_kind == "clipboard":
        return "clipboard_text"
    if input_kind == "image":
        return "image_reference"
    return "file_reference"


def validate_content_capture(payload: Mapping[str, Any]) -> dict[str, str]:
    """Validate one exact content capture and preserve its evidence exactly."""

    if not isinstance(payload, Mapping):
        raise TwoEntryCaptureError("capture must be an object")
    _require_exact_fields(payload, CONTENT_FIELDS)
    if payload["schema_version"] != SCHEMA_VERSION:
        raise TwoEntryCaptureError("unsupported schema_version")
    created = _string(payload["created"], "created", 64, required=True, single_line=True)
    if not _is_timezone_aware_iso8601(created):
        raise TwoEntryCaptureError("created must be timezone-aware ISO-8601")
    input_kind = _string(
        payload["input_kind"], "input_kind", 40, required=True, single_line=True
    )
    if input_kind not in INPUT_KINDS:
        raise TwoEntryCaptureError("unsupported input_kind")
    source = _string(payload["source"], "source", 2_048, single_line=True)
    raw_content = _string(
        payload["raw_content"], "raw_content", MAX_RAW_CONTENT_CHARS
    )
    requested_processing = _string(
        payload["requested_processing"],
        "requested_processing",
        40,
        required=True,
        single_line=True,
    )
    if requested_processing not in PROCESSING_MODES:
        raise TwoEntryCaptureError("unsupported requested_processing")

    if input_kind == "url":
        _validate_public_reference_url(source)
    elif input_kind in {"shared_text", "selected_text", "clipboard"}:
        if source:
            raise TwoEntryCaptureError("source must be blank for text input")
        if not raw_content.strip():
            raise TwoEntryCaptureError("raw_content is required for text input")
    else:
        if (
            not source
            or len(source) > 255
            or source in {".", ".."}
            or "/" in source
            or "\\" in source
        ):
            raise TwoEntryCaptureError("reference source must be a safe filename")

    source_type = classify_content_source(input_kind, source)
    return {
        "schema_version": SCHEMA_VERSION,
        "created": created,
        "input_kind": input_kind,
        "source_type": source_type,
        "source": source,
        "raw_content": raw_content,
        "requested_processing": requested_processing,
    }


def _validate_list(value: Any, name: str, maximum: int) -> list[str]:
    if not isinstance(value, list) or len(value) > maximum:
        raise TwoEntryCaptureError(f"{name} must contain at most {maximum} items")
    items = []
    for item in value:
        normalized = _string(item, name + " item", 500, required=True, single_line=True)
        items.append(normalized)
    return items


def _validate_optional_line(value: Any, name: str, maximum: int) -> Optional[str]:
    if value is None:
        return None
    return _string(value, name, maximum, required=True, single_line=True)


def _validate_short_article(value: Any, processing_mode: str) -> Optional[str]:
    if processing_mode != "short_article":
        if value is not None:
            raise TwoEntryCaptureError(
                "short_article_draft is only allowed for short_article"
            )
        return None
    article = _string(value, "short_article_draft", 3_000, required=True)
    if not article.startswith("AI draft\n"):
        raise TwoEntryCaptureError("short_article_draft must start with AI draft")
    body = article[len("AI draft\n") :]
    if re.search(r"[\u3400-\u9fff]", body):
        if not 150 <= len(body) <= 300:
            raise TwoEntryCaptureError("Chinese short article must be 150-300 characters")
    elif not 80 <= len(body.split()) <= 180:
        raise TwoEntryCaptureError("English short article must be 80-180 words")
    return article


def validate_content_suggestion(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a bounded, unconfirmed suggestion for one content capture."""

    if not isinstance(payload, Mapping):
        raise TwoEntryCaptureError("suggestion must be an object")
    _require_exact_fields(payload, SUGGESTION_FIELDS)
    processing_mode = _string(
        payload["processing_mode"],
        "processing_mode",
        40,
        required=True,
        single_line=True,
    )
    if processing_mode not in PROCESSING_MODES - {"raw_save"}:
        raise TwoEntryCaptureError("invalid suggestion processing_mode")
    suggestion = {
        "processing_mode": processing_mode,
        "suggested_title": _string(
            payload["suggested_title"],
            "suggested_title",
            200,
            required=True,
            single_line=True,
        ),
        "thirty_second_summary": _string(
            payload["thirty_second_summary"],
            "thirty_second_summary",
            500,
            required=True,
            single_line=True,
        ),
        "core_points": _validate_list(payload["core_points"], "core_points", 3),
        "why_worth_saving": _string(
            payload["why_worth_saving"],
            "why_worth_saving",
            500,
            required=True,
            single_line=True,
        ),
        "immediate_uses": _validate_list(
            payload["immediate_uses"], "immediate_uses", 3
        ),
        "convertible_material": _validate_list(
            payload["convertible_material"], "convertible_material", 3
        ),
        "facts_to_verify": _validate_list(
            payload["facts_to_verify"], "facts_to_verify", 5
        ),
        "recommendation": _validate_optional_line(
            payload["recommendation"], "recommendation", 1_000
        ),
        "short_article_draft": _validate_short_article(
            payload["short_article_draft"], processing_mode
        ),
    }
    if processing_mode == "recommendation" and suggestion["recommendation"] is None:
        raise TwoEntryCaptureError("recommendation mode requires recommendation")
    if processing_mode != "recommendation" and suggestion["recommendation"] is not None:
        raise TwoEntryCaptureError("recommendation is only allowed in recommendation mode")
    return suggestion


def _yaml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _render_bullets(heading: str, items: Sequence[str]) -> str:
    if not items:
        return ""
    return "\n".join([f"## {heading}", *["- " + item for item in items]])


def _render_content_markdown(
    capture: Mapping[str, str],
    *,
    ai_status: str,
    suggestion: Optional[Mapping[str, Any]],
) -> str:
    title = suggestion["suggested_title"] if suggestion else "Content Capture"
    sections = []
    if suggestion:
        sections.extend(
            [
                "> 以下內容是未確認建議；原始內容與來源保留在下方。",
                "## 30 秒摘要\n" + suggestion["thirty_second_summary"],
                _render_bullets("3 個重點", suggestion["core_points"]),
                "## 為甚麼值得留\n" + suggestion["why_worth_saving"],
                _render_bullets("可立即使用", suggestion["immediate_uses"]),
                _render_bullets("可轉化素材", suggestion["convertible_material"]),
                _render_bullets("待核實", suggestion["facts_to_verify"]),
            ]
        )
        if suggestion["recommendation"] is not None:
            sections.append("## 深入建議\n" + suggestion["recommendation"])
        if suggestion["short_article_draft"] is not None:
            sections.append("## AI 草稿\n" + suggestion["short_article_draft"])
    if capture["raw_content"]:
        sections.append("## 原始內容\n" + capture["raw_content"])
    sections.append("## Source\n" + (capture["source"] or "Not provided"))
    body = "\n\n".join(section for section in sections if section)
    return (
        "---\n"
        "type: content_capture\n"
        f"created: {_yaml_string(capture['created'])}\n"
        f"source_type: {capture['source_type']}\n"
        f"source: {_yaml_string(capture['source'])}\n"
        f"requested_processing: {capture['requested_processing']}\n"
        f"ai_status: {ai_status}\n"
        "review_status: unreviewed\n"
        "---\n"
        f"# {title}\n\n"
        f"{body}\n"
    )


def build_content_capture(
    capture: Mapping[str, Any],
    structured_suggestion: Optional[Mapping[str, Any]] = None,
) -> dict[str, str]:
    """Build a lossless local save result for the `收集內容` Shortcut."""

    request = validate_content_capture(capture)
    requested = request["requested_processing"]
    if requested == "raw_save":
        if structured_suggestion is not None:
            raise TwoEntryCaptureError("raw_save cannot include an AI suggestion")
        ai_status = "none"
        suggestion = None
        notification = "✓ 已保存"
    elif structured_suggestion is None:
        ai_status = "pending"
        suggestion = None
        notification = "✓ 已保存，待稍後整理"
    else:
        if not request["raw_content"].strip():
            raise TwoEntryCaptureError("cannot structure content that was not supplied")
        suggestion = validate_content_suggestion(structured_suggestion)
        if suggestion["processing_mode"] != requested:
            raise TwoEntryCaptureError("suggestion mode does not match the request")
        ai_status = "suggested"
        notification = "✓ 已整理並保存"
    return {
        "source_type": request["source_type"],
        "ai_status": ai_status,
        "notification": notification,
        "markdown": _render_content_markdown(
            request,
            ai_status=ai_status,
            suggestion=suggestion,
        ),
    }


def build_voice_flash(
    capture: Mapping[str, Any],
    structured_output: Optional[Mapping[str, Any]] = None,
) -> dict[str, str]:
    """Build one lossless `語音閃念` result by reusing the P1.3 contract."""

    request = validate_voice_input(capture)
    if structured_output is None:
        ai_status = "pending"
        notification = "✓ 已保存，待稍後整理"
    else:
        validate_structured_voice_output(
            structured_output,
            allowed_projects=request["allowed_projects"],
        )
        ai_status = "suggested"
        notification = "✓ 已整理並保存"
    return {
        "ai_status": ai_status,
        "notification": notification,
        "markdown": render_voice_markdown(request, structured_output),
    }
