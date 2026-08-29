"""Single-user API authentication boundary."""

from __future__ import annotations

import hmac

from fastapi import Request


def is_authorized(request: Request) -> bool:
    settings = request.app.state.settings
    if settings.auth_mode == "dev":
        return settings.app_env in {"development", "test"}
    header = request.headers.get("authorization", "")
    prefix = "Bearer "
    if not header.startswith(prefix) or settings.api_auth_token is None:
        return False
    return hmac.compare_digest(header[len(prefix) :], settings.api_auth_token)
