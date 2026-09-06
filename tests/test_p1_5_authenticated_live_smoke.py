import unittest
from unittest import mock

from tools.p1_5_authenticated_live_smoke import (
    fictional_payload,
    handoff_is_complete,
    safe_response_diagnostics,
    _request,
)


class AuthenticatedLiveSmokeTest(unittest.TestCase):
    def test_payload_is_fictional_and_schema_complete(self):
        payload = fictional_payload()
        self.assertEqual(payload["schema_version"], "1")
        self.assertEqual(payload["capture_type"], "voice")
        self.assertEqual(payload["source_type"], "voice_transcript")
        self.assertEqual(payload["requested_processing"], "voice_structure")
        self.assertIn("Fictional Project Aurora", payload["raw_content"])

    def test_handoff_requires_all_safe_contract_fields(self):
        result = {
            "markdown": "# Fictional result",
            "obsidian_handoff": {
                "markdown": "# Fictional result",
                "suggested_filename": "fictional.md",
                "suggested_date": "2026-09-06",
                "record_type": "free",
                "title": "Fictional result",
                "folder_key": "inbox",
            },
        }
        self.assertTrue(handoff_is_complete(result))
        del result["obsidian_handoff"]["folder_key"]
        self.assertFalse(handoff_is_complete(result))

    def test_request_uses_explicit_api_headers_for_post(self):
        response = mock.MagicMock(status=202, headers={})
        response.read.return_value = b'{"status":"pending"}'
        response.__enter__.return_value = response
        with mock.patch(
            "tools.p1_5_authenticated_live_smoke.urllib.request.urlopen",
            return_value=response,
        ) as urlopen:
            _request("/api/v1/capture", "POST", "not-a-real-token", fictional_payload())

        request = urlopen.call_args.args[0]
        self.assertEqual(request.get_header("User-agent"), "business-knowledge-capture-smoke/1.0")
        self.assertEqual(request.get_header("Accept"), "application/json")
        self.assertEqual(request.get_header("Content-type"), "application/json")

    def test_request_uses_same_safe_headers_for_poll_get(self):
        response = mock.MagicMock(status=200, headers={})
        response.read.return_value = b'{"status":"processed"}'
        response.__enter__.return_value = response
        with mock.patch(
            "tools.p1_5_authenticated_live_smoke.urllib.request.urlopen",
            return_value=response,
        ) as urlopen:
            _request("/api/v1/captures/fictional", "GET", "not-a-real-token")

        request = urlopen.call_args.args[0]
        self.assertEqual(request.get_header("User-agent"), "business-knowledge-capture-smoke/1.0")
        self.assertEqual(request.get_header("Accept"), "application/json")
        self.assertEqual(request.get_header("Content-type"), "application/json")

    def test_cloudflare_diagnostics_are_redacted_metadata_only(self):
        diagnostics = safe_response_diagnostics(
            403,
            {"error_code": 1010, "html": "secret raw response must not print"},
            {
                "cf-ray": "fictional-ray",
                "cf-error-type": "1020",
                "server": "cloudflare",
                "content-type": "text/html; charset=UTF-8",
            },
        )
        self.assertEqual(
            diagnostics,
            [
                "HTTP_STATUS=403",
                "CLOUDFLARE_ERROR_CODE=1010",
                "CF_RAY=fictional-ray",
                "CF_ERROR_TYPE=1020",
                "SERVER=cloudflare",
                "CONTENT_TYPE=text/html; charset=UTF-8",
            ],
        )
        self.assertNotIn("secret raw response", "\n".join(diagnostics))

    def test_cloudflare_diagnostics_bound_untrusted_metadata(self):
        diagnostics = safe_response_diagnostics(
            403,
            {"error_code": "raw body\nwith secrets"},
            {"server": "cloudflare\nraw response", "content-type": "text/html"},
        )
        joined = "\n".join(diagnostics)
        self.assertIn("CLOUDFLARE_ERROR_CODE=unknown", joined)
        self.assertNotIn("raw body", joined)
        self.assertNotIn("\nraw response", joined)


if __name__ == "__main__":
    unittest.main()
