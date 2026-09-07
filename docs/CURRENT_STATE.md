# OB Editor V0.1 — Current State

## Architecture

FastAPI composes authenticated capture routes, an in-memory production rate
limiter, a request-body limit middleware, `CaptureService`, a SQLite
`CaptureStore`, a URL extractor, and a provider abstraction. The default test
and local provider is deterministic `MockProvider`; live Gemini is explicitly
production-only. The Web/PWA is served by the same process, while Obsidian
writing remains Shortcut-side.

Flow:

```text
iPhone Shortcut -> POST /api/v1/capture -> SQLite pending row
                -> CaptureService -> URLExtractor (when needed)
                -> MockProvider or GeminiProvider -> SQLite result/failure
                -> GET /api/v1/captures/{id}
```

## Capture endpoints

- `POST /api/v1/capture`: validate, persist, and process synchronously for
  mock/local mode; production Gemini returns a queued response and schedules
  background processing.
- `GET /api/v1/captures/{capture_id}`: retrieve one record, including raw
  content and derived result when processed.
- `GET /api/v1/captures`: bounded list with status and metadata filters; raw
  content and derived result are omitted.
- `POST /api/v1/captures/{capture_id}/retry`: bounded manual retry.
- `PATCH /api/v1/captures/{capture_id}` and
  `POST /api/v1/captures/{capture_id}/dismiss`: review operations.

All non-health routes require configured authentication.

## Current request schema

`POST /api/v1/capture` accepts strict JSON schema version `"1"`:

- Required: `schema_version`, `capture_type` (`voice|content`),
  `source_type`, `raw_content`, `requested_processing`.
- Optional: `source`, `record_type` (default `free`),
  `allowed_projects` (default `[]`, max 8).
- Raw content is normalized only for line endings and bounded to 50,000
  characters. Unknown fields and incompatible source/mode combinations fail
  validation.

## Current response and state machine

The internal `CaptureResponse` is:

```json
{"ok": true, "capture_id": "uuid", "status": "processed", "result": {}, "error_code": null, "message": null}
```

Unsuccessful responses use `ok: false`, `capture_id`, `status`, `result: null`,
`error_code`, and `message`. The declared status literals are `pending`,
`processing`, `processed`, and `failed`.

In practice, provider failures, URL extraction failures, missing source
content, malformed provider JSON, schema mismatch, and provider timeouts are
currently persisted as `pending` (except unexpected exceptions, which are
`failed`). `PROCESSING_QUEUED` is also exposed as an error code for a queued
background task. This does not match the requested canonical state semantics.

## AI and timeout behaviour

`CaptureService._process` calls the provider after marking the row
`processing`. `GeminiProvider` performs the model call through a bounded
HTTPX transport. It has separate connect/read/write/pool limits and a bounded
response body. `AI_TIMEOUT`, network, authentication, quota, invalid JSON,
schema mismatch, and oversized response failures are sanitized before being
returned. URL extraction separately applies bounded public-URL validation and
transport limits.

## Persistence and recovery

`CaptureStore.create()` inserts the complete request, including exact
`raw_content`, into SQLite before any provider or extractor call. Failure
updates clear only derived `result_json` and `markdown`; they do not clear
`raw_content`. Therefore raw input is recoverable after processing failure via
the stored record and the current single-record GET endpoint. This is the
correct reliability boundary and needs no new database or infrastructure.

## Existing tests and known issues

The repository contains backend contract, service, API, Gemini adapter,
failure-preservation, URL-security, operations, restart, and Web/PWA tests.
The baseline run was 539 tests: 537 passed and 2 process-restart tests were
blocked by the sandbox's prohibition on binding a localhost socket.

Known V0.1 issues:

1. Client-visible response shape is not the requested deterministic
   `id/status/result/error` envelope.
2. `pending` is used as a failure state, obscuring retryable processing
   failures.
3. Queued background processing exposes an internal `PROCESSING_QUEUED`
   error code and is not represented consistently by GET.
4. Capture state-machine coverage does not explicitly prove malformed AI,
   timeout, unknown ID, and raw recovery as one API contract.
5. FastAPI `BackgroundTasks` is process-local; a process crash after the
   acknowledgement can leave a persisted `pending` row requiring recovery or
   retry. No workflow engine is currently present.
