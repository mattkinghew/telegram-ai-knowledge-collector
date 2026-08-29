"""P1.5 capture API routes."""

from __future__ import annotations

from dataclasses import asdict
from typing import Optional

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from backend.models import CaptureRequest
from backend.security.auth import is_authorized
from backend.storage.sqlite import RetryLimitError


router = APIRouter(prefix="/api/v1")


def error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )


def _unauthorized(request: Request) -> Optional[JSONResponse]:
    if is_authorized(request):
        return None
    return error_response(401, "AUTH_REQUIRED", "Valid API authentication is required.")


@router.post("/capture")
def create_capture(request: Request, payload: CaptureRequest):
    denied = _unauthorized(request)
    if denied:
        return denied
    response = request.app.state.capture_service.create(payload)
    return JSONResponse(
        status_code=200 if response.ok else (202 if response.status == "pending" else 500),
        content=response.model_dump(mode="json"),
    )


@router.get("/captures/{capture_id}")
def get_capture(request: Request, capture_id: str):
    denied = _unauthorized(request)
    if denied:
        return denied
    try:
        record = request.app.state.store.get(capture_id)
    except KeyError:
        return error_response(404, "NOT_FOUND", "Capture was not found.")
    return asdict(record)


@router.get("/captures")
def list_captures(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    capture_type: Optional[str] = None,
    source_type: Optional[str] = None,
    requested_processing: Optional[str] = None,
    project: Optional[str] = None,
    query: Optional[str] = Query(default=None, min_length=1, max_length=200),
    created_from: Optional[str] = None,
    created_to: Optional[str] = None,
):
    denied = _unauthorized(request)
    if denied:
        return denied
    try:
        result = request.app.state.store.list(
            page=page,
            page_size=page_size,
            status=status,
            capture_type=capture_type,
            source_type=source_type,
            requested_processing=requested_processing,
            project=project,
            query=query,
            created_from=created_from,
            created_to=created_to,
        )
    except ValueError as exc:
        return error_response(422, "INVALID_REQUEST", str(exc))
    data = []
    for record in result.items:
        item = asdict(record)
        item.pop("raw_content")
        item.pop("markdown")
        item.pop("result")
        data.append(item)
    return {
        "data": data,
        "pagination": {
            "page": result.page,
            "page_size": result.page_size,
            "total_items": result.total_items,
            "total_pages": (
                (result.total_items + result.page_size - 1) // result.page_size
            ),
        },
    }


@router.post("/captures/{capture_id}/retry")
def retry_capture(request: Request, capture_id: str):
    denied = _unauthorized(request)
    if denied:
        return denied
    try:
        response = request.app.state.capture_service.retry(capture_id)
    except KeyError:
        return error_response(404, "NOT_FOUND", "Capture was not found.")
    except RetryLimitError:
        return error_response(409, "RETRY_LIMIT", "Manual retry limit was reached.")
    except ValueError as exc:
        return error_response(409, "INVALID_STATE", str(exc))
    return JSONResponse(
        status_code=200 if response.ok else (202 if response.status == "pending" else 500),
        content=response.model_dump(mode="json"),
    )
