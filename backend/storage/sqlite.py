"""Parameterized SQLite store for bounded P1.5 processing state."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional

from backend.models import CaptureRequest, ProviderResult, new_capture_id


class RetryLimitError(ValueError):
    """Raised when the bounded manual retry allowance is exhausted."""


@dataclass(frozen=True)
class CaptureRecord:
    capture_id: str
    schema_version: str
    capture_type: str
    source_type: str
    source: Optional[str]
    raw_content: str
    requested_processing: str
    allowed_projects: List[str]
    status: str
    result: Optional[dict[str, Any]]
    markdown: Optional[str]
    error_code: Optional[str]
    error_message: Optional[str]
    retry_count: int
    reviewed: bool
    processing_dismissed: bool
    assigned_project: Optional[str]
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class CapturePage:
    items: List[CaptureRecord]
    page: int
    page_size: int
    total_items: int


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class CaptureStore:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.path))
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS captures (
                    capture_id TEXT PRIMARY KEY,
                    schema_version TEXT NOT NULL,
                    capture_type TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    source TEXT,
                    raw_content TEXT NOT NULL,
                    requested_processing TEXT NOT NULL,
                    allowed_projects_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    result_json TEXT,
                    markdown TEXT,
                    error_code TEXT,
                    error_message TEXT,
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    reviewed INTEGER NOT NULL DEFAULT 0,
                    processing_dismissed INTEGER NOT NULL DEFAULT 0,
                    assigned_project TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS captures_status_created ON captures(status, created_at DESC)"
            )

    def create(self, request: CaptureRequest) -> CaptureRecord:
        capture_id = new_capture_id()
        timestamp = _now()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO captures (
                    capture_id, schema_version, capture_type, source_type, source,
                    raw_content, requested_processing, allowed_projects_json,
                    status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)
                """,
                (
                    capture_id,
                    request.schema_version,
                    request.capture_type,
                    request.source_type,
                    request.source,
                    request.raw_content,
                    request.requested_processing,
                    json.dumps(request.allowed_projects, ensure_ascii=False),
                    timestamp,
                    timestamp,
                ),
            )
        return self.get(capture_id)

    def get(self, capture_id: str) -> CaptureRecord:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM captures WHERE capture_id = ?", (capture_id,)
            ).fetchone()
        if row is None:
            raise KeyError(capture_id)
        return self._record(row)

    def mark_processing(self, capture_id: str) -> CaptureRecord:
        self._update(
            capture_id,
            "status = 'processing', error_code = NULL, error_message = NULL, updated_at = ?",
            (_now(),),
        )
        return self.get(capture_id)

    def mark_processed(
        self,
        capture_id: str,
        result: Optional[ProviderResult],
        markdown: str,
    ) -> CaptureRecord:
        result_json = (
            json.dumps(result.model_dump(), ensure_ascii=False) if result else None
        )
        self._update(
            capture_id,
            "status = 'processed', result_json = ?, markdown = ?, error_code = NULL, error_message = NULL, updated_at = ?",
            (result_json, markdown, _now()),
        )
        return self.get(capture_id)

    def mark_failure(
        self,
        capture_id: str,
        *,
        status: str,
        error_code: str,
        message: str,
    ) -> CaptureRecord:
        if status not in {"pending", "failed"}:
            raise ValueError("failure status must be pending or failed")
        self._update(
            capture_id,
            "status = ?, result_json = NULL, markdown = NULL, error_code = ?, error_message = ?, updated_at = ?",
            (status, error_code, message[:300], _now()),
        )
        return self.get(capture_id)

    def begin_retry(self, capture_id: str) -> CaptureRecord:
        record = self.get(capture_id)
        if record.retry_count >= 2:
            raise RetryLimitError("manual retry limit reached")
        self._update(
            capture_id,
            "status = 'processing', retry_count = retry_count + 1, error_code = NULL, error_message = NULL, processing_dismissed = 0, updated_at = ?",
            (_now(),),
        )
        return self.get(capture_id)

    def update_review(
        self,
        capture_id: str,
        *,
        reviewed: bool,
        assigned_project: Optional[str],
    ) -> CaptureRecord:
        record = self.get(capture_id)
        if assigned_project is not None and assigned_project not in record.allowed_projects:
            raise ValueError("assigned_project is outside the capture allowlist")
        self._update(
            capture_id,
            "reviewed = ?, assigned_project = ?, updated_at = ?",
            (int(reviewed), assigned_project, _now()),
        )
        return self.get(capture_id)

    def dismiss_processing(self, capture_id: str) -> CaptureRecord:
        self._update(
            capture_id,
            "processing_dismissed = 1, updated_at = ?",
            (_now(),),
        )
        return self.get(capture_id)

    def list(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        capture_type: Optional[str] = None,
        source_type: Optional[str] = None,
        requested_processing: Optional[str] = None,
    ) -> CapturePage:
        if page < 1 or not 1 <= page_size <= 100:
            raise ValueError("pagination is outside the supported range")
        clauses = []
        values: List[Any] = []
        for column, value in (
            ("status", status),
            ("capture_type", capture_type),
            ("source_type", source_type),
            ("requested_processing", requested_processing),
        ):
            if value is not None:
                clauses.append(column + " = ?")
                values.append(value)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        with self._connect() as connection:
            total = connection.execute(
                "SELECT COUNT(*) FROM captures" + where, values
            ).fetchone()[0]
            rows = connection.execute(
                "SELECT * FROM captures"
                + where
                + " ORDER BY created_at DESC, capture_id ASC LIMIT ? OFFSET ?",
                values + [page_size, (page - 1) * page_size],
            ).fetchall()
        return CapturePage(
            items=[self._record(row) for row in rows],
            page=page,
            page_size=page_size,
            total_items=total,
        )

    def _update(self, capture_id: str, assignments: str, values: tuple[Any, ...]) -> None:
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE captures SET " + assignments + " WHERE capture_id = ?",
                values + (capture_id,),
            )
        if cursor.rowcount != 1:
            raise KeyError(capture_id)

    @staticmethod
    def _record(row: sqlite3.Row) -> CaptureRecord:
        return CaptureRecord(
            capture_id=row["capture_id"],
            schema_version=row["schema_version"],
            capture_type=row["capture_type"],
            source_type=row["source_type"],
            source=row["source"],
            raw_content=row["raw_content"],
            requested_processing=row["requested_processing"],
            allowed_projects=json.loads(row["allowed_projects_json"]),
            status=row["status"],
            result=json.loads(row["result_json"]) if row["result_json"] else None,
            markdown=row["markdown"],
            error_code=row["error_code"],
            error_message=row["error_message"],
            retry_count=row["retry_count"],
            reviewed=bool(row["reviewed"]),
            processing_dismissed=bool(row["processing_dismissed"]),
            assigned_project=row["assigned_project"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
