import unittest

from tools.p1_5_authenticated_live_smoke import fictional_payload, handoff_is_complete


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


if __name__ == "__main__":
    unittest.main()
