from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Iterable

from .core import (
    ProtectedPathError,
    UnsafePathError,
    _read_inbox_prefix,
    guard_local_path,
    is_protected_path,
    load_protected_patterns,
    parse_iso_date,
)
from .date_review import (
    DATE_EVENT_TYPES,
    EVENT_METADATA,
    DateReviewEvent,
    calculate_date_status,
)

MAX_DUE_SELECTIONS = 50
EVENT_FIELDS = dict(EVENT_METADATA)
EVENT_ORDER = {name: index for index, name in enumerate(DATE_EVENT_TYPES)}


@dataclass(frozen=True)
class DueSelection:
    event_type: str
    expected_date: date
    relative_path: str

    @property
    def selection_key(self) -> str:
        return (
            f"{self.event_type}::{self.expected_date.isoformat()}::"
            f"{self.relative_path}"
        )


@dataclass(frozen=True)
class ValidatedDueSelections:
    events: tuple[DateReviewEvent, ...]
    diagnostics: tuple[str, ...] = ()


def parse_due_selection(value: str) -> DueSelection:
    parts = value.split("::", 2)
    if len(parts) != 3 or not all(parts):
        raise ValueError("Invalid due selection format.")
    event_type, raw_date, relative_path = parts
    if event_type not in DATE_EVENT_TYPES:
        raise ValueError(f"Unsupported due event type: {event_type}")
    try:
        expected_date = parse_iso_date(raw_date, "Due selection date")
    except ValueError as exc:
        raise ValueError("Due selection date must use YYYY-MM-DD.") from exc
    return DueSelection(event_type, expected_date, relative_path)


def _selection_path(selection: DueSelection, vault: Path) -> Path:
    relative = PurePosixPath(selection.relative_path)
    if relative.is_absolute() or selection.relative_path.startswith("/"):
        raise ValueError("Due selection path must be Vault-relative.")
    if ".." in relative.parts:
        raise ValueError("Due selection path must not contain traversal.")

    path = vault.joinpath(*relative.parts)
    try:
        patterns = load_protected_patterns(vault)
    except UnsafePathError as exc:
        raise ValueError(
            "Selected note or ancestor is a symbolic link."
        ) from exc
    if is_protected_path(path, vault, patterns):
        raise ValueError("Selected note is blocked by protected-path policy.")
    if len(relative.parts) != 2 or relative.parts[0] != "00_Inbox":
        raise ValueError(
            "Due selection must reference a direct Inbox Markdown note."
        )
    if Path(relative.name).suffix.lower() != ".md":
        raise ValueError("Selected note is not a regular Markdown file.")

    try:
        guard_local_path(path, vault, patterns)
    except ProtectedPathError as exc:
        raise ValueError(
            "Selected note is blocked by protected-path policy."
        ) from exc
    except UnsafePathError as exc:
        raise ValueError(
            "Selected note or ancestor is a symbolic link."
        ) from exc
    try:
        mode = os.lstat(str(path)).st_mode
    except FileNotFoundError as exc:
        raise ValueError("Selected Inbox note no longer exists.") from exc
    if stat.S_ISLNK(mode):
        raise ValueError("Selected note or ancestor is a symbolic link.")
    if not stat.S_ISREG(mode):
        raise ValueError("Selected note is not a regular Markdown file.")
    return path


def validate_due_selection(
    *,
    vault: Path,
    selection: DueSelection,
    as_of: date,
    window_days: int,
) -> DateReviewEvent:
    path = _selection_path(selection, vault)
    try:
        title, metadata = _read_inbox_prefix(path, require_metadata=False)
    except OSError as exc:
        raise ValueError("Selected Inbox note could not be read.") from exc
    field = EVENT_FIELDS[selection.event_type]
    raw_current = metadata.get(field, "")
    event_label = field.lower()
    if not raw_current:
        raise ValueError(
            f"Selected {event_label} no longer exists."
        )
    try:
        current_date = parse_iso_date(raw_current, field)
    except ValueError as exc:
        raise ValueError("Due selection is stale.") from exc
    if current_date != selection.expected_date:
        raise ValueError(
            "Due selection is stale. "
            f"Expected {event_label}: {selection.expected_date.isoformat()}. "
            f"Current {event_label}: {current_date.isoformat()}. "
            f"Path: {selection.relative_path}"
        )

    days_until, status = calculate_date_status(current_date, as_of, window_days)
    return DateReviewEvent(
        event_type=selection.event_type,
        event_date=current_date,
        days_until=days_until,
        status=status,
        title=title or path.stem,
        suggested_category=metadata.get("Suggested Category", ""),
        action_required=metadata.get("Action Required", ""),
        reminder_note=metadata.get("Reminder Note", ""),
        related_project=metadata.get("Related Project", ""),
        related_area=metadata.get("Related Area", ""),
        source_type=metadata.get("Source Type", ""),
        relative_path=selection.relative_path,
    )


def validate_due_selections(
    *,
    vault: Path,
    values: Iterable[str],
    as_of: date,
    window_days: int,
) -> ValidatedDueSelections:
    raw_values = tuple(values)
    if len(raw_values) > MAX_DUE_SELECTIONS:
        raise ValueError(
            f"Too many due selections (maximum {MAX_DUE_SELECTIONS})."
        )
    if not 1 <= window_days <= 365:
        raise ValueError("Due-soon window must be between 1 and 365 days.")

    unique: list[DueSelection] = []
    seen: set[str] = set()
    diagnostics: list[str] = []
    for value in raw_values:
        selection = parse_due_selection(value)
        if selection.selection_key in seen:
            diagnostics.append(
                f"Duplicate due selection ignored: {selection.selection_key}"
            )
            continue
        seen.add(selection.selection_key)
        unique.append(selection)

    events = [
        validate_due_selection(
            vault=vault,
            selection=selection,
            as_of=as_of,
            window_days=window_days,
        )
        for selection in unique
    ]
    events.sort(
        key=lambda event: (
            event.event_date,
            EVENT_ORDER[event.event_type],
            event.title.casefold(),
            event.relative_path,
        )
    )
    return ValidatedDueSelections(tuple(events), tuple(diagnostics))
