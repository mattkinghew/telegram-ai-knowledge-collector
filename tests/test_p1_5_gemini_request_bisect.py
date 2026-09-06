from __future__ import annotations

import json
import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import httpx

from tools.p1_5_gemini_request_bisect import (
    MAX_SANITIZED_MESSAGE,
    _credential_metadata,
    _sanitized_http_error,
    run,
)
from tools.p1_5_gemini_credential import credential_shape, load_gemini_key


class GeminiRequestBisectDiagnosticsTests(unittest.TestCase):
    def test_credential_shape_rejects_short_and_wrong_prefix(self) -> None:
        self.assertEqual(credential_shape("short"), "too_short")
        self.assertEqual(credential_shape("not-a-real-key-value"), "prefix_mismatch")
        self.assertEqual(credential_shape("AIza" + "x" * 20), "valid_shape")

    def test_explicit_environment_key_is_the_only_value_loaded(self) -> None:
        key, source = load_gemini_key({"GEMINI_API_KEY": "fictional-value"})
        self.assertEqual((key, source), ("fictional-value", "environment"))

    def test_credential_metadata_never_contains_key(self) -> None:
        metadata = _credential_metadata("AIza-fictional-secret-value")
        self.assertEqual(metadata["exists"], True)
        self.assertEqual(metadata["source"], "environment")
        self.assertEqual(metadata["prefix_shape"], True)
        self.assertNotIn("AIza", repr(metadata))

    def test_http_error_extracts_bounded_safe_fields_only(self) -> None:
        body = json.dumps(
            {
                "error": {
                    "status": "INVALID_ARGUMENT",
                    "message": "Invalid request; x-goog-api-key=AIza1234567890 and private prompt text",
                    "details": [{"reason": "BAD_REQUEST"}],
                }
            }
        ).encode()
        result = _sanitized_http_error(body)
        self.assertEqual(result["status"], "INVALID_ARGUMENT")
        self.assertEqual(result["reason"], "BAD_REQUEST")
        self.assertLessEqual(len(result["message"]), MAX_SANITIZED_MESSAGE)
        self.assertNotIn("AIza", result["message"])
        self.assertNotIn("x-goog-api-key=", result["message"])

    def test_malformed_error_body_is_metadata_only(self) -> None:
        self.assertEqual(
            _sanitized_http_error(b"private response body"),
            {"status": "UNKNOWN", "message": "non_json_error", "reason": ""},
        )

    def test_invalid_credential_fails_closed_without_transport(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            result = run(
                environ={"GEMINI_API_KEY": "too-short", "GEMINI_MODEL": "gemini-3.6-flash"}
            )
        self.assertEqual(result, 2)
        self.assertIn("CREDENTIAL_LENGTH=9", output.getvalue())
        self.assertNotIn("too-short", output.getvalue())

    def test_expected_network_error_is_bounded_without_traceback(self) -> None:
        class FailingClient:
            def stream(self, *args, **kwargs):
                raise httpx.ConnectError("private detail")

            def close(self):
                return None

        class FakeProvider:
            def __init__(self, **kwargs):
                self._client = FailingClient()
                self._model = kwargs["model"]

            def _payload(self, request):
                return {
                    "model": self._model,
                    "input": "fictional",
                    "system_instruction": "fictional",
                    "response_format": [{"schema": {"type": "object"}}],
                }

        output = io.StringIO()
        with patch("tools.p1_5_gemini_request_bisect.GeminiProvider", FakeProvider):
            with redirect_stdout(output):
                result = run(
                    environ={
                        "GEMINI_API_KEY": "AIza" + "x" * 20,
                        "GEMINI_MODEL": "gemini-3.6-flash",
                    }
                )
        self.assertEqual(result, 1)
        self.assertIn("error_category=connect", output.getvalue())
        self.assertNotIn("Traceback", output.getvalue())
        self.assertNotIn("private detail", output.getvalue())


if __name__ == "__main__":
    unittest.main()
