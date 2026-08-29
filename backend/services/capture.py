"""Capture orchestration with lossless failure behavior."""

from __future__ import annotations

import logging
import time
from typing import Optional, Tuple

from backend.models import CaptureRequest, CaptureResponse, ProviderResult
from backend.providers.base import Provider, ProviderFailure
from backend.services.extraction import ExtractedArticle, URLExtractionError, URLExtractor
from backend.services.markdown import build_capture_markdown
from backend.storage.sqlite import CaptureRecord, CaptureStore, RetryLimitError


LOGGER = logging.getLogger("backend.capture")
FETCHABLE_SOURCE_TYPES = frozenset({"article_url", "social_post"})


class CaptureService:
    def __init__(
        self,
        *,
        store: CaptureStore,
        provider: Provider,
        extractor: URLExtractor,
    ) -> None:
        self.store = store
        self.provider = provider
        self.extractor = extractor

    def create(self, request: CaptureRequest) -> CaptureResponse:
        record = self.store.create(request)
        return self._process(record, request)

    def retry(self, capture_id: str) -> CaptureResponse:
        current = self.store.get(capture_id)
        if current.status == "processed":
            raise ValueError("processed captures do not require retry")
        record = self.store.begin_retry(capture_id)
        request = self._request_from_record(record)
        return self._process(record, request, already_processing=True)

    def _process(
        self,
        record: CaptureRecord,
        request: CaptureRequest,
        *,
        already_processing: bool = False,
    ) -> CaptureResponse:
        started = time.monotonic()
        if not already_processing:
            self.store.mark_processing(record.capture_id)
        try:
            if request.requested_processing == "raw_save":
                markdown = build_capture_markdown(request, None)
                self.store.mark_processed(record.capture_id, None, markdown)
                response = self._success(record.capture_id, markdown, None, None)
                self._log(record.capture_id, request, "processed", None, started)
                return response

            extracted: Optional[ExtractedArticle] = None
            provider_request = request
            if not request.raw_content.strip():
                if request.source_type in FETCHABLE_SOURCE_TYPES and request.source:
                    extracted = self.extractor.extract(request.source)
                    provider_request = request.model_copy(
                        update={"raw_content": extracted.text}
                    )
                else:
                    return self._pending(
                        record.capture_id,
                        request,
                        "URL_FETCH_FAILED",
                        "Source content is unavailable — reference was saved for later review.",
                        started,
                    )

            outcome = self.provider.process(provider_request)
            if isinstance(outcome, ProviderFailure):
                return self._pending(
                    record.capture_id,
                    request,
                    outcome.error_code,
                    outcome.message,
                    started,
                )
            result = ProviderResult.model_validate(outcome.model_dump())
            markdown = build_capture_markdown(
                request,
                result,
                extracted_content=extracted.text if extracted else None,
            )
            self.store.mark_processed(record.capture_id, result, markdown)
            response = self._success(record.capture_id, markdown, result, extracted)
            self._log(record.capture_id, request, "processed", None, started)
            return response
        except URLExtractionError as exc:
            return self._pending(
                record.capture_id,
                request,
                exc.error_code,
                str(exc),
                started,
            )
        except RetryLimitError:
            raise
        except Exception:
            message = "Processing failed — capture was saved for manual review."
            self.store.mark_failure(
                record.capture_id,
                status="failed",
                error_code="INTERNAL_ERROR",
                message=message,
            )
            self._log(record.capture_id, request, "failed", "INTERNAL_ERROR", started)
            return CaptureResponse(
                ok=False,
                capture_id=record.capture_id,
                status="failed",
                result=None,
                error_code="INTERNAL_ERROR",
                message=message,
            )

    def _pending(
        self,
        capture_id: str,
        request: CaptureRequest,
        error_code: str,
        message: str,
        started: float,
    ) -> CaptureResponse:
        self.store.mark_failure(
            capture_id,
            status="pending",
            error_code=error_code,
            message=message,
        )
        self._log(capture_id, request, "pending", error_code, started)
        return CaptureResponse(
            ok=False,
            capture_id=capture_id,
            status="pending",
            result=None,
            error_code=error_code,
            message=message,
        )

    @staticmethod
    def _success(
        capture_id: str,
        markdown: str,
        result: Optional[ProviderResult],
        extracted: Optional[ExtractedArticle],
    ) -> CaptureResponse:
        payload = {
            "markdown": markdown,
            "provider_result": result.model_dump() if result else None,
            "extracted": (
                {
                    "final_url": extracted.final_url,
                    "content_type": extracted.content_type,
                }
                if extracted
                else None
            ),
        }
        return CaptureResponse(
            ok=True,
            capture_id=capture_id,
            status="processed",
            result=payload,
            error_code=None,
            message=None,
        )

    @staticmethod
    def _request_from_record(record: CaptureRecord) -> CaptureRequest:
        return CaptureRequest(
            schema_version=record.schema_version,
            capture_type=record.capture_type,
            source_type=record.source_type,
            source=record.source,
            raw_content=record.raw_content,
            requested_processing=record.requested_processing,
            allowed_projects=record.allowed_projects,
        )

    @staticmethod
    def _log(
        capture_id: str,
        request: CaptureRequest,
        status: str,
        error_code: Optional[str],
        started: float,
    ) -> None:
        duration_ms = int((time.monotonic() - started) * 1000)
        LOGGER.info(
            "capture_id=%s status=%s error=%s duration_ms=%s processing=%s",
            capture_id,
            status,
            error_code or "none",
            duration_ms,
            request.requested_processing,
        )
