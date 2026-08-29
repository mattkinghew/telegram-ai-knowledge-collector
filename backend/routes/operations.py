"""Review, dashboard, project, and report-preview operations."""

from __future__ import annotations

from dataclasses import asdict
from typing import List, Literal, Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.routes.captures import error_response
from backend.security.auth import is_authorized
from backend.services.reports import build_report_preview


router = APIRouter(prefix="/api/v1")


class ReviewUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    reviewed: Optional[bool] = None
    assigned_project: Optional[str] = Field(default=None, max_length=80)

    @model_validator(mode="after")
    def require_change(self) -> "ReviewUpdate":
        if not self.model_fields_set:
            raise ValueError("at least one review field is required")
        if self.assigned_project is not None and not self.assigned_project.strip():
            raise ValueError("assigned_project cannot be blank")
        return self


class ReportPreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    report_type: Literal["daily", "period"]
    period: str = Field(min_length=1, max_length=100)
    capture_ids: List[str] = Field(min_length=1, max_length=50)

    @model_validator(mode="after")
    def validate_selection(self) -> "ReportPreviewRequest":
        if "\n" in self.period or "\r" in self.period:
            raise ValueError("period must be one line")
        if len(set(self.capture_ids)) != len(self.capture_ids):
            raise ValueError("capture_ids must not contain duplicates")
        return self


def _unauthorized(request: Request):
    if is_authorized(request):
        return None
    return error_response(401, "AUTH_REQUIRED", "Valid API authentication is required.")


@router.patch("/captures/{capture_id}")
def update_capture(request: Request, capture_id: str, payload: ReviewUpdate):
    denied = _unauthorized(request)
    if denied:
        return denied
    try:
        current = request.app.state.store.get(capture_id)
        reviewed = payload.reviewed if "reviewed" in payload.model_fields_set else current.reviewed
        assigned = (
            payload.assigned_project
            if "assigned_project" in payload.model_fields_set
            else current.assigned_project
        )
        updated = request.app.state.store.update_review(
            capture_id,
            reviewed=reviewed,
            assigned_project=assigned,
        )
    except KeyError:
        return error_response(404, "NOT_FOUND", "Capture was not found.")
    except ValueError as exc:
        return error_response(422, "INVALID_REQUEST", str(exc))
    return asdict(updated)


@router.post("/captures/{capture_id}/dismiss")
def dismiss_capture(request: Request, capture_id: str):
    denied = _unauthorized(request)
    if denied:
        return denied
    try:
        updated = request.app.state.store.dismiss_processing(capture_id)
    except KeyError:
        return error_response(404, "NOT_FOUND", "Capture was not found.")
    return asdict(updated)


@router.get("/dashboard/today")
def today(request: Request):
    denied = _unauthorized(request)
    if denied:
        return denied
    store = request.app.state.store
    recent = store.list(page=1, page_size=5)
    pending_count = store.list(page=1, page_size=1, status="pending").total_items
    failed_count = store.list(page=1, page_size=1, status="failed").total_items
    next_actions = []
    project_progress = []
    for record in recent.items:
        if record.result:
            sections = record.result.get("sections", {})
            next_actions.extend(sections.get("next_actions", [])[:2])
        if record.assigned_project:
            project_progress.append(
                {
                    "project": record.assigned_project,
                    "latest_progress": record.title,
                    "last_updated": record.updated_at,
                }
            )
    return {
        "recent_captures": [_summary(record) for record in recent.items],
        "recent_project_progress": project_progress[:3],
        "next_actions": next_actions[:5],
        "pending_count": pending_count,
        "failed_count": failed_count,
    }


@router.get("/projects")
def projects(request: Request):
    denied = _unauthorized(request)
    if denied:
        return denied
    records = request.app.state.store.list(page=1, page_size=100).items
    latest = {}
    for record in records:
        if record.assigned_project and record.assigned_project not in latest:
            sections = record.result.get("sections", {}) if record.result else {}
            latest[record.assigned_project] = {
                "project": record.assigned_project,
                "latest_progress": record.title,
                "next_action": _first(sections.get("next_actions", [])),
                "blocker": _first(sections.get("blockers", [])),
                "last_updated": record.updated_at,
            }
    return {"data": list(latest.values()), "limit": 100}


@router.post("/reports/preview")
def report_preview(request: Request, payload: ReportPreviewRequest):
    denied = _unauthorized(request)
    if denied:
        return denied
    records = []
    try:
        for capture_id in payload.capture_ids:
            records.append(request.app.state.store.get(capture_id))
    except KeyError:
        return error_response(404, "NOT_FOUND", "A selected capture was not found.")
    markdown = build_report_preview(payload.report_type, payload.period, records)
    return {
        "report_type": payload.report_type,
        "period": payload.period,
        "selected_capture_ids": payload.capture_ids,
        "markdown": markdown,
        "sent": False,
        "published": False,
    }


def _summary(record):
    return {
        "capture_id": record.capture_id,
        "title": record.title,
        "capture_type": record.capture_type,
        "source_type": record.source_type,
        "source": record.source,
        "status": record.status,
        "created_at": record.created_at,
        "assigned_project": record.assigned_project,
        "requested_processing": record.requested_processing,
    }


def _first(items):
    return items[0] if items else None
