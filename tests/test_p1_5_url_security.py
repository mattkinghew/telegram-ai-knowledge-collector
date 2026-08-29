from __future__ import annotations

import socket
import unittest
from pathlib import Path

from backend.services.extraction import (
    ExtractedArticle,
    FetchResponse,
    URLExtractionError,
    URLExtractor,
    validate_safe_url,
)


ROOT = Path(__file__).parent.parent
PUBLIC_IP = "93.184.216.34"


def resolver(host: str, port: int, *, type: int):
    del port, type
    addresses = {
        "example.com": PUBLIC_IP,
        "public.example": PUBLIC_IP,
        "private.example": "10.0.0.8",
        "mixed.example": PUBLIC_IP,
    }
    if host == "mixed.example":
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", (PUBLIC_IP, 443)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.168.1.8", 443)),
        ]
    if host not in addresses:
        raise socket.gaierror("fictional unresolved host")
    address = addresses[host]
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, 443))]


class FakeTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url: str, *, limits):
        self.calls.append((url, limits))
        return self.responses.pop(0)


class P15URLSecurityTests(unittest.TestCase):
    def test_public_http_and_https_are_accepted(self) -> None:
        self.assertEqual(
            validate_safe_url("https://example.com/a", resolver=resolver),
            "https://example.com/a",
        )
        self.assertEqual(
            validate_safe_url("http://example.com/a", resolver=resolver),
            "http://example.com/a",
        )

    def test_local_private_link_local_and_reserved_targets_are_rejected(self) -> None:
        urls = (
            "http://localhost/a",
            "http://127.0.0.1/a",
            "http://[::1]/a",
            "http://192.168.1.1/a",
            "http://10.0.0.1/a",
            "http://172.16.0.1/a",
            "http://172.31.255.255/a",
            "http://169.254.169.254/latest/meta-data",
            "http://0.0.0.0/a",
            "http://224.0.0.1/a",
            "https://private.example/a",
            "https://mixed.example/a",
        )
        for url in urls:
            with self.subTest(url=url), self.assertRaises(URLExtractionError):
                validate_safe_url(url, resolver=resolver)

    def test_unsupported_scheme_credentials_and_malformed_urls_are_rejected(self) -> None:
        for url in (
            "file:///etc/passwd",
            "ftp://example.com/a",
            "data:text/plain,hello",
            "javascript:alert(1)",
            "https://user:pass@example.com/a",
            "https:///missing-host",
            "not a url",
        ):
            with self.subTest(url=url), self.assertRaises(URLExtractionError):
                validate_safe_url(url, resolver=resolver)

    def test_html_fixture_is_extracted_and_bounded_without_script_or_style(self) -> None:
        body = (ROOT / "samples" / "p1_5_article_fixture.html").read_bytes()
        transport = FakeTransport(
            [FetchResponse(200, {"content-type": "text/html; charset=utf-8"}, body)]
        )
        result = URLExtractor(resolver=resolver, transport=transport).extract(
            "https://example.com/article"
        )
        self.assertIsInstance(result, ExtractedArticle)
        self.assertIn("Fictional Capture Workflow", result.text)
        self.assertIn("preserves raw evidence", result.text)
        self.assertNotIn("window.secret", result.text)
        self.assertNotIn("color: black", result.text)

    def test_redirect_destination_is_revalidated_before_second_request(self) -> None:
        transport = FakeTransport(
            [
                FetchResponse(
                    302,
                    {"location": "https://private.example/internal"},
                    b"",
                )
            ]
        )
        with self.assertRaisesRegex(URLExtractionError, "non-public"):
            URLExtractor(resolver=resolver, transport=transport).extract(
                "https://example.com/start"
            )
        self.assertEqual(len(transport.calls), 1)

    def test_relative_redirect_is_supported_but_redirect_count_is_bounded(self) -> None:
        transport = FakeTransport(
            [
                FetchResponse(302, {"location": "/two"}, b""),
                FetchResponse(302, {"location": "/three"}, b""),
                FetchResponse(302, {"location": "/four"}, b""),
                FetchResponse(302, {"location": "/five"}, b""),
            ]
        )
        extractor = URLExtractor(resolver=resolver, transport=transport)
        with self.assertRaisesRegex(URLExtractionError, "redirect"):
            extractor.extract("https://example.com/one")
        self.assertEqual(len(transport.calls), 4)

    def test_oversized_body_and_content_length_are_rejected(self) -> None:
        for response in (
            FetchResponse(200, {"content-type": "text/plain"}, b"x" * 1_000_001),
            FetchResponse(
                200,
                {"content-type": "text/plain", "content-length": "1000001"},
                b"x",
            ),
        ):
            with self.subTest(headers=response.headers):
                transport = FakeTransport([response])
                with self.assertRaisesRegex(URLExtractionError, "size limit"):
                    URLExtractor(resolver=resolver, transport=transport).extract(
                        "https://example.com/large"
                    )

    def test_unsupported_mime_and_http_failure_are_actionable(self) -> None:
        cases = (
            (
                FetchResponse(200, {"content-type": "application/pdf"}, b"pdf"),
                "UNSUPPORTED_CONTENT_TYPE",
            ),
            (
                FetchResponse(503, {"content-type": "text/plain"}, b"unavailable"),
                "URL_FETCH_FAILED",
            ),
        )
        for response, code in cases:
            with self.subTest(code=code):
                with self.assertRaises(URLExtractionError) as caught:
                    URLExtractor(
                        resolver=resolver,
                        transport=FakeTransport([response]),
                    ).extract("https://example.com/a")
                self.assertEqual(caught.exception.error_code, code)

    def test_limits_are_explicit_and_forwarded_to_transport(self) -> None:
        transport = FakeTransport(
            [FetchResponse(200, {"content-type": "text/plain"}, b"fictional")]
        )
        extractor = URLExtractor(resolver=resolver, transport=transport)
        extractor.extract("https://example.com/a")
        limits = transport.calls[0][1]
        self.assertEqual(limits.connect_timeout_seconds, 5.0)
        self.assertEqual(limits.read_timeout_seconds, 10.0)
        self.assertEqual(limits.max_redirects, 3)
        self.assertEqual(limits.max_response_bytes, 1_000_000)
        self.assertEqual(limits.max_extracted_characters, 20_000)


if __name__ == "__main__":
    unittest.main()
