"""Shared, redacted Gemini credential lookup for local diagnostics."""

from __future__ import annotations

import getpass
import os
import subprocess
import sys
from typing import Mapping, Optional

KEYCHAIN_SERVICE = "com.business-knowledge-capture.p1-5.gemini-api-key"
MIN_GEMINI_KEY_LENGTH = 20


def load_gemini_key(values: Optional[Mapping[str, str]] = None) -> tuple[str, str]:
    """Read an explicit mapping, or the current environment/Keychain."""
    environ = os.environ if values is None else values
    configured = environ.get("GEMINI_API_KEY", "")
    if configured:
        return configured, "environment"
    if values is not None or sys.platform != "darwin":
        return "", "unavailable"
    result = subprocess.run(
        [
            "/usr/bin/security",
            "find-generic-password",
            "-s",
            KEYCHAIN_SERVICE,
            "-a",
            getpass.getuser(),
            "-w",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return "", "keychain_unavailable"
    return result.stdout.rstrip("\n"), "keychain"


def credential_shape(api_key: str) -> str:
    """Classify shape without returning any key characters."""
    if not api_key:
        return "missing"
    if api_key != api_key.strip() or any(character.isspace() for character in api_key):
        return "whitespace"
    if len(api_key) < MIN_GEMINI_KEY_LENGTH:
        return "too_short"
    if not api_key.startswith("AIza"):
        return "prefix_mismatch"
    return "valid_shape"
