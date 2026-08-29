"""FastAPI application composition for the P1.5 offline MVP."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from backend.config import Settings
from backend.providers.base import Provider
from backend.providers.gemini import GeminiProvider
from backend.providers.mock import MockProvider
from backend.routes.captures import error_response, router as captures_router
from backend.routes.operations import router as operations_router
from backend.security.payload import BodyLimitMiddleware
from backend.services.capture import CaptureService
from backend.services.extraction import URLExtractor
from backend.storage.sqlite import CaptureStore


def create_app(
    *,
    settings: Optional[Settings] = None,
    store: Optional[CaptureStore] = None,
    provider: Optional[Provider] = None,
    extractor: Optional[URLExtractor] = None,
) -> FastAPI:
    configured = settings or Settings.from_env()
    capture_store = store or CaptureStore(configured.database_path)
    if provider is None:
        provider = (
            GeminiProvider(api_key=None)
            if configured.ai_provider == "gemini"
            else MockProvider()
        )
    capture_extractor = extractor or URLExtractor()

    application = FastAPI(
        title="P1.5 Hybrid Capture API",
        version="1.0",
        openapi_url=None,
        docs_url=None,
        redoc_url=None,
    )
    application.state.settings = configured
    application.state.store = capture_store
    application.state.capture_service = CaptureService(
        store=capture_store,
        provider=provider,
        extractor=capture_extractor,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(configured.allowed_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    @application.middleware("http")
    async def security_and_size_boundary(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none'"
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @application.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        del request, exc
        return error_response(422, "INVALID_REQUEST", "Request validation failed.")

    @application.exception_handler(Exception)
    async def internal_error_handler(request: Request, exc: Exception):
        del request, exc
        return error_response(500, "INTERNAL_ERROR", "Unexpected server error.")

    @application.get("/health")
    def health():
        return {"ok": True, "status": "healthy"}

    @application.get("/", include_in_schema=False)
    def web_root():
        return RedirectResponse(url="/app/")

    application.add_middleware(
        BodyLimitMiddleware,
        max_bytes=configured.max_request_bytes,
    )
    application.include_router(captures_router)
    application.include_router(operations_router)
    web_root_path = Path(__file__).parent.parent / "web"
    application.mount(
        "/app",
        StaticFiles(directory=str(web_root_path), html=True),
        name="web",
    )
    return application


app = create_app()
