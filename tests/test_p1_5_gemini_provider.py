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


def interaction_response(result: dict, *, include_step_status: bool = True) -> dict:
    step = {
        "type": "model_output",
        "content": [
            {
                "type": "text",
                "text": json.dumps(result, ensure_ascii=False),
            }
        ],
    }
    if include_step_status:
        step["status"] = "done"
    return {
        "id": "int_fictional",
        "status": "completed",
        "steps": [step],
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
            "https://generativelanguage.googleapis.com/v1beta/interactions",
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

    def test_structured_request_allows_model_read_time_without_extending_connect_budget(self) -> None:
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["timeout"] = request.extensions.get("timeout")
            return httpx.Response(
                200,
                json=interaction_response(provider_result("summary")),
            )

        self.provider_with_handler(handler).process(self.content_request("summary"))

        self.assertEqual(
            captured["timeout"],
            {"connect": 5.0, "read": 60.0, "write": 10.0, "pool": 5.0},
        )

    def test_structured_schema_uses_only_interactions_supported_keywords(self) -> None:
        schema = GeminiProvider._response_schema("voice_structure")
        encoded = json.dumps(schema)
        self.assertNotIn("minLength", encoded)
        self.assertNotIn("maxLength", encoded)

    def test_capture_api_completes_through_gemini_provider_path(self) -> None:
        observed = {}

        def handler(request: httpx.Request) -> httpx.Response:
            observed["timeout"] = request.extensions.get("timeout")
            return httpx.Response(
                200,
                json=interaction_response(provider_result("voice_structure")),
            )

        client = httpx.Client(
            transport=httpx.MockTransport(handler),
            trust_env=False,
        )
        self.addCleanup(client.close)
        provider = GeminiProvider(api_key=API_KEY, model=MODEL, client=client)
        with tempfile.TemporaryDirectory() as directory:
            store = CaptureStore(Path(directory) / "captures.sqlite3")
            settings = Settings(
                app_env="production",
                ai_provider="gemini",
                database_path=Path(directory) / "captures.sqlite3",
                auth_mode="token",
                api_auth_token="fictional-api-auth-token",
                allowed_origins=("https://app.example",),
                enable_live_ai=True,
                gemini_api_key=API_KEY,
                gemini_model=MODEL,
            )
            application = create_app(settings=settings, store=store, provider=provider)

            from fastapi.testclient import TestClient

            with TestClient(application) as api:
                response = api.post(
                    "/api/v1/capture",
                    headers={"Authorization": "Bearer fictional-api-auth-token"},
                    json=self.voice_request().model_dump(mode="json"),
                )
                capture_id = response.json()["capture_id"]
                stored = store.get(capture_id)
                status_response = api.get(
                    "/api/v1/captures/" + capture_id,
                    headers={"Authorization": "Bearer fictional-api-auth-token"},
                )

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json()["status"], "pending")
        self.assertNotIn("error_code", response.json())
        self.assertNotIn("message", response.json())
        self.assertEqual(stored.status, "processed")
        self.assertTrue(stored.markdown)
        self.assertEqual(status_response.status_code, 200)
        self.assertEqual(status_response.json()["status"], "processed")
        self.assertEqual(
            observed["timeout"],
            {"connect": 5.0, "read": 60.0, "write": 10.0, "pool": 5.0},
        )

    def test_timing_diagnostics_are_stage_only_and_secret_free(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json=interaction_response(provider_result("summary")),
            )

        with self.assertLogs("backend.providers.gemini", level="INFO") as logs:
            self.provider_with_handler(handler).process(self.content_request("summary"))

        output = "\n".join(logs.output)
        for stage in (
            "request_construction",
            "network_request",
            "provider_response",
            "structured_parsing",
        ):
            self.assertIn(f"stage={stage}", output)
        self.assertIn("timeout_ms=0", output)
        self.assertNotIn(API_KEY, output)
        self.assertNotIn(self.content_request("summary").raw_content, output)
        self.assertNotIn("x-goog-api-key", output)

    def test_timeout_timing_identifies_network_stage_without_details(self) -> None:
        def timeout(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("private timeout detail", request=request)

        with self.assertLogs("backend.providers.gemini", level="INFO") as logs:
            outcome = self.provider_with_handler(timeout).process(
                self.content_request("summary")
            )

        self.assertEqual(outcome.error_code, "AI_TIMEOUT")
        output = "\n".join(logs.output)
        self.assertIn(
            "stage=network_request elapsed_ms=", output
        )
        self.assertIn("timeout_ms=60000 result=timeout", output)
        self.assertNotIn("private timeout detail", output)

    def test_current_interactions_response_without_legacy_step_status_is_accepted(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json=interaction_response(
                    provider_result("summary"), include_step_status=False
                ),
            )

        outcome = self.provider_with_handler(handler).process(
            self.content_request("summary")
        )
        self.assertIsInstance(outcome, ProviderResult)

    def test_failure_diagnostic_is_sanitized_and_metadata_only(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                503,
                json={"error": {"message": "private provider response"}},
            )

        with self.assertLogs("backend.providers.gemini", level="WARNING") as logs:
            outcome = self.provider_with_handler(handler).process(
                self.content_request("summary")
            )

        self.assertEqual(outcome.error_code, "AI_UNAVAILABLE")
        self.assertEqual(len(logs.output), 1)
        self.assertIn("error_code=AI_UNAVAILABLE", logs.output[0])
        self.assertIn("diagnostic=http_status_503", logs.output[0])
        self.assertNotIn("private provider response", logs.output[0])

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
            with self.subTest(expected=expected), self.assertLogs(
                "backend.providers.gemini", level="WARNING"
            ) as logs:
                outcome = self.provider_with_handler(handler).process(
                    self.content_request("summary")
                )
                self.assertEqual(outcome.error_code, expected)
                self.assertNotIn("private", outcome.message)
                self.assertNotIn("private", logs.output[0])

    def test_http_auth_quota_and_unavailable_failures_are_safely_mapped(self) -> None:
        for status, expected in (
            (401, "AI_AUTH_FAILED"),
            (403, "AI_AUTH_FAILED"),
            (429, "AI_RATE_LIMITED"),
            (404, "AI_UNAVAILABLE"),
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

    def test_production_auth_error_explains_required_local_startup_settings(self) -> None:
        environment = self.base_env()
        environment.pop("AUTH_MODE")
        environment.pop("API_AUTH_TOKEN")

        with self.assertRaisesRegex(
            SettingsError,
            r"production requires AUTH_MODE=token and API_AUTH_TOKEN",
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
            self.assertEqual(created.status, "failed")
            self.assertEqual(created.error_code, "AI_UNAVAILABLE")
            capture_id = created.capture_id

            for expected_retry_count in (1, 2):
                retried = service.retry(capture_id)
                self.assertEqual(retried.status, "failed")
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
