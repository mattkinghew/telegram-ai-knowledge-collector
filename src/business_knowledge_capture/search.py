from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterable, Optional

from .core import (
    CATEGORIES,
    MAX_INBOX_CANDIDATES,
    _read_inbox_prefix,
    list_safe_inbox_candidates,
    parse_iso_date,
)

MAX_SEARCH_RESULTS = 200
DEFAULT_SEARCH_LIMIT = 50
MAX_SEARCH_DIAGNOSTICS = 20
SEARCH_SORTS = (
    "created-desc",
    "created-asc",
    "deadline-asc",
    "deadline-desc",
    "title-asc",
    "title-desc",
)
SOURCE_TYPES = ("text", "url", "file", "voice_transcript")
DUPLICATE_STATUSES = ("unique", "exact_duplicate_suggested", "check_unavailable")


@dataclass(frozen=True)
class InboxSearchRecord:
    title: str
    created: Optional[date]
    suggested_category: str
    deadline: Optional[date]
    related_project: str
    related_area: str
    source_type: str
    file_type: str
    processing_status: str
    duplicate_status: str
    action_required: str
    relative_path: str
    source_filename: str = ""
    duplicate_match_type: str = ""
    resource_expiry: Optional[date] = None
    reminder_date: Optional[date] = None
    reminder_note: str = ""


@dataclass(frozen=True)
class InboxSearchQuery:
    title: str = ""
    keyword: str = ""
    categories: tuple[str, ...] = ()
    created_from: Optional[date] = None
    created_to: Optional[date] = None
    deadline_from: Optional[date] = None
    deadline_to: Optional[date] = None
    resource_expiry_from: Optional[date] = None
    resource_expiry_to: Optional[date] = None
    reminder_from: Optional[date] = None
    reminder_to: Optional[date] = None
    related_project: str = ""
    related_area: str = ""
    source_types: tuple[str, ...] = ()
    file_types: tuple[str, ...] = ()
    processing_statuses: tuple[str, ...] = ()
    duplicate_statuses: tuple[str, ...] = ()
    has_deadline: bool = False
    missing_deadline: bool = False
    has_resource_expiry: bool = False
    missing_resource_expiry: bool = False
    has_reminder: bool = False
    missing_reminder: bool = False
    has_action: bool = False
    missing_action: bool = False
    sort: str = "created-desc"
    limit: int = DEFAULT_SEARCH_LIMIT


@dataclass(frozen=True)
class InboxSearchResult:
    query: InboxSearchQuery
    total_matches: int
    records: tuple[InboxSearchRecord, ...]
    diagnostics: tuple[str, ...] = ()


def parse_filter_date(value: str, label: str) -> Optional[date]:
    if not value:
        return None
    return parse_iso_date(value, label)


def _metadata_date(value: str) -> Optional[date]:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        try:
            return datetime.fromisoformat(value).date()
        except ValueError:
            return None


def validate_search_query(query: InboxSearchQuery) -> None:
    if not 1 <= query.limit <= MAX_SEARCH_RESULTS:
        raise ValueError(f"Search limit must be between 1 and {MAX_SEARCH_RESULTS}.")
    if query.sort not in SEARCH_SORTS:
        raise ValueError(f"Search sort must be one of: {', '.join(SEARCH_SORTS)}.")
    if query.has_deadline and query.missing_deadline:
        raise ValueError("--has-deadline and --missing-deadline are mutually exclusive.")
    if query.has_action and query.missing_action:
        raise ValueError("--has-action and --missing-action are mutually exclusive.")
    if query.has_resource_expiry and query.missing_resource_expiry:
        raise ValueError(
            "--has-resource-expiry and --missing-resource-expiry are mutually exclusive."
        )
    if query.has_reminder and query.missing_reminder:
        raise ValueError("--has-reminder and --missing-reminder are mutually exclusive.")
    invalid_categories = [value for value in query.categories if value not in CATEGORIES]
    if invalid_categories:
        raise ValueError(f"Category must be one of: {', '.join(CATEGORIES)}.")
    invalid_source_types = [value for value in query.source_types if value not in SOURCE_TYPES]
    if invalid_source_types:
        raise ValueError(f"Source type must be one of: {', '.join(SOURCE_TYPES)}.")
    invalid_duplicate_statuses = [
        value for value in query.duplicate_statuses if value not in DUPLICATE_STATUSES
    ]
    if invalid_duplicate_statuses:
        raise ValueError(
            f"Duplicate status must be one of: {', '.join(DUPLICATE_STATUSES)}."
        )
    for start, end, label in (
        (query.created_from, query.created_to, "Created"),
        (query.deadline_from, query.deadline_to, "Deadline"),
        (
            query.resource_expiry_from,
            query.resource_expiry_to,
            "Resource Expiry",
        ),
        (query.reminder_from, query.reminder_to, "Reminder"),
    ):
        if start and end and start > end:
            raise ValueError(f"{label} start date must not be after end date.")


def _contains(value: str, query: str) -> bool:
    return query.casefold() in value.casefold()


def _matches_any_exact(value: str, filters: Iterable[str]) -> bool:
    choices = tuple(item.casefold() for item in filters)
    return not choices or value.casefold() in choices


def _matches(record: InboxSearchRecord, query: InboxSearchQuery) -> bool:
    if query.title and not _contains(record.title, query.title):
        return False
    if query.keyword:
        keyword_fields = (
            record.title,
            record.suggested_category,
            record.action_required,
            record.related_project,
            record.related_area,
            record.source_filename,
            record.source_type,
            record.file_type,
            record.processing_status,
            record.duplicate_status,
            record.duplicate_match_type,
            record.reminder_note,
        )
        if not any(_contains(value, query.keyword) for value in keyword_fields):
            return False
    if not _matches_any_exact(record.suggested_category, query.categories):
        return False
    if query.created_from and (record.created is None or record.created < query.created_from):
        return False
    if query.created_to and (record.created is None or record.created > query.created_to):
        return False
    if query.deadline_from and (
        record.deadline is None or record.deadline < query.deadline_from
    ):
        return False
    if query.deadline_to and (
        record.deadline is None or record.deadline > query.deadline_to
    ):
        return False
    if query.resource_expiry_from and (
        record.resource_expiry is None
        or record.resource_expiry < query.resource_expiry_from
    ):
        return False
    if query.resource_expiry_to and (
        record.resource_expiry is None
        or record.resource_expiry > query.resource_expiry_to
    ):
        return False
    if query.reminder_from and (
        record.reminder_date is None or record.reminder_date < query.reminder_from
    ):
        return False
    if query.reminder_to and (
        record.reminder_date is None or record.reminder_date > query.reminder_to
    ):
        return False
    if query.has_deadline and record.deadline is None:
        return False
    if query.missing_deadline and record.deadline is not None:
        return False
    if query.has_resource_expiry and record.resource_expiry is None:
        return False
    if query.missing_resource_expiry and record.resource_expiry is not None:
        return False
    if query.has_reminder and record.reminder_date is None:
        return False
    if query.missing_reminder and record.reminder_date is not None:
        return False
    if query.related_project and not _contains(record.related_project, query.related_project):
        return False
    if query.related_area and not _contains(record.related_area, query.related_area):
        return False
    if not _matches_any_exact(record.source_type, query.source_types):
        return False
    if not _matches_any_exact(record.file_type, query.file_types):
        return False
    if not _matches_any_exact(record.processing_status, query.processing_statuses):
        return False
    if not _matches_any_exact(record.duplicate_status, query.duplicate_statuses):
        return False
    if query.has_action and not record.action_required.strip():
        return False
    if query.missing_action and record.action_required.strip():
        return False
    return True


def sort_search_records(
    records: Iterable[InboxSearchRecord],
    sort_mode: str,
) -> list[InboxSearchRecord]:
    values = sorted(records, key=lambda record: record.relative_path)
    if sort_mode.startswith("title-"):
        return sorted(
            values,
            key=lambda record: record.title.casefold(),
            reverse=sort_mode.endswith("-desc"),
        )
    field = "created" if sort_mode.startswith("created-") else "deadline"
    present = [record for record in values if getattr(record, field) is not None]
    missing = [record for record in values if getattr(record, field) is None]
    present.sort(
        key=lambda record: getattr(record, field),
        reverse=sort_mode.endswith("-desc"),
    )
    return present + missing


def search_inbox(
    *,
    vault: Path,
    query: InboxSearchQuery,
    max_candidates: int = MAX_INBOX_CANDIDATES,
) -> InboxSearchResult:
    validate_search_query(query)
    candidates, candidate_diagnostics = list_safe_inbox_candidates(
        vault=vault,
        max_candidates=max_candidates,
    )
    diagnostics = list(candidate_diagnostics)
    records: list[InboxSearchRecord] = []
    for candidate in candidates:
        relative = candidate.relative_to(vault).as_posix()
        try:
            title, metadata = _read_inbox_prefix(candidate, require_metadata=False)
        except OSError:
            title = ""
            metadata = {}
            diagnostics.append(f"{relative}: candidate could not be read.")
        except ValueError as exc:
            title = ""
            metadata = {}
            diagnostics.append(f"{relative}: {exc}")
        if not metadata:
            diagnostics.append(f"{relative}: missing or empty Metadata section.")
        if not title:
            title = candidate.stem
            diagnostics.append(f"{relative}: missing H1; filename used as title.")
        created_value = metadata.get("Created", "")
        deadline_value = metadata.get("Deadline", "")
        resource_expiry_value = metadata.get("Resource Expiry", "")
        reminder_value = metadata.get("Reminder Date", "")
        created = _metadata_date(created_value)
        deadline = _metadata_date(deadline_value)
        resource_expiry = None
        reminder_date = None
        if resource_expiry_value:
            try:
                resource_expiry = parse_iso_date(
                    resource_expiry_value, "Resource Expiry"
                )
            except ValueError:
                diagnostics.append(
                    f"{relative}: invalid Resource Expiry metadata ignored."
                )
        if reminder_value:
            try:
                reminder_date = parse_iso_date(reminder_value, "Reminder Date")
            except ValueError:
                diagnostics.append(f"{relative}: invalid Reminder Date metadata ignored.")
        if created_value and created is None:
            diagnostics.append(f"{relative}: invalid Created metadata ignored.")
        if deadline_value and deadline is None:
            diagnostics.append(f"{relative}: invalid Deadline metadata ignored.")
        record = InboxSearchRecord(
            title=title,
            created=created,
            suggested_category=metadata.get("Suggested Category", ""),
            deadline=deadline,
            resource_expiry=resource_expiry,
            reminder_date=reminder_date,
            reminder_note=metadata.get("Reminder Note", ""),
            related_project=metadata.get("Related Project", ""),
            related_area=metadata.get("Related Area", ""),
            source_type=metadata.get("Source Type", ""),
            file_type=metadata.get("File Type", ""),
            processing_status=metadata.get("Processing Status", ""),
            duplicate_status=metadata.get("Duplicate Status", ""),
            action_required=metadata.get("Action Required", ""),
            relative_path=relative,
            source_filename=metadata.get("Source Filename", ""),
            duplicate_match_type=metadata.get("Duplicate Match Type", ""),
        )
        if _matches(record, query):
            records.append(record)
    ordered = sort_search_records(records, query.sort)
    return InboxSearchResult(
        query=query,
        total_matches=len(ordered),
        records=tuple(ordered[: query.limit]),
        diagnostics=tuple(diagnostics),
    )


def _date_text(value: Optional[date]) -> str:
    return value.isoformat() if value else ""


def format_search_text(result: InboxSearchResult) -> str:
    lines = [f"Found {result.total_matches} result(s)."]
    for index, record in enumerate(result.records, start=1):
        lines.extend(
            (
                "",
                f"{index}. {record.title}",
                f"   Created: {_date_text(record.created)}",
                f"   Category: {record.suggested_category}",
                f"   Deadline: {_date_text(record.deadline)}",
                f"   Resource Expiry: {_date_text(record.resource_expiry)}",
                f"   Reminder Date: {_date_text(record.reminder_date)}",
                f"   Reminder Note: {record.reminder_note}",
                f"   Project: {record.related_project}",
                f"   Area: {record.related_area}",
                f"   Source: {record.source_type}",
                f"   File Type: {record.file_type}",
                f"   Status: {record.processing_status}",
                f"   Duplicate: {record.duplicate_status}",
                f"   Action: {record.action_required}",
                f"   Path: {record.relative_path}",
            )
        )
    return "\n".join(lines)


def _query_json(query: InboxSearchQuery) -> dict[str, object]:
    return {
        "title": query.title,
        "keyword": query.keyword,
        "categories": list(query.categories),
        "created_from": _date_text(query.created_from),
        "created_to": _date_text(query.created_to),
        "deadline_from": _date_text(query.deadline_from),
        "deadline_to": _date_text(query.deadline_to),
        "resource_expiry_from": _date_text(query.resource_expiry_from),
        "resource_expiry_to": _date_text(query.resource_expiry_to),
        "reminder_from": _date_text(query.reminder_from),
        "reminder_to": _date_text(query.reminder_to),
        "related_project": query.related_project,
        "related_area": query.related_area,
        "source_types": list(query.source_types),
        "file_types": list(query.file_types),
        "processing_statuses": list(query.processing_statuses),
        "duplicate_statuses": list(query.duplicate_statuses),
        "has_deadline": query.has_deadline,
        "missing_deadline": query.missing_deadline,
        "has_resource_expiry": query.has_resource_expiry,
        "missing_resource_expiry": query.missing_resource_expiry,
        "has_reminder": query.has_reminder,
        "missing_reminder": query.missing_reminder,
        "has_action": query.has_action,
        "missing_action": query.missing_action,
        "sort": query.sort,
        "limit": query.limit,
    }


def format_search_json(result: InboxSearchResult) -> str:
    records = [
        {
            "title": record.title,
            "created": _date_text(record.created),
            "suggested_category": record.suggested_category,
            "deadline": _date_text(record.deadline),
            "resource_expiry": _date_text(record.resource_expiry),
            "reminder_date": _date_text(record.reminder_date),
            "reminder_note": record.reminder_note,
            "related_project": record.related_project,
            "related_area": record.related_area,
            "source_type": record.source_type,
            "file_type": record.file_type,
            "processing_status": record.processing_status,
            "duplicate_status": record.duplicate_status,
            "action_required": record.action_required,
            "relative_path": record.relative_path,
        }
        for record in result.records
    ]
    return json.dumps(
        {
            "query": _query_json(result.query),
            "total_matches": result.total_matches,
            "returned": len(records),
            "results": records,
        },
        ensure_ascii=False,
        indent=2,
    )


def format_search_diagnostics(result: InboxSearchResult) -> tuple[str, ...]:
    shown = list(result.diagnostics[:MAX_SEARCH_DIAGNOSTICS])
    suppressed = len(result.diagnostics) - len(shown)
    if suppressed:
        shown.append(f"Additional malformed-note diagnostics suppressed: {suppressed}")
    return tuple(shown)
