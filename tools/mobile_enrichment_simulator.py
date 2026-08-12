#!/usr/bin/env python3
"""DEVELOPMENT SIMULATOR ONLY — NOT AI AND NOT PRODUCTION.

The simulator validates fictional version-2 enrichment requests and emits
deterministic responses. It performs no network, credential, or Vault access.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence
from urllib.parse import urlparse


SCHEMA_VERSION = "2"
MAX_RAW_CONTENT_CHARS = 50_000
SOURCE_TYPES = frozenset(
    {
        "personal",
        "clipboard",
        "voice_transcript",
        "url",
        "shared_text",
        "image_reference",
        "file_reference",
    }
)
OUTPUT_GOALS = frozenset(
    {"collect", "task", "content", "project_knowledge", "progress", "decision"}
)
REQUEST_FIELDS = frozenset(
    {
        "schema_version",
        "source_type",
        "source",
        "raw_content",
        "user_insight",
        "user_context",
        "user_action",
        "output_goal",
        "project",
        "allowed_projects",
    }
)
RESULT_FIELDS = frozenset(
    {
        "suggested_title",
        "one_sentence_insight",
        "supporting_points",
        "possible_applications",
        "suggested_next_action",
        "output_angle",
        "related_project",
        "facts_to_verify",
        "missing_information",
        "confidence",
    }
)
FAILURES = {
    "ai_unavailable": (
        "AI_UNAVAILABLE",
        "AI enrichment is unavailable.",
    ),
    "timeout": (
        "AI_TIMEOUT",
        "AI enrichment timed out.",
    ),
}


class EnrichmentContractError(ValueError):
    """Raised when a request or response violates the offline contract."""


def _string(
    payload: Mapping[str, Any],
    name: str,
    max_length: int,
    *,
    required: bool = False,
) -> str:
    value = payload.get(name)
    if not isinstance(value, str):
        raise EnrichmentContractError(f"{name} must be a string")
    if len(value) > max_length:
        raise EnrichmentContractError(f"{name} exceeds {max_length} characters")
    if required and not value.strip():
        raise EnrichmentContractError(f"{name} is required")
    return value.replace("\r\n", "\n").replace("\r", "\n")


def validate_enrichment_request(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise EnrichmentContractError("request must be an object")
    unknown = set(payload) - REQUEST_FIELDS
    missing = REQUEST_FIELDS - set(payload)
    if unknown:
        raise EnrichmentContractError("unexpected request fields")
    if missing:
        raise EnrichmentContractError("missing request fields")
    if payload["schema_version"] != SCHEMA_VERSION:
        raise EnrichmentContractError("unsupported schema_version")

    source_type = _string(payload, "source_type", 40, required=True)
    if source_type not in SOURCE_TYPES:
        raise EnrichmentContractError("unsupported source_type")
    source = _string(payload, "source", 2_048)
    if source_type == "url":
        parsed = urlparse(source)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or parsed.username is not None
            or parsed.password is not None
            or any(character.isspace() for character in source)
        ):
            raise EnrichmentContractError("source must be an HTTP or HTTPS URL")
    else:
        if len(source) > 500:
            raise EnrichmentContractError("source exceeds 500 characters")
        if source.startswith(('/', '\\')) or re.match(
            r"^[A-Za-z]:[\\/]", source
        ):
            raise EnrichmentContractError("source must not be an absolute local path")

    output_goal = _string(payload, "output_goal", 40, required=True)
    if output_goal not in OUTPUT_GOALS:
        raise EnrichmentContractError("unsupported output_goal")
    raw_content = _string(
        payload,
        "raw_content",
        MAX_RAW_CONTENT_CHARS,
        required=True,
    )
    user_insight = _string(payload, "user_insight", 2_000, required=True)
    user_context = _string(payload, "user_context", 2_000, required=True)
    user_action = _string(payload, "user_action", 1_000)
    project = _string(payload, "project", 200)

    allowed_projects_value = payload["allowed_projects"]
    if not isinstance(allowed_projects_value, list):
        raise EnrichmentContractError("allowed_projects must be an array")
    if len(allowed_projects_value) > 20:
        raise EnrichmentContractError("allowed_projects exceeds 20 items")
    allowed_projects = []
    for value in allowed_projects_value:
        if not isinstance(value, str) or not value or len(value) > 200 or "\n" in value:
            raise EnrichmentContractError("invalid allowed project")
        allowed_projects.append(value)
    if len(set(allowed_projects)) != len(allowed_projects):
        raise EnrichmentContractError("allowed_projects must be unique")
    if project and project not in allowed_projects:
        raise EnrichmentContractError("project must be in allowed_projects")

    return {
        "schema_version": SCHEMA_VERSION,
        "source_type": source_type,
        "source": source,
        "raw_content": raw_content,
        "user_insight": user_insight,
        "user_context": user_context,
        "user_action": user_action,
        "output_goal": output_goal,
        "project": project,
        "allowed_projects": allowed_projects,
    }


def _validate_optional_string(value: Any, name: str, max_length: int) -> None:
    if value is not None and (
        not isinstance(value, str) or not value or len(value) > max_length
    ):
        raise EnrichmentContractError(f"invalid {name}")


def _validate_string_list(value: Any, name: str, max_items: int) -> None:
    if not isinstance(value, list) or len(value) > max_items:
        raise EnrichmentContractError(f"invalid {name}")
    if any(not isinstance(item, str) or not item or len(item) > 500 for item in value):
        raise EnrichmentContractError(f"invalid {name} item")


def validate_success_response(
    payload: Mapping[str, Any],
    *,
    allowed_projects: Sequence[str],
) -> dict[str, Any]:
    if not isinstance(payload, Mapping) or set(payload) != {"ok", "schema_version", "result"}:
        raise EnrichmentContractError("invalid success envelope")
    if payload["ok"] is not True or payload["schema_version"] != SCHEMA_VERSION:
        raise EnrichmentContractError("invalid success envelope values")
    result = payload["result"]
    if not isinstance(result, Mapping) or set(result) != RESULT_FIELDS:
        raise EnrichmentContractError("invalid result fields")
    _validate_optional_string(result["suggested_title"], "suggested_title", 200)
    _validate_optional_string(
        result["one_sentence_insight"], "one_sentence_insight", 500
    )
    _validate_optional_string(
        result["suggested_next_action"], "suggested_next_action", 500
    )
    _validate_optional_string(result["output_angle"], "output_angle", 500)
    _validate_optional_string(result["related_project"], "related_project", 200)
    _validate_string_list(result["supporting_points"], "supporting_points", 3)
    _validate_string_list(result["possible_applications"], "possible_applications", 3)
    _validate_string_list(result["facts_to_verify"], "facts_to_verify", 5)
    _validate_string_list(result["missing_information"], "missing_information", 5)
    if result["confidence"] not in {"low", "medium", "high"}:
        raise EnrichmentContractError("invalid confidence")
    if result["related_project"] is not None and result["related_project"] not in allowed_projects:
        raise EnrichmentContractError("related_project is not allowed")
    return dict(payload)


def _success_payload(request: Mapping[str, Any]) -> dict[str, Any]:
    related_project = request["project"] or None
    missing_information = []
    facts_to_verify = []
    if request["source_type"] in {"url", "image_reference", "file_reference"}:
        missing_information.append("The referenced source content was not supplied.")
        facts_to_verify.append("Verify the referenced source before reuse.")
    return {
        "ok": True,
        "schema_version": SCHEMA_VERSION,
        "result": {
            "suggested_title": "Fictional enrichment suggestion",
            "one_sentence_insight": "Review the user insight against the supplied source evidence.",
            "supporting_points": ["The user supplied an insight and intended context."],
            "possible_applications": ["Use the capture in the user-selected output goal."],
            "suggested_next_action": request["user_action"] or None,
            "output_angle": None,
            "related_project": related_project,
            "facts_to_verify": facts_to_verify,
            "missing_information": missing_information,
            "confidence": "medium" if request["raw_content"] else "low",
        },
    }


def simulate_enrichment(payload: Mapping[str, Any], *, mode: str = "success") -> Any:
    """Return deterministic fake data for contract development only."""

    request = validate_enrichment_request(payload)
    if mode == "success":
        response = _success_payload(request)
        return validate_success_response(
            response,
            allowed_projects=request["allowed_projects"],
        )
    if mode in FAILURES:
        error_code, message = FAILURES[mode]
        return {"ok": False, "error_code": error_code, "message": message}
    if mode == "invalid_json":
        return '{"ok": true, "result":'
    if mode == "schema_mismatch":
        response = _success_payload(request)
        response["result"]["supporting_points"] = ["one", "two", "three", "four"]
        return response
    raise EnrichmentContractError(f"unknown simulator mode: {mode}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="DEVELOPMENT SIMULATOR ONLY — NOT AI AND NOT PRODUCTION."
    )
    parser.add_argument("request", type=Path, help="Fictional request JSON")
    parser.add_argument(
        "--mode",
        default="success",
        choices=(
            "success",
            "ai_unavailable",
            "timeout",
            "invalid_json",
            "schema_mismatch",
        ),
    )
    args = parser.parse_args(argv)
    payload = json.loads(args.request.read_text(encoding="utf-8"))
    response = simulate_enrichment(payload, mode=args.mode)
    if isinstance(response, str):
        print(response)
    else:
        print(json.dumps(response, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
