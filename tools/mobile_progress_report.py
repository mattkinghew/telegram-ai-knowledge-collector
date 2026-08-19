#!/usr/bin/env python3
"""Deterministic travel progress report builder with no Vault or network access."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence
from urllib.parse import urlparse


RECORD_TYPES = frozenset({"progress_update", "task", "decision", "due_event", "evidence"})
RECORD_FIELDS = frozenset({"type", "title", "status", "detail", "due_date", "link"})


class ProgressReportContractError(ValueError):
    """Raised when explicitly selected records violate the report contract."""


def _text(
    value: Any,
    name: str,
    maximum: int,
    *,
    required: bool = False,
    single_line: bool = False,
) -> str:
    if not isinstance(value, str):
        raise ProgressReportContractError(f"{name} must be a string")
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    if len(value) > maximum or (required and not value.strip()):
        raise ProgressReportContractError(f"invalid {name}")
    if single_line and "\n" in value:
        raise ProgressReportContractError(f"{name} must be a single line")
    return value


def _date(value: str) -> str:
    if not value:
        return ""
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise ProgressReportContractError("due_date must be YYYY-MM-DD") from exc


def _link(value: str) -> str:
    if not value:
        return ""
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password:
        raise ProgressReportContractError("link must be a credential-free HTTP or HTTPS URL")
    return value


def validate_progress_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping) or set(payload) != {"reporting_period", "project", "selected_records"}:
        raise ProgressReportContractError("invalid report payload fields")
    period = _text(payload["reporting_period"], "reporting_period", 200, required=True, single_line=True)
    project = _text(payload["project"], "project", 200, required=True, single_line=True)
    records_value = payload["selected_records"]
    if not isinstance(records_value, list) or not 1 <= len(records_value) <= 100:
        raise ProgressReportContractError("selected_records must contain 1-100 records")
    records = []
    for item in records_value:
        if not isinstance(item, Mapping) or set(item) != RECORD_FIELDS:
            raise ProgressReportContractError("invalid selected record fields")
        record_type = _text(item["type"], "type", 40, required=True, single_line=True)
        if record_type not in RECORD_TYPES:
            raise ProgressReportContractError("unsupported selected record type")
        records.append(
            {
                "type": record_type,
                "title": _text(item["title"], "title", 300, required=True, single_line=True),
                "status": _text(item["status"], "status", 80, single_line=True),
                "detail": _text(item["detail"], "detail", 2_000),
                "due_date": _date(_text(item["due_date"], "due_date", 10, single_line=True)),
                "link": _link(_text(item["link"], "link", 2_048, single_line=True)),
            }
        )
    return {"reporting_period": period, "project": project, "selected_records": records}


def _line(record: Mapping[str, str]) -> str:
    details = [record["status"], record["detail"]]
    if record["due_date"]:
        details.append(f"due {record['due_date']}")
    if record["link"]:
        details.append(record["link"])
    suffix = " — ".join(value for value in details if value)
    return f"- {record['title']}" + (f" — {suffix}" if suffix else "")


def render_progress_report(payload: Mapping[str, Any]) -> str:
    data = validate_progress_payload(payload)
    records = data["selected_records"]

    def section(types: set[str], statuses: Optional[set[str]] = None) -> str:
        selected = [
            record for record in records
            if record["type"] in types and (statuses is None or record["status"] in statuses)
        ]
        return "\n".join(_line(record) for record in selected) or "- None selected."

    completed = section({"progress_update", "task"}, {"completed", "done"})
    current = section({"progress_update", "task"}, {"in_progress", "active"})
    milestones = section({"task", "due_event"}, {"next", "pending"})
    decisions = section({"decision"})
    evidence = section({"evidence"})
    follow_ups = section({"task"}, {"next", "blocked", "pending"})
    risks = section({"progress_update", "task"}, {"blocked"})
    return (
        "# Progress Report\n\n"
        f"## Reporting Period\n\n{data['reporting_period']}\n\n"
        f"## Executive Summary\n\nProject: {data['project']}\n"
        "This draft contains only explicitly selected structured records.\n\n"
        f"## Completed\n\n{completed}\n\n"
        f"## Current Progress\n\n{current}\n\n"
        f"## Next Milestones\n\n{milestones}\n\n"
        f"## Risks / Blockers\n\n{risks}\n\n"
        f"## Decisions Required\n\n{decisions}\n\n"
        f"## Evidence\n\n{evidence}\n\n"
        f"## Outstanding Follow-ups\n\n{follow_ups}\n"
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Fictional selected-record JSON")
    args = parser.parse_args(argv)
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    print(render_progress_report(payload), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
