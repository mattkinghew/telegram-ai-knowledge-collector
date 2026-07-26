from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .core import (
    DisabledSummarizer,
    DuplicateResult,
    ExtractedSource,
    UnsafePathError,
    _guard_no_symlinks,
    capture_inbox_note,
    extract_source,
    load_protected_patterns,
    validate_optional_iso_date,
)

HANDOFF_SCHEMA_VERSION = 1
MAX_HANDOFF_BYTES = 256 * 1024
MAX_PREVIEW_CONTENT = 2_000
SOURCE_TYPES = ("text", "url", "voice_transcript")
HANDOFF_FIELDS = (
    "schema_version",
    "handoff_id",
    "source_type",
    "title",
    "content",
    "source_url",
    "captured_at",
    "action_required",
    "deadline",
    "resource_expiry",
    "reminder_date",
    "reminder_note",
    "related_project",
    "related_area",
)
STRING_FIELDS = HANDOFF_FIELDS[1:]
SINGLE_LINE_FIELDS = (
    "handoff_id",
    "title",
    "source_url",
    "captured_at",
    "action_required",
    "deadline",
    "resource_expiry",
    "reminder_date",
    "reminder_note",
    "related_project",
    "related_area",
)
FIELD_LIMITS = {
    "handoff_id": (1, 128),
    "source_type": (1, 32),
    "title": (1, 200),
    "content": (0, 50_000),
    "source_url": (0, 2_048),
    "captured_at": (1, 64),
    "action_required": (0, 500),
    "deadline": (0, 10),
    "resource_expiry": (0, 10),
    "reminder_date": (0, 10),
    "reminder_note": (0, 500),
    "related_project": (0, 200),
    "related_area": (0, 200),
}
HANDOFF_ID_PATTERN = re.compile(r"^[A-Za-z0-9_.:-]+$")


class HandoffValidationError(ValueError):
    pass


class HandoffFileSafetyError(UnsafePathError):
    pass


@dataclass(frozen=True)
class MobileHandoff:
    schema_version: int
    handoff_id: str
    source_type: str
    title: str
    content: str
    source_url: str
    captured_at: str
    action_required: str
    deadline: str
    resource_expiry: str
    reminder_date: str
    reminder_note: str
    related_project: str
    related_area: str


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise HandoffValidationError(
                f"Handoff JSON contains a duplicate key: {key}."
            )
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> None:
    raise HandoffValidationError(f"Handoff JSON contains an invalid number: {value}.")


def read_handoff_file(path: Path) -> bytes:
    expanded = Path(os.path.abspath(os.path.expanduser(str(path))))
    if expanded.suffix.lower() != ".json":
        raise HandoffFileSafetyError("Handoff file must use the .json extension.")
    try:
        _guard_no_symlinks(expanded)
    except UnsafePathError as exc:
        raise HandoffFileSafetyError(
            "Handoff file or ancestor is a symbolic link."
        ) from exc
    try:
        mode = os.lstat(str(expanded)).st_mode
    except FileNotFoundError as exc:
        raise HandoffFileSafetyError("Handoff file does not exist.") from exc
    if not stat.S_ISREG(mode):
        raise HandoffFileSafetyError(
            "Handoff file must be a regular JSON file."
        )
    size = os.lstat(str(expanded)).st_size
    if size > MAX_HANDOFF_BYTES:
        raise HandoffFileSafetyError("Handoff file exceeds 256 KB.")
    with expanded.open("rb") as handle:
        raw = handle.read(MAX_HANDOFF_BYTES + 1)
    if len(raw) > MAX_HANDOFF_BYTES:
        raise HandoffFileSafetyError("Handoff file exceeds 256 KB.")
    return raw


def parse_handoff_bytes(raw: bytes) -> MobileHandoff:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HandoffFileSafetyError("Handoff file must be valid UTF-8.") from exc
    try:
        payload = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite,
        )
    except HandoffValidationError:
        raise
    except json.JSONDecodeError as exc:
        raise HandoffValidationError("Handoff file contains invalid JSON.") from exc
    return validate_handoff_payload(payload)


def _validate_captured_at(value: str) -> None:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise HandoffValidationError(
            "captured_at must be an ISO-8601 datetime with a timezone."
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise HandoffValidationError("captured_at must include a timezone.")


def _validate_url(value: str) -> None:
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise HandoffValidationError(
            "URL handoff source_url must not contain control characters."
        )
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError as exc:
        raise HandoffValidationError(
            "URL handoff requires an HTTP or HTTPS source_url."
        ) from exc
    if (
        parsed.scheme.lower() not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or (port is not None and not 1 <= port <= 65535)
    ):
        raise HandoffValidationError(
            "URL handoff requires an HTTP or HTTPS source_url without embedded credentials."
        )


def validate_handoff_payload(payload: object) -> MobileHandoff:
    if not isinstance(payload, dict):
        raise HandoffValidationError("Handoff JSON must be one object.")
    unknown = sorted(set(payload) - set(HANDOFF_FIELDS))
    if unknown:
        raise HandoffValidationError(f"Unknown handoff field: {unknown[0]}.")
    missing = [field for field in HANDOFF_FIELDS if field not in payload]
    if missing:
        raise HandoffValidationError(f"Missing handoff field: {missing[0]}.")
    if type(payload["schema_version"]) is not int:
        raise HandoffValidationError("schema_version must be the integer 1.")
    if payload["schema_version"] != HANDOFF_SCHEMA_VERSION:
        raise HandoffValidationError(
            f"Unsupported handoff schema version: {payload['schema_version']}."
        )
    for field in STRING_FIELDS:
        value = payload[field]
        if not isinstance(value, str):
            raise HandoffValidationError(f"Handoff {field} must be a string.")
        minimum, maximum = FIELD_LIMITS[field]
        if not minimum <= len(value) <= maximum:
            if minimum:
                raise HandoffValidationError(
                    f"Handoff {field} must be {minimum}–{maximum} characters."
                )
            raise HandoffValidationError(
                f"Handoff {field} must not exceed {maximum} characters."
            )
        if field in SINGLE_LINE_FIELDS and ("\n" in value or "\r" in value):
            raise HandoffValidationError(
                f"Handoff {field} must not contain newlines."
            )
        if field in SINGLE_LINE_FIELDS and any(
            ord(character) < 32 or ord(character) == 127 for character in value
        ):
            raise HandoffValidationError(
                f"Handoff {field} must not contain control characters."
            )

    if not HANDOFF_ID_PATTERN.fullmatch(payload["handoff_id"]):
        raise HandoffValidationError(
            "Handoff handoff_id contains unsupported characters."
        )
    if payload["source_type"] not in SOURCE_TYPES:
        raise HandoffValidationError(
            f"Unsupported handoff source type: {payload['source_type']}."
        )
    for field, label in (
        ("deadline", "Deadline"),
        ("resource_expiry", "Resource Expiry"),
        ("reminder_date", "Reminder Date"),
    ):
        try:
            validate_optional_iso_date(payload[field], label)
        except ValueError as exc:
            raise HandoffValidationError(str(exc)) from exc
    _validate_captured_at(payload["captured_at"])

    source_type = payload["source_type"]
    content = payload["content"]
    source_url = payload["source_url"]
    if source_type == "text":
        if not content.strip():
            raise HandoffValidationError("Text handoff content must not be empty.")
        if source_url:
            raise HandoffValidationError(
                "Text handoff source_url must be empty."
            )
    elif source_type == "url":
        if not source_url:
            raise HandoffValidationError(
                "URL handoff requires an HTTP or HTTPS source_url."
            )
        _validate_url(source_url)
    else:
        if not content.strip():
            raise HandoffValidationError(
                "Voice transcript content must not be empty."
            )
        if source_url:
            raise HandoffValidationError(
                "Voice transcript source_url must be empty."
            )
    return MobileHandoff(**payload)


def load_handoff(path: Path) -> MobileHandoff:
    return parse_handoff_bytes(read_handoff_file(path))


def format_handoff_preview(
    handoff: MobileHandoff,
    *,
    show_content: bool = False,
) -> str:
    lines = [
        "Handoff is valid.",
        "",
        f"Handoff ID: {handoff.handoff_id}",
        f"Source Type: {handoff.source_type}",
        f"Title: {handoff.title}",
        f"Captured At: {handoff.captured_at}",
        f"Content Characters: {len(handoff.content)}",
        f"Action Required: {handoff.action_required}",
        f"Deadline: {handoff.deadline}",
        f"Resource Expiry: {handoff.resource_expiry}",
        f"Reminder Date: {handoff.reminder_date}",
        f"Related Project: {handoff.related_project}",
        f"Related Area: {handoff.related_area}",
    ]
    if show_content:
        content = handoff.content[:MAX_PREVIEW_CONTENT]
        lines.extend(("", "Content:", content))
        if len(handoff.content) > MAX_PREVIEW_CONTENT:
            lines.append(
                f"[Content truncated after {MAX_PREVIEW_CONTENT} characters.]"
            )
    return "\n".join(lines)


def _handoff_source(handoff: MobileHandoff, vault: Path) -> ExtractedSource:
    patterns = load_protected_patterns(vault)
    if handoff.source_type == "text":
        return extract_source(
            vault=vault,
            patterns=patterns,
            text=handoff.content,
        )
    if handoff.source_type == "url":
        source = extract_source(
            vault=vault,
            patterns=patterns,
            url=handoff.source_url,
        )
        return ExtractedSource(
            source_type=source.source_type,
            source_url=source.source_url,
            processing_status=source.processing_status,
            source_notes=handoff.content
            or "URL recorded; remote content was not fetched.",
            content_hash=source.content_hash,
        )
    content = handoff.content.strip()
    return ExtractedSource(
        source_type="voice_transcript",
        processing_status="transcript_registered",
        readable_text=content,
        source_notes=content,
        content_hash=hashlib.sha256(content.encode()).hexdigest(),
    )


def import_handoff(
    *,
    vault: Path,
    file_path: Path,
) -> tuple[Path, DuplicateResult]:
    handoff = load_handoff(file_path)
    source = _handoff_source(handoff, vault)
    metadata = (
        ("Handoff Schema Version", str(handoff.schema_version)),
        ("Handoff ID", handoff.handoff_id),
        ("Handoff Source Type", handoff.source_type),
        ("Handoff Captured At", handoff.captured_at),
        (
            "Transcript Review Status",
            "pending"
            if handoff.source_type == "voice_transcript"
            else "not_applicable",
        ),
    )
    review_items = ("Mobile handoff reviewed",)
    if handoff.source_type == "voice_transcript":
        review_items += ("Voice transcript checked",)
    return capture_inbox_note(
        vault=vault,
        source=source,
        title=handoff.title,
        summarizer=DisabledSummarizer(),
        action_required=handoff.action_required,
        deadline=handoff.deadline,
        resource_expiry=handoff.resource_expiry,
        reminder_date=handoff.reminder_date,
        reminder_note=handoff.reminder_note,
        related_project=handoff.related_project,
        related_area=handoff.related_area,
        extra_metadata=metadata,
        extra_review_items=review_items,
    )
