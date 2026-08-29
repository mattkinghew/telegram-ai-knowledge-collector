"""ASGI request-body limiter that stops reading after the configured cap."""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict

from fastapi.responses import JSONResponse


ASGIApp = Callable[
    [
        Dict[str, Any],
        Callable[..., Awaitable[Dict[str, Any]]],
        Callable[..., Awaitable[None]],
    ],
    Awaitable[None],
]


class BodyLimitMiddleware:
    def __init__(self, app: ASGIApp, *, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        declared = headers.get(b"content-length", b"")
        if declared.isdigit() and int(declared) > self.max_bytes:
            await self._reject(scope, receive, send)
            return

        received = 0
        too_large = False

        async def limited_receive():
            nonlocal received, too_large
            message = await receive()
            if message.get("type") == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    too_large = True
                    return {"type": "http.request", "body": b"", "more_body": False}
            return message

        async def limited_send(message) -> None:
            if not too_large:
                await send(message)

        await self.app(scope, limited_receive, limited_send)
        if too_large:
            await self._reject(scope, receive, send)

    @staticmethod
    async def _reject(scope, receive, send) -> None:
        response = JSONResponse(
            status_code=413,
            content={
                "error": {
                    "code": "PAYLOAD_TOO_LARGE",
                    "message": "Request exceeded the configured payload limit.",
                }
            },
            headers={
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "Referrer-Policy": "no-referrer",
                "Content-Security-Policy": "default-src 'self'; frame-ancestors 'none'",
                "Cache-Control": "no-store",
            },
        )
        await response(scope, receive, send)
