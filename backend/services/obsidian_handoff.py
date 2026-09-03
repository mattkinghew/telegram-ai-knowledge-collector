"""Pure, Vault-independent metadata for the iPhone-to-Obsidian handoff."""

from __future__ import annotations

import re
from typing import Iterable, Optional


FOLDER_KEYS = {
    "daily_control": "Daily",
    "work_log": "Work",
    "reflection": "Reflection",
    "todo": "Tasks",
    "meeting_followup": "Meetings",
    "free": "Inbox",
}
_INVALID_FILENAME = re.compile(r'[\\/:*?"<>|\x00-\x1f\x7f]')
_DOT_RUN = re.compile(r"\.{2,}")
_WHITESPACE = re.compile(r"\s+")
_SPACES_AROUND_DASH = re.compile(r"\s*-\s*")
MAX_TITLE_LENGTH = 100


def sanitize_note_title(title: str) -> str:
    """Return a deterministic, CJK-preserving single filename component."""

    value = _INVALID_FILENAME.sub("-", str(title))
    value = _DOT_RUN.sub("-", value)
    value = _WHITESPACE.sub(" ", value).strip(" .")
    value = _SPACES_AROUND_DASH.sub("-", value).strip("- .")
    value = value[:MAX_TITLE_LENGTH].rstrip(" .")
    return value or "Captured item"


def build_suggested_filename(
    suggested_date: str,
    title: str,
    *,
    existing_names: Optional[Iterable[str]] = None,
) -> str:
    """Build a date-prefixed Markdown filename without inspecting a Vault."""

    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", suggested_date):
        raise ValueError("suggested_date must use YYYY-MM-DD")
    base = f"{suggested_date}-{sanitize_note_title(title)}"
    filename = f"{base}.md"
    existing = set(existing_names or ())
    suffix = 2
    while filename in existing:
        filename = f"{base}-{suffix}.md"
        suffix += 1
    return filename


def folder_for_record_type(record_type: str) -> str:
    """Map an allow-listed record type to a logical folder key only."""

    try:
        return FOLDER_KEYS[record_type]
    except KeyError as exc:
        raise ValueError("unsupported record_type") from exc


def build_obsidian_handoff(
    *,
    markdown: str,
    suggested_date: str,
    record_type: str,
    title: str,
    existing_names: Optional[Iterable[str]] = None,
) -> dict[str, str]:
    """Return additive Shortcut metadata; no absolute path or Vault ID is included."""

    folder_for_record_type(record_type)
    safe_title = sanitize_note_title(title)
    return {
        "markdown": markdown,
        "suggested_filename": build_suggested_filename(
            suggested_date, safe_title, existing_names=existing_names
        ),
        "suggested_date": suggested_date,
        "record_type": record_type,
        "title": safe_title,
        "folder_key": record_type,
    }
