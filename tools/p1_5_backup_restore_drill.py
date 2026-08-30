#!/usr/bin/env python3
"""Create and verify one sanitized P1.5 SQLite backup/restore drill."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Dict, Iterable, List


BLOCKED_PARTS = frozenset(
    {
        "20_areas",
        "25_self_management",
        "private",
        "credentials",
        ".env",
        ".obsidian",
    }
)
REQUIRED_STATUS_COUNTS = {"processed": 3, "pending": 1, "failed": 1}


class DrillError(ValueError):
    """Raised before an unsafe or unverifiable drill can continue."""


def _guard_path(path: Path, *, must_exist: bool) -> Path:
    expanded = path.expanduser().absolute()
    parts = expanded.parts
    if expanded.anchor == "/" and len(parts) > 1 and parts[1] == "private":
        parts = parts[2:]
    if any(part.casefold() in BLOCKED_PARTS for part in parts):
        raise DrillError("backup/restore path is blocked by protected-path policy")
    for candidate in (expanded, *expanded.parents):
        if candidate.is_symlink():
            raise DrillError("backup/restore paths must not contain symlinks")
    if must_exist:
        if not expanded.is_file():
            raise DrillError("source database must be an existing regular file")
    else:
        if expanded.exists():
            raise DrillError("backup and restore targets must not already exist")
        if not expanded.parent.is_dir():
            raise DrillError("backup and restore parent directories must exist")
    return expanded


def _integrity(path: Path) -> str:
    connection = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    try:
        rows = connection.execute("PRAGMA integrity_check").fetchall()
    finally:
        connection.close()
    if rows != [("ok",)]:
        raise DrillError("SQLite integrity check failed")
    return "ok"


def _online_backup(source: Path, destination: Path) -> None:
    source_connection = sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)
    destination_connection = sqlite3.connect(str(destination))
    try:
        with destination_connection:
            source_connection.backup(destination_connection)
    finally:
        destination_connection.close()
        source_connection.close()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _records(path: Path, capture_ids: Iterable[str]) -> Dict[str, dict]:
    connection = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    records = {}
    try:
        for capture_id in capture_ids:
            row = connection.execute(
                "SELECT * FROM captures WHERE capture_id = ?",
                (capture_id,),
            ).fetchone()
            if row is None:
                raise DrillError("an expected capture ID is missing")
            records[capture_id] = dict(row)
    finally:
        connection.close()
    return records


def run_drill(
    *,
    source: Path,
    backup: Path,
    restore: Path,
    expected_capture_ids: Iterable[str],
) -> dict:
    """Back up, restore, and compare five explicitly selected fictional rows."""

    source_path = _guard_path(Path(source), must_exist=True)
    backup_path = _guard_path(Path(backup), must_exist=False)
    restore_path = _guard_path(Path(restore), must_exist=False)
    if len({source_path, backup_path, restore_path}) != 3:
        raise DrillError("source, backup, and restore paths must be distinct")

    capture_ids: List[str] = list(expected_capture_ids)
    if len(capture_ids) != 5 or len(set(capture_ids)) != 5:
        raise DrillError("exactly five unique fictional capture IDs are required")
    source_records = _records(source_path, capture_ids)
    status_counts = {
        status: sum(record["status"] == status for record in source_records.values())
        for status in REQUIRED_STATUS_COUNTS
    }
    if status_counts != REQUIRED_STATUS_COUNTS:
        raise DrillError("selected records must contain 3 processed, 1 pending, and 1 failed")

    started = time.monotonic()
    _online_backup(source_path, backup_path)
    _integrity(backup_path)
    _online_backup(backup_path, restore_path)
    integrity = _integrity(restore_path)
    restored_records = _records(restore_path, capture_ids)
    elapsed_ms = int((time.monotonic() - started) * 1000)

    if restored_records != source_records:
        raise DrillError("restored capture fields do not match the source snapshot")

    return {
        "ok": True,
        "capture_count": len(capture_ids),
        "status_counts": status_counts,
        "integrity": integrity,
        "backup_bytes": backup_path.stat().st_size,
        "backup_sha256": _sha256(backup_path),
        "restore_duration_ms": elapsed_ms,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify one fictional P1.5 SQLite backup and clean restore."
    )
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--backup", required=True, type=Path)
    parser.add_argument("--restore", required=True, type=Path)
    parser.add_argument(
        "--expected-capture-id",
        action="append",
        required=True,
        help="Repeat exactly five times; IDs are verified but never printed.",
    )
    args = parser.parse_args()
    evidence = run_drill(
        source=args.source,
        backup=args.backup,
        restore=args.restore,
        expected_capture_ids=args.expected_capture_id,
    )
    print(json.dumps(evidence, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
