#!/usr/bin/env python3
"""Validate an explicitly supplied public example config without reading private data."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence


KNOWN_KEYS = frozenset(
    {"obsidian_vault_id", "active_projects", "make_webhook_url", "ai_enabled"}
)
PLACEHOLDER_VAULT_ID = "EXAMPLE_VAULT_ID"
WEBHOOK_PLACEHOLDERS = frozenset({"", "SET_ON_DEVICE_ONLY"})
CREDENTIAL_PATTERN = re.compile(
    r"(?i)(?:api[_ -]?key|(?:access[_ -]?)?token\s*[=:]|bearer\s+|password\s*[=:]|"
    r"secret\s*[=:]|(?:sk|ghp|glpat)-[A-Za-z0-9_-]{8,})"
)


class PrivateConfigValidationError(ValueError):
    """Raised when a public example contains private or unsupported values."""


def _safe_project_name(value: Any) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 80:
        raise PrivateConfigValidationError(
            "active_projects must contain non-empty strings up to 80 characters"
        )
    if "\n" in value or "\r" in value:
        raise PrivateConfigValidationError("active project names must be single-line")
    if CREDENTIAL_PATTERN.search(value):
        raise PrivateConfigValidationError("credential-like content is not allowed")
    return value


def validate_private_config(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return a normalized example config or raise a bounded validation error."""

    if not isinstance(payload, Mapping) or set(payload) != KNOWN_KEYS:
        raise PrivateConfigValidationError(
            "config must contain exactly the known keys: " + ", ".join(sorted(KNOWN_KEYS))
        )
    if payload["obsidian_vault_id"] != PLACEHOLDER_VAULT_ID:
        raise PrivateConfigValidationError(
            "obsidian_vault_id must remain EXAMPLE_VAULT_ID in Git"
        )
    projects = payload["active_projects"]
    if not isinstance(projects, list) or not 1 <= len(projects) <= 8:
        raise PrivateConfigValidationError("active_projects must contain 1-8 items")
    normalized_projects = [_safe_project_name(value) for value in projects]
    if len(set(normalized_projects)) != len(normalized_projects):
        raise PrivateConfigValidationError("active_projects must be unique")
    webhook = payload["make_webhook_url"]
    if webhook not in WEBHOOK_PLACEHOLDERS:
        raise PrivateConfigValidationError(
            "make_webhook_url must remain SET_ON_DEVICE_ONLY or blank"
        )
    if not isinstance(payload["ai_enabled"], bool):
        raise PrivateConfigValidationError("ai_enabled must be a boolean")
    return {
        "obsidian_vault_id": PLACEHOLDER_VAULT_ID,
        "active_projects": normalized_projects,
        "make_webhook_url": webhook,
        "ai_enabled": payload["ai_enabled"],
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "config",
        type=Path,
        help="Explicit path to the public example JSON; no config is auto-discovered",
    )
    args = parser.parse_args(argv)
    try:
        payload = json.loads(args.config.read_text(encoding="utf-8"))
        validate_private_config(payload)
    except (OSError, UnicodeError, json.JSONDecodeError, PrivateConfigValidationError) as exc:
        print(f"Private config example: FAIL — {exc}")
        return 1
    print("Private config example: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
