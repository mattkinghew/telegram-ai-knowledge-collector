from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import httpx

from backend.app import create_app
from backend.config import Settings, SettingsError
from backend.models import CaptureRequest, ProviderResult
from backend.providers.gemini import GeminiConfigurationError, GeminiProvider
from backend.providers.mock import MockProvider
from backend.services.capture import CaptureService
from backend.services.extraction import URLExtractor
from backend.storage.sqlite import CaptureStore, RetryLimitError


MODEL = "gemini-3.6-flash"
API_KEY = "fictional-gemini-test-key"


def provider_result(mode: str) -> dict:
    sections = {
        "voice_structure": {
            "completed": ["Completed a fictional CSV mapping."],
            "in_progress": [],
            "next_actions": ["Test the fictional invalid URL."],
            "blockers": [],
            "decisions": [],
            "knowledge": [],
            "content_ideas": ["Draft a fictional AI pricing post."],
            "facts_to_verify": [],
            "related_projects": ["Project Alpha"],
        },
        "summary": {},
        "recommendation": {
            "situation": ["A fictional project needs a bounded choice."],
            "insight": ["The evidence supports a small reversible test."],
            "recommended_action": ["Run the fictional test first."],
            "reason": ["It limits cost and preserves evidence."],
            "verification_risk": ["Confirm the result before adoption."],
        },
        "short_article": {
            "draft": ["AI draft: Fictional source material becomes a reviewable short post."],
        },
    }[mode]
    return {
        "processing_mode": mode,
        "title": "Fictional capture",
        "summary": "A bounded fictional result for review.",
        "points": ["Raw evidence remains separate."],
        "why_it_matters": "The result stays reviewable and unconfirmed.",
        "sections": sections,
    }


def interaction_response(result: dict) -> dict:
    return {
        "id": "int_fictional",
        "status": "completed",
        "steps": [
            {
                "type": "model_output",
                "status": "done",
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, ensure_ascii=False),
                    }
                ],
            }
        ],
    }


class GeminiProviderTests(unittest.TestCase):
    def voice_request(self) -> CaptureRequest:
        return CaptureRequest(
            schema_version="1",
            capture_type="voice",
            source_type="voice_transcript",
            source=None,
            raw_content=(
                "今日完成 Project Alpha 嘅 CSV mapping，下一步要測 invalid URL，"
                "另外想到可以寫一篇 AI pricing short post。"
            ),
            requested_processing="voice_structure",
            allowed_projects=["Project Alpha"],
        )

    def content_request(self, mode: str) -> CaptureRequest:
        return CaptureRequest(
            schema_version="1",
            capture_type="content",
            source_type="selected_text",
            source=None,
            raw_content="Fictional public-safe source text supplied directly.",
            requested_processing=mode,
            allowed_projects=[],
        )

    def provider_with_handler(self, handler) -> GeminiProvider:
        client = httpx.Client(
            transport=httpx.MockTransport(handler),
            trust_env=False,
        )
        self.addCleanup(client.close)
        return GeminiProvider(api_key=API_KEY, model=MODEL, client=client)

    def test_valid_voice_request_uses_minimal_prompt_and_strict_result(self) -> None:
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["request"] = request
            return httpx.Response(
                200,
                json=interaction_response(provider_result("voice_structure")),
            )

        outcome = self.provider_with_handler(handler).process(self.voice_request())

        self.assertIsInstance(outcome, ProviderResult)
        self.assertEqual(outcome.processing_mode, "voice_structure")
        request = captured["request"]
        self.assertEqual(request.method, "POST")
        self.assertEqual(
            str(request.url),
            "https://generativelanguage.googleapis.com/v1beta2/interactions",
        )
        self.assertEqual(request.headers["x-goog-api-key"], API_KEY)
        payload = json.loads(request.content)
        self.assertEqual(
            set(payload),
            {"model", "input", "system_instruction", "response_format"},
        )
        self.assertEqual(payload["model"], MODEL)
        provider_input = json.loads(payload["input"])
        self.assertEqual(
            set(provider_input),
            {"processing_mode", "raw_content", "allowed_projects"},
        )
        self.assertEqual(
            provider_input["raw_content"], self.voice_request().raw_content
        )
        self.assertIn("Structured Capture Processor", payload["system_instruction"])
        self.assertNotIn(API_KEY, request.content.decode("utf-8"))
        self.assertNotIn("Vault", payload["input"])

    def test_valid_content_modes_return_strict_results(self) -> None:
        for mode in ("summary", "recommendation", "short_article"):
            with self.subTest(mode=mode):
                def handler(request: httpx.Request, current_mode=mode) -> httpx.Response:
                    payload = json.loads(request.content)
                    provider_input = json.loads(payload["input"])
                    self.assertEqual(
                        set(provider_input),
                        {"processing_mode", "source_type", "raw_content"},
                    )
                    self.assertIn(
                        "Knowledge Enrichment", payload["system_instruction"]
                    )
                    return httpx.Response(
                        200,
                        json=interaction_response(provider_result(current_mode)),
                    )

                outcome = self.provider_with_handler(handler).process(
                    self.content_request(mode)
                )
                self.assertIsInstance(outcome, ProviderResult)
                self.assertEqual(outcome.processing_mode, mode)

    def test_unsupported_live_mode_fails_without_transport_call(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise AssertionError("unsupported mode must not call Gemini")

        outcome = self.provider_with_handler(handler).process(
            self.content_request("project_knowledge")
        )
        self.assertEqual(outcome.error_code, "INVALID_REQUEST")

    def test_timeout_and_network_failures_are_safely_mapped(self) -> None:
        def timeout(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("private timeout detail", request=request)

        def network(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("private network detail", request=request)

        for handler, expected in (
            (timeout, "AI_TIMEOUT"),
            (network, "NETWORK_UNAVAILABLE"),
        ):
            with self.subTest(expected=expected):
                outcome = self.provider_with_handler(handler).process(
                    self.content_request("summary")
                )
                self.assertEqual(outcome.error_code, expected)
                self.assertNotIn("private", outcome.message)

    def test_http_auth_quota_and_unavailable_failures_are_safely_mapped(self) -> None:
        for status, expected in (
            (401, "AI_AUTH_FAILED"),
            (403, "AI_AUTH_FAILED"),
            (429, "AI_RATE_LIMITED"),
            (500, "AI_UNAVAILABLE"),
            (503, "AI_UNAVAILABLE"),
        ):
            with self.subTest(status=status):
                def handler(request: httpx.Request, code=status) -> httpx.Response:
                    return httpx.Response(
                        code,
                        json={"error": {"message": "private provider response"}},
                    )

                outcome = self.provider_with_handler(handler).process(
                    self.content_request("summary")
                )
                self.assertEqual(outcome.error_code, expected)
                self.assertNotIn("private", outcome.message)

    def test_invalid_json_is_not_accepted(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "status": "completed",
                    "steps": [
                        {
                            "type": "model_output",
                            "status": "done",
                            "content": [{"type": "text", "text": "{not json"}],
                        }
                    ],
                },
            )

        outcome = self.provider_with_handler(handler).process(
            self.content_request("summary")
        )
        self.assertEqual(outcome.error_code, "INVALID_AI_JSON")

    def test_schema_mismatch_and_unexpected_fields_are_not_accepted(self) -> None:
        missing = provider_result("summary")
        missing.pop("summary")
        unexpected = dict(provider_result("summary"), provider_parameters={})
        for result in (missing, unexpected):
            with self.subTest(keys=sorted(result)):
                def handler(request: httpx.Request, value=result) -> httpx.Response:
                    return httpx.Response(200, json=interaction_response(value))

                outcome = self.provider_with_handler(handler).process(
                    self.content_request("summary")
                )
                self.assertEqual(outcome.error_code, "SCHEMA_MISMATCH")

    def test_response_mode_must_match_request_mode(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json=interaction_response(provider_result("recommendation")),
            )

        outcome = self.provider_with_handler(handler).process(
            self.content_request("summary")
        )
        self.assertEqual(outcome.error_code, "SCHEMA_MISMATCH")

    def test_oversized_provider_response_is_rejected(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=b"x" * (256 * 1024 + 1))

        outcome = self.provider_with_handler(handler).process(
            self.content_request("summary")
        )
        self.assertEqual(outcome.error_code, "PAYLOAD_TOO_LARGE")

    def test_provider_requires_explicit_valid_secret_and_model(self) -> None:
        for key, model in ((None, MODEL), ("", MODEL), (API_KEY, ""), (API_KEY, "other-model")):
            with self.subTest(key=bool(key), model=model), self.assertRaises(
                GeminiConfigurationError
            ):
                GeminiProvider(api_key=key, model=model)


class GeminiConfigurationTests(unittest.TestCase):
    def base_env(self) -> dict:
        return {
            "APP_ENV": "production",
            "AI_PROVIDER": "mock",
            "DATABASE_URL": "sqlite:///./data/test.sqlite3",
            "AUTH_MODE": "token",
            "API_AUTH_TOKEN": "fictional-api-auth-token",
            "ALLOWED_ORIGINS": "https://app.example",
        }

    def test_default_configuration_keeps_live_ai_disabled(self) -> None:
        settings = Settings.from_env(
            {
                "APP_ENV": "test",
                "DATABASE_URL": "sqlite:///./data/test.sqlite3",
                "ALLOWED_ORIGINS": "http://127.0.0.1:8000",
            }
        )
        self.assertEqual(settings.ai_provider, "mock")
        self.assertFalse(settings.enable_live_ai)
        self.assertIsNone(settings.gemini_api_key)
        self.assertIsNone(settings.gemini_model)

    def test_live_ai_requires_every_explicit_production_setting(self) -> None:
        valid = dict(
            self.base_env(),
            AI_PROVIDER="gemini",
            ENABLE_LIVE_AI="true",
            GEMINI_API_KEY=API_KEY,
            GEMINI_MODEL=MODEL,
        )
        settings = Settings.from_env(valid)
        self.assertTrue(settings.enable_live_ai)
        self.assertEqual(settings.gemini_model, MODEL)

        invalid_environments = [
            dict(valid, ENABLE_LIVE_AI="false"),
            dict(valid, GEMINI_API_KEY=""),
            dict(valid, GEMINI_MODEL=""),
            dict(valid, GEMINI_MODEL="other-model"),
            dict(valid, APP_ENV="development", AUTH_MODE="dev", API_AUTH_TOKEN=""),
            dict(valid, APP_ENV="test", AI_PROVIDER="gemini"),
            dict(valid, ENABLE_LIVE_AI="yes"),
            dict(self.base_env(), ENABLE_LIVE_AI="true"),
        ]
        for environment in invalid_environments:
            with self.subTest(environment=sorted(environment)), self.assertRaises(
                SettingsError
            ):
                Settings.from_env(environment)

    def test_secret_values_are_excluded_from_settings_repr(self) -> None:
        settings = Settings.from_env(
            dict(
                self.base_env(),
                AI_PROVIDER="gemini",
                ENABLE_LIVE_AI="true",
                GEMINI_API_KEY=API_KEY,
                GEMINI_MODEL=MODEL,
            )
        )
        representation = repr(settings)
        self.assertNotIn(API_KEY, representation)
        self.assertNotIn("fictional-api-auth-token", representation)

    def test_test_application_uses_mock_provider(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            settings = Settings(
                app_env="test",
                ai_provider="mock",
                database_path=Path(directory) / "captures.sqlite3",
                auth_mode="dev",
                api_auth_token=None,
                allowed_origins=("http://127.0.0.1:8000",),
            )
            application = create_app(settings=settings)
            self.assertIsInstance(
                application.state.capture_service.provider,
                MockProvider,
            )


class GeminiFailurePreservationTests(unittest.TestCase):
    def test_provider_failure_preserves_capture_and_manual_retry_is_bounded(self) -> None:
        def unavailable(request: httpx.Request) -> httpx.Response:
            return httpx.Response(503, json={"private": "provider detail"})

        client = httpx.Client(
            transport=httpx.MockTransport(unavailable),
            trust_env=False,
        )
        self.addCleanup(client.close)
        provider = GeminiProvider(api_key=API_KEY, model=MODEL, client=client)

        with tempfile.TemporaryDirectory() as directory:
            store = CaptureStore(Path(directory) / "captures.sqlite3")
            service = CaptureService(
                store=store,
                provider=provider,
                extractor=URLExtractor(),
            )
            request = CaptureRequest(
                schema_version="1",
                capture_type="content",
                source_type="article_url",
                source="https://example.invalid/fictional-source",
                raw_content="Fictional article supplied directly for safe processing.",
                requested_processing="summary",
                allowed_projects=[],
            )

            created = service.create(request)
            self.assertEqual(created.status, "pending")
            self.assertEqual(created.error_code, "AI_UNAVAILABLE")
            capture_id = created.capture_id

            for expected_retry_count in (1, 2):
                retried = service.retry(capture_id)
                self.assertEqual(retried.status, "pending")
                self.assertEqual(store.get(capture_id).retry_count, expected_retry_count)

            with self.assertRaises(RetryLimitError):
                service.retry(capture_id)

            stored = store.get(capture_id)
            self.assertEqual(stored.capture_id, capture_id)
            self.assertEqual(stored.source, request.source)
            self.assertEqual(stored.raw_content, request.raw_content)
            self.assertEqual(stored.requested_processing, "summary")
            self.assertNotIn("provider detail", stored.error_message)


if __name__ == "__main__":
    unittest.main()
