#!/usr/bin/env python3
"""Dependency-free oracle for the mobile capture contract.

This module never opens Obsidian, accesses a Vault, or makes a network request.
It only validates fictional structured input, renders Markdown, and constructs
an ``obsidian://new`` URI for offline contract testing.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence
from urllib.parse import quote, urlencode, urlparse


SCHEMA_VERSION = "1"
MAX_RAW_CONTENT_CHARS = 50_000
SOURCE_TYPES = frozenset(
    {
        "personal",
        "clipboard",
        "voice_transcript",
        "url",
        "shared_text",
        "image_reference",
        "file_reference",
    }
)
OUTPUT_GOALS = frozenset(
    {"collect", "task", "content", "project_knowledge", "progress", "decision"}
)
CAPTURE_FIELDS = frozenset(
    {
        "schema_version",
        "captured_at",
        "source_type",
        "source",
        "raw_content",
        "insight",
        "context",
        "action",
        "output_goal",
        "project",
    }
)
REQUIRED_CAPTURE_FIELDS = frozenset(
    {
        "schema_version",
        "captured_at",
        "source_type",
        "raw_content",
        "insight",
    }
)


class MobileCaptureValidationError(ValueError):
    """Raised when a mobile capture violates the canonical contract."""


def _normalize_line_endings(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n")


def _require_string(
    payload: Mapping[str, Any],
    name: str,
    *,
    max_length: int,
    allow_empty: bool = True,
) -> str:
    value = payload.get(name, "")
    if value is None and allow_empty:
        value = ""
    if not isinstance(value, str):
        raise MobileCaptureValidationError(f"{name} must be a string")
    value = _normalize_line_endings(value)
    if len(value) > max_length:
        raise MobileCaptureValidationError(f"{name} exceeds {max_length} characters")
    if not allow_empty and not value.strip():
        raise MobileCaptureValidationError(f"{name} is required")
    return value


def _normalize_timestamp(value: str) -> str:
    if not isinstance(value, str) or not value:
        raise MobileCaptureValidationError("captured_at is required")
    parse_value = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        timestamp = datetime.fromisoformat(parse_value)
    except ValueError as exc:
        raise MobileCaptureValidationError(
            "captured_at must be an ISO-8601 timestamp"
        ) from exc
    if timestamp.tzinfo is None:
        raise MobileCaptureValidationError("captured_at must include a UTC offset")
    timestamp = timestamp.replace(microsecond=0)
    normalized = timestamp.isoformat()
    if normalized.endswith("+00:00"):
        return normalized[:-6] + "Z"
    return normalized


def _validate_source(source_type: str, source: str) -> None:
    if "\n" in source:
        raise MobileCaptureValidationError("source must be a single line")
    if source_type == "url":
        parsed = urlparse(source)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or parsed.username is not None
            or parsed.password is not None
            or any(character.isspace() for character in source)
        ):
            raise MobileCaptureValidationError(
                "URL source must be a valid HTTP or HTTPS URL without credentials"
            )
        return
    if source_type in {"personal", "clipboard", "voice_transcript", "shared_text"}:
        if source:
            raise MobileCaptureValidationError(
                f"source must be blank for {source_type}"
            )
        return
    if source_type in {"image_reference", "file_reference"}:
        if "/" in source or "\\" in source or source in {".", ".."}:
            raise MobileCaptureValidationError(
                "reference source must be a filename, not a path"
            )
        return
    if source.startswith(('/', '\\')) or re.match(r"^[A-Za-z]:[\\/]", source):
        raise MobileCaptureValidationError("source must not contain an absolute path")


def normalize_capture_input(payload: Mapping[str, Any]) -> dict[str, str]:
    """Validate and normalize a canonical capture without rewriting user text."""

    if not isinstance(payload, Mapping):
        raise MobileCaptureValidationError("capture must be an object")
    unknown = set(payload) - CAPTURE_FIELDS
    missing = REQUIRED_CAPTURE_FIELDS - set(payload)
    if unknown:
        raise MobileCaptureValidationError(
            "unexpected fields: " + ", ".join(sorted(unknown))
        )
    if missing:
        raise MobileCaptureValidationError(
            "missing fields: " + ", ".join(sorted(missing))
        )
    if payload["schema_version"] != SCHEMA_VERSION:
        raise MobileCaptureValidationError(
            f"schema_version must be {SCHEMA_VERSION!r}"
        )

    source_type_value = payload["source_type"]
    if not isinstance(source_type_value, str):
        raise MobileCaptureValidationError("source_type must be a string")
    source_type = source_type_value.strip().lower()
    if source_type not in SOURCE_TYPES:
        raise MobileCaptureValidationError("unsupported source_type")

    output_goal_value = payload.get("output_goal", "collect")
    if not isinstance(output_goal_value, str):
        raise MobileCaptureValidationError("output_goal must be a string")
    output_goal = output_goal_value.strip().lower()
    if output_goal not in OUTPUT_GOALS:
        raise MobileCaptureValidationError("unsupported output_goal")

    source = _require_string(payload, "source", max_length=2_048)
    _validate_source(source_type, source)
    normalized = {
        "schema_version": SCHEMA_VERSION,
        "captured_at": _normalize_timestamp(payload["captured_at"]),
        "source_type": source_type,
        "source": source,
        "raw_content": _require_string(
            payload,
            "raw_content",
            max_length=MAX_RAW_CONTENT_CHARS,
            allow_empty=False,
        ),
        "insight": _require_string(
            payload, "insight", max_length=2_000, allow_empty=False
        ),
        "context": _require_string(payload, "context", max_length=2_000),
        "action": _require_string(payload, "action", max_length=1_000),
        "output_goal": output_goal,
        "project": _require_string(payload, "project", max_length=200),
    }
    for name in ("insight", "project"):
        if "\n" in normalized[name]:
            raise MobileCaptureValidationError(f"{name} must be a single line")
    return normalized


def validate_mobile_capture(payload: Mapping[str, Any]) -> dict[str, str]:
    """Public validation entrypoint for the canonical capture contract."""

    return normalize_capture_input(payload)


def _yaml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _render_list(values: Sequence[Any]) -> list[str]:
    return [f"- {value}" for value in values if isinstance(value, str) and value]


def _render_ai_suggestions(ai_suggestions: Mapping[str, Any]) -> list[str]:
    lines = ["## AI 整理建議", "", "> 以下內容是未確認建議；不得視為來源事實。"]
    scalar_fields = (
        ("one_sentence_insight", "一句洞見"),
        ("suggested_next_action", "建議下一步"),
        ("output_angle", "可形成的輸出"),
        ("related_project", "建議關聯專案"),
        ("confidence", "信心"),
    )
    list_fields = (
        ("supporting_points", "支持重點"),
        ("possible_applications", "可能應用"),
        ("facts_to_verify", "需要核實"),
        ("missing_information", "缺失資料"),
    )
    for key, label in scalar_fields:
        value = ai_suggestions.get(key)
        if isinstance(value, str) and value:
            lines.extend(("", f"### {label}", "", value))
    for key, label in list_fields:
        value = ai_suggestions.get(key)
        if isinstance(value, list):
            rendered = _render_list(value)
            if rendered:
                lines.extend(("", f"### {label}", "", *rendered))
    return lines


def render_mobile_markdown(
    capture: Mapping[str, Any],
    *,
    ai_suggestions: Optional[Mapping[str, Any]] = None,
) -> str:
    """Render deterministic Markdown while preserving source and user layers."""

    normalized = normalize_capture_input(capture)
    ai_status = "suggested" if ai_suggestions is not None else "none"
    source = _yaml_string(normalized["source"]) if normalized["source"] else ""
    project = _yaml_string(normalized["project"]) if normalized["project"] else ""
    lines = [
        "---",
        "status: inbox",
        f"created: {normalized['captured_at']}",
        f"source_type: {normalized['source_type']}",
        f"source: {source}",
        f"project: {project}",
        f"output_goal: {normalized['output_goal']}",
        f"ai_status: {ai_status}",
        "---",
        "",
        f"# {normalized['insight']}",
    ]
    for heading, value in (
        ("## 原始內容", normalized["raw_content"]),
        ("## 最值得記住", normalized["insight"]),
        ("## 可以幫我處理", normalized["context"]),
        ("## 下一步", normalized["action"]),
    ):
        if lines[-1] != "":
            lines.append("")
        lines.extend((heading, ""))
        if value:
            lines.append(value)
    if ai_suggestions is not None:
        lines.extend(("", *_render_ai_suggestions(ai_suggestions)))
    return "\n".join(lines) + "\n"


def build_mobile_filename(captured_at: str, *, unique_suffix: str) -> str:
    """Return a flat-Inbox timestamp path with a supplied four-digit suffix."""

    normalized = _normalize_timestamp(captured_at)
    parsed = datetime.fromisoformat(
        normalized[:-1] + "+00:00" if normalized.endswith("Z") else normalized
    )
    if not isinstance(unique_suffix, str) or not re.fullmatch(
        r"[0-9]{4}", unique_suffix
    ):
        raise MobileCaptureValidationError("unique_suffix must be four digits")
    base = f"00_Inbox/{parsed.strftime('%Y-%m-%d-%H%M%S')}"
    return f"{base}-{unique_suffix}"


def build_obsidian_uri(vault: str, file_path: str, content: str) -> str:
    """Construct but never open a standard percent-encoded Obsidian URI."""

    for name, value in (("vault", vault), ("file", file_path), ("content", content)):
        if not isinstance(value, str) or not value:
            raise MobileCaptureValidationError(f"{name} must be a non-empty string")
    if not file_path.startswith("00_Inbox/") or file_path.count("/") != 1:
        raise MobileCaptureValidationError("file must be a direct child of 00_Inbox")
    query = urlencode(
        (("vault", vault), ("file", file_path), ("content", content)),
        doseq=False,
        safe="",
        quote_via=quote,
    )
    return f"obsidian://new?{query}"


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Render a fictional mobile capture without opening Obsidian."
    )
    parser.add_argument("capture", type=Path, help="Path to canonical capture JSON")
    parser.add_argument("--vault", default="EXAMPLE_VAULT_ID")
    parser.add_argument(
        "--suffix",
        required=True,
        help="Deterministic four-digit filename suffix for this offline oracle",
    )
    args = parser.parse_args(argv)
    payload = json.loads(args.capture.read_text(encoding="utf-8"))
    capture = payload["capture"] if "capture" in payload else payload
    normalized = validate_mobile_capture(capture)
    markdown = render_mobile_markdown(normalized)
    print(
        build_obsidian_uri(
            args.vault,
            build_mobile_filename(
                normalized["captured_at"], unique_suffix=args.suffix
            ),
            markdown,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
