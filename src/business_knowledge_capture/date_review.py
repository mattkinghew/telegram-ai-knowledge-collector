from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable, Optional

from .core import (
    CATEGORIES,
    MAX_INBOX_CANDIDATES,
    _read_inbox_prefix,
    list_safe_inbox_candidates,
    parse_iso_date,
)

DEFAULT_DUE_LIMIT = 50
MAX_DUE_RESULTS = 200
MAX_DATE_DIAGNOSTICS = 20
DATE_EVENT_TYPES = ("reminder", "deadline", "resource_expiry")
DATE_STATUSES = ("overdue", "due_today", "due_soon", "upcoming")
DUE_SORTS = (
    "date-asc",
    "date-desc",
    "days-until-asc",
    "title-asc",
    "title-desc",
)
EVENT_LABELS = {
    "reminder": "Reminder",
    "deadline": "Deadline",
    "resource_expiry": "Resource Expiry",
}
EVENT_METADATA = (
    ("deadline", "Deadline"),
    ("resource_expiry", "Resource Expiry"),
    ("reminder", "Reminder Date"),
)


@dataclass(frozen=True)
class DateReviewEvent:
    event_type: str
    event_date: date
    days_until: int
    status: str
    title: str
    suggested_category: str
    action_required: str
    reminder_note: str
    related_project: str
    related_area: str
    source_type: str
    relative_path: str

    @property
    def selection_key(self) -> str:
        return (
            f"{self.event_type}::{self.event_date.isoformat()}::"
            f"{self.relative_path}"
        )


@dataclass(frozen=True)
class DateReviewQuery:
    as_of: date
    window_days: int = 14
    event_types: tuple[str, ...] = ()
    statuses: tuple[str, ...] = ()
    categories: tuple[str, ...] = ()
    related_project: str = ""
    related_area: str = ""
    include_upcoming: bool = False
    sort: str = "date-asc"
    limit: int = DEFAULT_DUE_LIMIT


@dataclass(frozen=True)
class DateReviewResult:
    query: DateReviewQuery
    total_events: int
    events: tuple[DateReviewEvent, ...]
    diagnostics: tuple[str, ...] = ()


def validate_date_review_query(query: DateReviewQuery) -> None:
    if not 1 <= query.window_days <= 365:
        raise ValueError("Due-soon window must be between 1 and 365 days.")
    if not 1 <= query.limit <= MAX_DUE_RESULTS:
        raise ValueError(f"Due result limit must be between 1 and {MAX_DUE_RESULTS}.")
    if query.sort not in DUE_SORTS:
        raise ValueError(f"Due sort must be one of: {', '.join(DUE_SORTS)}.")
    invalid_types = [value for value in query.event_types if value not in DATE_EVENT_TYPES]
    if invalid_types:
        raise ValueError(f"Event type must be one of: {', '.join(DATE_EVENT_TYPES)}.")
    invalid_statuses = [value for value in query.statuses if value not in DATE_STATUSES]
    if invalid_statuses:
        raise ValueError(f"Date status must be one of: {', '.join(DATE_STATUSES)}.")
    invalid_categories = [value for value in query.categories if value not in CATEGORIES]
    if invalid_categories:
        raise ValueError(f"Category must be one of: {', '.join(CATEGORIES)}.")


def calculate_date_status(
    event_date: date,
    as_of: date,
    window_days: int,
) -> tuple[int, str]:
    days_until = (event_date - as_of).days
    if days_until < 0:
        status = "overdue"
    elif days_until == 0:
        status = "due_today"
    elif days_until <= window_days:
        status = "due_soon"
    else:
        status = "upcoming"
    return days_until, status


def _contains(value: str, query: str) -> bool:
    return query.casefold() in value.casefold()


def _matches(event: DateReviewEvent, query: DateReviewQuery) -> bool:
    if query.event_types and event.event_type not in query.event_types:
        return False
    if query.statuses and event.status not in query.statuses:
        return False
    if query.categories and event.suggested_category not in query.categories:
        return False
    if query.related_project and not _contains(event.related_project, query.related_project):
        return False
    if query.related_area and not _contains(event.related_area, query.related_area):
        return False
    if (
        event.status == "upcoming"
        and not query.include_upcoming
        and "upcoming" not in query.statuses
    ):
        return False
    return True


def sort_date_events(
    events: Iterable[DateReviewEvent],
    sort_mode: str,
) -> list[DateReviewEvent]:
    event_order = {name: index for index, name in enumerate(DATE_EVENT_TYPES)}
    values = sorted(events, key=lambda event: event.relative_path)
    values.sort(key=lambda event: event_order[event.event_type])
    if sort_mode == "date-asc":
        values.sort(key=lambda event: event.event_date)
    elif sort_mode == "date-desc":
        values.sort(key=lambda event: event.event_date, reverse=True)
    elif sort_mode == "days-until-asc":
        values.sort(key=lambda event: event.days_until)
    elif sort_mode == "title-asc":
        values.sort(key=lambda event: event.title.casefold())
    elif sort_mode == "title-desc":
        values.sort(key=lambda event: event.title.casefold(), reverse=True)
    return values


def review_due_dates(
    *,
    vault: Path,
    query: DateReviewQuery,
    max_candidates: int = MAX_INBOX_CANDIDATES,
) -> DateReviewResult:
    validate_date_review_query(query)
    candidates, candidate_diagnostics = list_safe_inbox_candidates(
        vault=vault,
        max_candidates=max_candidates,
    )
    diagnostics = list(candidate_diagnostics)
    events: list[DateReviewEvent] = []
    for candidate in candidates:
        relative = candidate.relative_to(vault).as_posix()
        try:
            title, metadata = _read_inbox_prefix(candidate, require_metadata=False)
        except OSError:
            diagnostics.append(f"{relative}: candidate could not be read.")
            continue
        except ValueError as exc:
            diagnostics.append(f"{relative}: {exc}")
            continue
        if not title:
            title = candidate.stem
            diagnostics.append(f"{relative}: missing H1; filename used as title.")

        parsed_dates: dict[str, date] = {}
        for event_type, field in EVENT_METADATA:
            raw_value = metadata.get(field, "")
            if not raw_value:
                continue
            try:
                parsed_dates[event_type] = parse_iso_date(raw_value, field)
            except ValueError:
                diagnostics.append(
                    f"{relative}: invalid {field} metadata ignored."
                )

        reminder = parsed_dates.get("reminder")
        deadline = parsed_dates.get("deadline")
        expiry = parsed_dates.get("resource_expiry")
        if reminder and deadline and reminder > deadline:
            diagnostics.append(f"{relative}: Reminder Date is later than Deadline.")
        if reminder and expiry and reminder > expiry:
            diagnostics.append(
                f"{relative}: Reminder Date is later than Resource Expiry."
            )

        for event_type, event_date in parsed_dates.items():
            days_until, status = calculate_date_status(
                event_date, query.as_of, query.window_days
            )
            event = DateReviewEvent(
                event_type=event_type,
                event_date=event_date,
                days_until=days_until,
                status=status,
                title=title,
                suggested_category=metadata.get("Suggested Category", ""),
                action_required=metadata.get("Action Required", ""),
                reminder_note=metadata.get("Reminder Note", ""),
                related_project=metadata.get("Related Project", ""),
                related_area=metadata.get("Related Area", ""),
                source_type=metadata.get("Source Type", ""),
                relative_path=relative,
            )
            if _matches(event, query):
                events.append(event)
    ordered = sort_date_events(events, query.sort)
    return DateReviewResult(
        query=query,
        total_events=len(ordered),
        events=tuple(ordered[: query.limit]),
        diagnostics=tuple(diagnostics),
    )


def format_due_text(result: DateReviewResult) -> str:
    lines = [
        f"Found {result.total_events} date event(s).",
        f"As of: {result.query.as_of.isoformat()}",
        f"Due-soon window: {result.query.window_days} days",
    ]
    for index, event in enumerate(result.events, 1):
        day_label = (
            f"Days Overdue: {abs(event.days_until)}"
            if event.days_until < 0
            else f"Days Until: {event.days_until}"
        )
        lines.extend(
            (
                "",
                f"{index}. {event.title}",
                f"   Event: {EVENT_LABELS[event.event_type]}",
                f"   Date: {event.event_date.isoformat()}",
                f"   {day_label}",
                f"   Status: {event.status}",
                f"   Action: {event.action_required}",
                f"   Reminder Note: {event.reminder_note}",
                f"   Category: {event.suggested_category}",
                f"   Project: {event.related_project}",
                f"   Area: {event.related_area}",
                f"   Source: {event.source_type}",
                f"   Path: {event.relative_path}",
                f"   Selection Key: {event.selection_key}",
            )
        )
    return "\n".join(lines)


def format_due_json(result: DateReviewResult) -> str:
    query = result.query
    records = [
        {
            "title": event.title,
            "event_type": event.event_type,
            "event_date": event.event_date.isoformat(),
            "days_until": event.days_until,
            "status": event.status,
            "suggested_category": event.suggested_category,
            "action_required": event.action_required,
            "reminder_note": event.reminder_note,
            "related_project": event.related_project,
            "related_area": event.related_area,
            "source_type": event.source_type,
            "relative_path": event.relative_path,
            "selection_key": event.selection_key,
        }
        for event in result.events
    ]
    return json.dumps(
        {
            "as_of": query.as_of.isoformat(),
            "window_days": query.window_days,
            "filters": {
                "event_types": list(query.event_types),
                "statuses": list(query.statuses),
                "categories": list(query.categories),
                "related_project": query.related_project,
                "related_area": query.related_area,
                "include_upcoming": query.include_upcoming,
                "sort": query.sort,
                "limit": query.limit,
            },
            "total_events": result.total_events,
            "returned": len(records),
            "results": records,
        },
        ensure_ascii=False,
        indent=2,
    )


def format_date_diagnostics(result: DateReviewResult) -> tuple[str, ...]:
    shown = list(result.diagnostics[:MAX_DATE_DIAGNOSTICS])
    suppressed = len(result.diagnostics) - len(shown)
    if suppressed:
        shown.append(
            f"Additional malformed-date diagnostics suppressed: {suppressed}"
        )
    return tuple(shown)
