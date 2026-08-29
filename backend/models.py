"""Strict public and provider contracts for P1.5."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from urllib.parse import urlparse
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


CaptureType = Literal["voice", "content"]
SourceType = Literal[
    "voice_transcript",
    "article_url",
    "social_post",
    "selected_text",
    "video_url",
    "video_transcript",
    "image_reference",
    "file_reference",
    "clipboard_text",
]
ProcessingMode = Literal[
    "raw_save",
    "voice_structure",
    "summary",
    "recommendation",
    "short_article",
    "project_knowledge",
]
CaptureStatus = Literal["pending", "processing", "processed", "failed"]
ErrorCode = Literal[
    "NETWORK_UNAVAILABLE",
    "AI_UNAVAILABLE",
    "AI_TIMEOUT",
    "INVALID_AI_JSON",
    "SCHEMA_MISMATCH",
    "URL_FETCH_FAILED",
    "UNSUPPORTED_CONTENT_TYPE",
    "PAYLOAD_TOO_LARGE",
    "INVALID_REQUEST",
    "INTERNAL_ERROR",
]


URL_SOURCE_TYPES = frozenset(
    {"article_url", "social_post", "video_url", "video_transcript"}
)
TEXT_SOURCE_TYPES = frozenset(
    {"voice_transcript", "selected_text", "clipboard_text", "video_transcript"}
)
REFERENCE_SOURCE_TYPES = frozenset({"image_reference", "file_reference"})


def new_capture_id() -> str:
    """Return an opaque identifier that contains no user content."""

    return str(uuid4())


def _validate_http_url(value: str) -> str:
    parsed = urlparse(value)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.hostname is None
        or parsed.username is not None
        or parsed.password is not None
        or any(character.isspace() for character in value)
    ):
        raise ValueError("source must be an HTTP or HTTPS URL without credentials")
    return value


class CaptureRequest(BaseModel):
    """Versioned request accepted from a Shortcut or the Web App."""

    model_config = ConfigDict(extra="forbid", strict=True)

    schema_version: Literal["1"]
    capture_type: CaptureType
    source_type: SourceType
    source: Optional[str] = Field(max_length=2_048)
    raw_content: str = Field(max_length=50_000)
    requested_processing: ProcessingMode
    allowed_projects: List[str] = Field(max_length=8)

    @field_validator("raw_content")
    @classmethod
    def normalize_newlines(cls, value: str) -> str:
        return value.replace("\r\n", "\n").replace("\r", "\n")

    @field_validator("allowed_projects")
    @classmethod
    def validate_projects(cls, value: List[str]) -> List[str]:
        if len(set(value)) != len(value):
            raise ValueError("allowed_projects must not contain duplicates")
        for project in value:
            if not project.strip() or len(project) > 80 or "\n" in project or "\r" in project:
                raise ValueError("allowed project names must be 1-80 characters on one line")
        return value

    @model_validator(mode="after")
    def validate_compatibility(self) -> "CaptureRequest":
        if self.capture_type == "voice":
            if self.source_type != "voice_transcript":
                raise ValueError("voice capture requires voice_transcript")
            if self.requested_processing not in {"raw_save", "voice_structure"}:
                raise ValueError("voice capture supports raw_save or voice_structure")
        elif self.requested_processing == "voice_structure":
            raise ValueError("voice_structure requires voice capture")

        if self.source_type in URL_SOURCE_TYPES:
            if self.source is None:
                raise ValueError("URL source types require source")
            _validate_http_url(self.source)
        elif self.source_type in REFERENCE_SOURCE_TYPES:
            if (
                self.source is None
                or not self.source
                or self.source in {".", ".."}
                or "/" in self.source
                or "\\" in self.source
                or ":" in self.source
                or len(self.source) > 255
            ):
                raise ValueError("file references require a safe filename only")
        elif self.source is not None:
            raise ValueError("text source types require a null source")

        if self.source_type in TEXT_SOURCE_TYPES and not self.raw_content.strip():
            raise ValueError("this source type requires raw_content")
        return self


class ProviderResult(BaseModel):
    """Bounded, provider-independent output; model output remains untrusted."""

    model_config = ConfigDict(extra="forbid", strict=True)

    processing_mode: Literal[
        "voice_structure",
        "summary",
        "recommendation",
        "short_article",
        "project_knowledge",
    ]
    title: str = Field(min_length=1, max_length=200)
    summary: str = Field(min_length=1, max_length=600)
    points: List[str] = Field(max_length=3)
    why_it_matters: str = Field(min_length=1, max_length=600)
    sections: Dict[str, List[str]] = Field(max_length=12)

    @field_validator("title", "summary", "why_it_matters")
    @classmethod
    def reject_control_lines(cls, value: str) -> str:
        if "\x00" in value:
            raise ValueError("text contains a null byte")
        if "\n" in value or "\r" in value:
            raise ValueError("provider scalar text must remain on one line")
        return value

    @field_validator("points")
    @classmethod
    def validate_points(cls, value: List[str]) -> List[str]:
        for point in value:
            if not point.strip() or len(point) > 500 or "\n" in point or "\r" in point:
                raise ValueError("points must be non-empty bounded lines")
        return value

    @field_validator("sections")
    @classmethod
    def validate_sections(cls, value: Dict[str, List[str]]) -> Dict[str, List[str]]:
        for name, items in value.items():
            if not name or len(name) > 50 or len(items) > 10:
                raise ValueError("provider sections are bounded")
            for item in items:
                if (
                    not item.strip()
                    or len(item) > 1_000
                    or "\x00" in item
                    or "\n" in item
                    or "\r" in item
                ):
                    raise ValueError("provider section items are bounded text")
        return value

    @model_validator(mode="after")
    def validate_mode_sections(self) -> "ProviderResult":
        expected = {
            "voice_structure": {
                "completed",
                "in_progress",
                "next_actions",
                "blockers",
                "decisions",
                "knowledge",
                "content_ideas",
                "facts_to_verify",
                "related_projects",
            },
            "summary": set(),
            "recommendation": {
                "situation",
                "insight",
                "recommended_action",
                "reason",
                "verification_risk",
            },
            "short_article": {"draft"},
            "project_knowledge": {
                "reusable_knowledge",
                "project_use",
                "facts_to_verify",
            },
        }[self.processing_mode]
        if set(self.sections) != expected:
            raise ValueError("provider sections do not match processing_mode")
        return self


class CaptureResponse(BaseModel):
    """Stable response envelope shared by create, status, list, and retry."""

    model_config = ConfigDict(extra="forbid", strict=True)

    ok: bool
    capture_id: str
    status: CaptureStatus
    result: Optional[Dict[str, Any]]
    error_code: Optional[ErrorCode]
    message: Optional[str] = Field(max_length=300)

    @field_validator("capture_id")
    @classmethod
    def validate_capture_id(cls, value: str) -> str:
        try:
            from uuid import UUID

            parsed = UUID(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("capture_id must be a UUID") from exc
        if str(parsed) != value:
            raise ValueError("capture_id must use canonical UUID form")
        return value

    @model_validator(mode="after")
    def validate_envelope(self) -> "CaptureResponse":
        if self.ok:
            if self.status != "processed" or self.result is None or self.error_code is not None:
                raise ValueError("successful responses require processed result")
        elif self.error_code is None or self.result is not None:
            raise ValueError("unsuccessful responses require an error without result")
        return self
