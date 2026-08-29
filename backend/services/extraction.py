"""Bounded HTTP(S) article extraction with explicit SSRF controls."""

from __future__ import annotations

import codecs
import html
import ipaddress
import re
import socket
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Callable, Dict, Optional, Protocol
from urllib.parse import urljoin, urlparse

import httpx


Resolver = Callable[..., list[tuple[object, ...]]]
REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})
ACCEPTED_CONTENT_TYPES = frozenset(
    {"text/html", "application/xhtml+xml", "text/plain"}
)


class URLExtractionError(ValueError):
    def __init__(self, error_code: str, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code


@dataclass(frozen=True)
class FetchLimits:
    connect_timeout_seconds: float = 5.0
    read_timeout_seconds: float = 10.0
    max_redirects: int = 3
    max_response_bytes: int = 1_000_000
    max_extracted_characters: int = 20_000


@dataclass(frozen=True)
class FetchResponse:
    status_code: int
    headers: Dict[str, str]
    body: bytes


@dataclass(frozen=True)
class ExtractedArticle:
    final_url: str
    content_type: str
    text: str


class Transport(Protocol):
    def get(self, url: str, *, limits: FetchLimits) -> FetchResponse:
        """Fetch one response with redirects disabled."""


class HTTPXTransport:
    """Production transport with separate timeouts and bounded streaming."""

    def get(self, url: str, *, limits: FetchLimits) -> FetchResponse:
        timeout = httpx.Timeout(
            connect=limits.connect_timeout_seconds,
            read=limits.read_timeout_seconds,
            write=limits.connect_timeout_seconds,
            pool=limits.connect_timeout_seconds,
        )
        try:
            with httpx.Client(
                timeout=timeout,
                follow_redirects=False,
                trust_env=False,
            ) as client:
                with client.stream(
                    "GET",
                    url,
                    headers={"User-Agent": "HybridCaptureP1.5/1.0"},
                ) as response:
                    headers = {key.lower(): value for key, value in response.headers.items()}
                    declared = headers.get("content-length")
                    if declared and declared.isdigit() and int(declared) > limits.max_response_bytes:
                        raise URLExtractionError(
                            "PAYLOAD_TOO_LARGE",
                            "Article response exceeded the configured size limit.",
                        )
                    chunks = bytearray()
                    for chunk in response.iter_bytes():
                        chunks.extend(chunk)
                        if len(chunks) > limits.max_response_bytes:
                            raise URLExtractionError(
                                "PAYLOAD_TOO_LARGE",
                                "Article response exceeded the configured size limit.",
                            )
                    return FetchResponse(response.status_code, headers, bytes(chunks))
        except URLExtractionError:
            raise
        except httpx.TimeoutException as exc:
            raise URLExtractionError(
                "NETWORK_UNAVAILABLE",
                "Article request timed out — original URL was preserved.",
            ) from exc
        except httpx.HTTPError as exc:
            raise URLExtractionError(
                "URL_FETCH_FAILED",
                "Article could not be fetched — original URL was preserved.",
            ) from exc


def validate_safe_url(
    url: str,
    *,
    resolver: Resolver = socket.getaddrinfo,
) -> str:
    """Reject non-public destinations before each outbound request."""

    if not isinstance(url, str) or any(character.isspace() for character in url):
        raise URLExtractionError("INVALID_REQUEST", "URL is malformed.")
    parsed = urlparse(url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.hostname is None
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise URLExtractionError(
            "INVALID_REQUEST",
            "Only HTTP or HTTPS URLs without credentials are supported.",
        )
    hostname = parsed.hostname.rstrip(".").lower()
    if hostname == "localhost" or hostname.endswith(".localhost") or "%" in hostname:
        raise URLExtractionError("INVALID_REQUEST", "URL resolved to a non-public address.")
    try:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
    except ValueError as exc:
        raise URLExtractionError("INVALID_REQUEST", "URL port is invalid.") from exc
    try:
        addresses = [ipaddress.ip_address(hostname)]
    except ValueError:
        try:
            records = resolver(hostname, port, type=socket.SOCK_STREAM)
        except (socket.gaierror, UnicodeError) as exc:
            raise URLExtractionError(
                "URL_FETCH_FAILED",
                "URL hostname could not be resolved — original URL was preserved.",
            ) from exc
        addresses = []
        for record in records:
            address_text = str(record[4][0]).split("%", 1)[0]
            try:
                address = ipaddress.ip_address(address_text)
            except ValueError as exc:
                raise URLExtractionError(
                    "INVALID_REQUEST", "URL resolved to an invalid address."
                ) from exc
            if address not in addresses:
                addresses.append(address)
    if not addresses or any(
        not address.is_global
        or address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
        for address in addresses
    ):
        raise URLExtractionError("INVALID_REQUEST", "URL resolved to a non-public address.")
    return url


class _ReadableHTML(HTMLParser):
    SKIPPED = frozenset({"script", "style", "noscript", "svg", "nav", "footer"})

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._depth = 0
        self._parts = []

    def handle_starttag(self, tag: str, attrs) -> None:
        del attrs
        if tag.lower() in self.SKIPPED:
            self._depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in self.SKIPPED and self._depth:
            self._depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._depth and data.strip():
            self._parts.append(data.strip())

    def text(self) -> str:
        return "\n".join(self._parts)


def _decode(body: bytes, content_type_header: str) -> str:
    match = re.search(r"charset=([^;\s]+)", content_type_header, re.IGNORECASE)
    charset = match.group(1).strip('"\'') if match else "utf-8"
    try:
        codecs.lookup(charset)
    except LookupError:
        charset = "utf-8"
    return body.decode(charset, errors="replace")


class URLExtractor:
    def __init__(
        self,
        *,
        resolver: Resolver = socket.getaddrinfo,
        transport: Optional[Transport] = None,
        limits: FetchLimits = FetchLimits(),
    ) -> None:
        self.resolver = resolver
        self.transport = transport or HTTPXTransport()
        self.limits = limits

    def extract(self, url: str) -> ExtractedArticle:
        current = url
        redirects = 0
        while True:
            validate_safe_url(current, resolver=self.resolver)
            response = self.transport.get(current, limits=self.limits)
            if response.status_code in REDIRECT_STATUSES:
                if redirects >= self.limits.max_redirects:
                    raise URLExtractionError(
                        "URL_FETCH_FAILED",
                        "Article redirect limit was exceeded — original URL was preserved.",
                    )
                location = response.headers.get("location")
                if not location:
                    raise URLExtractionError(
                        "URL_FETCH_FAILED",
                        "Article redirect had no destination — original URL was preserved.",
                    )
                current = urljoin(current, location)
                redirects += 1
                continue
            if not 200 <= response.status_code < 300:
                raise URLExtractionError(
                    "URL_FETCH_FAILED",
                    "Article request failed — original URL was preserved.",
                )
            declared = response.headers.get("content-length")
            if (
                (declared and declared.isdigit() and int(declared) > self.limits.max_response_bytes)
                or len(response.body) > self.limits.max_response_bytes
            ):
                raise URLExtractionError(
                    "PAYLOAD_TOO_LARGE",
                    "Article response exceeded the configured size limit.",
                )
            content_type_header = response.headers.get("content-type", "")
            content_type = content_type_header.split(";", 1)[0].strip().lower()
            if content_type not in ACCEPTED_CONTENT_TYPES:
                raise URLExtractionError(
                    "UNSUPPORTED_CONTENT_TYPE",
                    "Article content type is unsupported — original URL was preserved.",
                )
            decoded = _decode(response.body, content_type_header)
            if content_type in {"text/html", "application/xhtml+xml"}:
                parser = _ReadableHTML()
                parser.feed(decoded)
                text = html.unescape(parser.text())
            else:
                text = decoded
            text = text.strip()[: self.limits.max_extracted_characters]
            if not text:
                raise URLExtractionError(
                    "URL_FETCH_FAILED",
                    "Article text could not be extracted — original URL was preserved.",
                )
            return ExtractedArticle(current, content_type, text)
