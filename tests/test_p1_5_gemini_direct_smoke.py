from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout

import httpx

from tools.p1_5_gemini_direct_smoke import GEMINI_ENDPOINT, main, run_direct_smoke


MODEL = "gemini-3.6-flash"
KEY = "fictional-direct-key"


def response(*, text: str = "GEMINI_OK") -> dict:
    return {"steps": [{"type": "model_output", "content": [{"type": "text", "text": text}]}]}


class DirectGeminiSmokeTests(unittest.TestCase):
    def test_missing_key_is_blocked(self) -> None:
        result = run_direct_smoke(environ={"GEMINI_MODEL": MODEL})
        self.assertTrue(result["blocked"])

    def test_success_uses_current_endpoint_and_never_exposes_key(self) -> None:
        seen = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["url"] = str(request.url)
            seen["key"] = request.headers["x-goog-api-key"]
            seen["body"] = request.content
            return httpx.Response(200, json=response())

        result = run_direct_smoke(
            environ={"GEMINI_API_KEY": KEY, "GEMINI_MODEL": MODEL},
            transport=httpx.MockTransport(handler),
        )
        self.assertEqual(result, {"ok": True, "category": None, "http_status": 200, "output_match": True})
        self.assertEqual(seen["url"], GEMINI_ENDPOINT)
        self.assertNotIn(KEY.encode(), b"GEMINI_DIRECT_SMOKE=PASS")
        self.assertEqual(__import__("json").loads(seen["body"])["input"], "Reply with exactly: GEMINI_OK")

    def test_status_mapping(self) -> None:
        for status, category in ((400, "PARSE"), (401, "AUTH"), (403, "PERMISSION"), (404, "MODEL"), (429, "QUOTA"), (503, "HTTP")):
            with self.subTest(status=status):
                result = run_direct_smoke(
                    environ={"GEMINI_API_KEY": KEY, "GEMINI_MODEL": MODEL},
                    transport=httpx.MockTransport(lambda request, status=status: httpx.Response(status)),
                )
                self.assertEqual((result["category"], result["http_status"]), (category, status))

    def test_timeout_network_and_malformed_response(self) -> None:
        def timeout(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("private detail")

        timeout_result = run_direct_smoke(
            environ={"GEMINI_API_KEY": KEY, "GEMINI_MODEL": MODEL},
            transport=httpx.MockTransport(timeout),
        )
        self.assertEqual(timeout_result["category"], "NETWORK")
        self.assertEqual(timeout_result["error_code"], "PROVIDER_TIMEOUT")
        malformed = httpx.MockTransport(lambda request: httpx.Response(200, text="not-json"))
        self.assertEqual(run_direct_smoke(environ={"GEMINI_API_KEY": KEY, "GEMINI_MODEL": MODEL}, transport=malformed)["category"], "PARSE")

    def test_request_contract_failure_is_not_network(self) -> None:
        result = run_direct_smoke(
            environ={"GEMINI_API_KEY": KEY, "GEMINI_MODEL": MODEL},
            endpoint="not-a-url",
        )
        self.assertEqual(result["category"], "REQUEST")
        self.assertEqual(result["error_code"], "MALFORMED_REQUEST")

        def unsupported(request: httpx.Request) -> httpx.Response:
            raise httpx.UnsupportedProtocol("hidden", request=request)

        result = run_direct_smoke(
            environ={"GEMINI_API_KEY": KEY, "GEMINI_MODEL": MODEL},
            transport=httpx.MockTransport(unsupported),
        )
        self.assertEqual(result["category"], "REQUEST")
        self.assertEqual(result["error_code"], "MALFORMED_REQUEST")

    def test_dns_tls_and_socket_failures_have_sanitized_codes(self) -> None:
        failures = (("gaierror", "PROVIDER_DNS"), ("SSLError", "PROVIDER_TLS"), ("ConnectionResetError", "PROVIDER_RESET"))
        for exception, code in failures:
            with self.subTest(code=code):
                cause = type(exception, (OSError,), {})()
                error = httpx.ConnectError("hidden", request=httpx.Request("POST", GEMINI_ENDPOINT))
                error.__cause__ = cause
                result = run_direct_smoke(
                    environ={"GEMINI_API_KEY": KEY, "GEMINI_MODEL": MODEL},
                    transport=httpx.MockTransport(lambda request, error=error: (_ for _ in ()).throw(error)),
                )
                self.assertEqual(result["category"], "NETWORK")
                self.assertEqual(result["error_code"], code)
                self.assertNotIn("hidden", str(result))

    def test_model_allowlist_and_cli_missing_key_do_not_print_secret(self) -> None:
        self.assertEqual(run_direct_smoke(environ={"GEMINI_API_KEY": KEY, "GEMINI_MODEL": "other"})["category"], "MODEL")
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(main([]), 2)
        self.assertNotIn(KEY, output.getvalue())


if __name__ == "__main__":
    unittest.main()
