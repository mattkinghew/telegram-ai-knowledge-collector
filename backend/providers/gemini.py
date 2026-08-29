"""Disabled-by-default Gemini boundary for later live configuration."""

from __future__ import annotations

from typing import Optional

from backend.models import CaptureRequest
from backend.providers.base import ProviderFailure


class GeminiProvider:
    """Fail safely offline; P1.5 never performs a live Gemini call by default."""

    def __init__(self, api_key: Optional[str]) -> None:
        self._configured = bool(api_key and api_key.strip())

    def process(self, request: CaptureRequest) -> ProviderFailure:
        del request
        if not self._configured:
            message = "AI temporarily unavailable — capture was saved."
        else:
            message = "Live Gemini processing is disabled in offline P1.5 — capture was saved."
        return ProviderFailure(error_code="AI_UNAVAILABLE", message=message)
