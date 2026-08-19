#!/usr/bin/env python3
"""Render a deterministic Markdown project dashboard without Vault access."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence


PROJECT_FIELDS = frozenset({"name", "status", "latest_update", "next_action", "blocker", "next_review"})


class DashboardContractError(ValueError):
    """Raised when project dashboard input is invalid."""


def _value(item: Mapping[str, Any], name: str, maximum: int, *, required: bool = False) -> str:
    value = item.get(name)
    if not isinstance(value, str) or len(value) > maximum or (required and not value.strip()):
        raise DashboardContractError(f"invalid {name}")
    if "\n" in value:
        raise DashboardContractError(f"{name} must be a single line")
    return value


def render_project_dashboard(payload: Mapping[str, Any]) -> str:
    if not isinstance(payload, Mapping) or set(payload) != {"projects"}:
        raise DashboardContractError("invalid dashboard fields")
    projects = payload["projects"]
    if not isinstance(projects, list) or not 1 <= len(projects) <= 20:
        raise DashboardContractError("projects must contain 1-20 items")
    lines = ["# Project Dashboard", "", "## Active"]
    names = set()
    for item in projects:
        if not isinstance(item, Mapping) or set(item) != PROJECT_FIELDS:
            raise DashboardContractError("invalid project fields")
        name = _value(item, "name", 200, required=True)
        if name in names:
            raise DashboardContractError("project names must be unique")
        names.add(name)
        next_review = _value(item, "next_review", 10)
        if next_review:
            try:
                next_review = date.fromisoformat(next_review).isoformat()
            except ValueError as exc:
                raise DashboardContractError("next_review must be YYYY-MM-DD") from exc
        lines.extend(
            [
                "",
                f"### {name}",
                f"Status: {_value(item, 'status', 80)}",
                f"Latest update: {_value(item, 'latest_update', 500)}",
                f"Next action: {_value(item, 'next_action', 500)}",
                f"Blocker: {_value(item, 'blocker', 500)}",
                f"Next review: {next_review}",
            ]
        )
    return "\n".join(lines) + "\n"


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Fictional project-status JSON")
    args = parser.parse_args(argv)
    print(render_project_dashboard(json.loads(args.input.read_text(encoding="utf-8"))), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
