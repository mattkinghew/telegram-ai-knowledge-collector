"""Provider interface and safe failure value."""

from __future__ import annotations

from typing import Protocol, Union

from pydantic import BaseModel, ConfigDict, Field

from backend.models import CaptureRequest, ErrorCode, ProviderResult


class ProviderFailure(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    error_code: ErrorCode
    message: str = Field(min_length=1, max_length=300)


ProviderOutcome = Union[ProviderResult, ProviderFailure]


class Provider(Protocol):
    def process(self, request: CaptureRequest) -> ProviderOutcome:
        """Process one already-validated capture without mutating it."""
