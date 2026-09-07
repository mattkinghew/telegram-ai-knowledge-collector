# OB Editor V0.1 — Canonical Capture API

## Authentication and limits

`POST /api/v1/capture` and `GET /api/v1/captures/{id}` require the configured
Bearer authentication. The body limit is 128 KiB; request and field limits are
defined by the existing strict `CaptureRequest` model.

## POST capture

`POST /api/v1/capture` accepts the existing schema-version-1 request. On
acceptance, the raw request is persisted before processing.

```json
{"id":"<uuid>","status":"pending"}
```

The response may already be `processed` when synchronous processing completes,
or `pending` when processing is deferred. It never exposes provider-specific
queue codes.

## GET capture status

`GET /api/v1/captures/{id}` returns the persisted capture state:

```json
{"id":"<uuid>","status":"processing"}
```

For `processed`, `result` is required:

```json
{"id":"<uuid>","status":"processed","result":{}}
```

For `failed`, `error` is required and bounded:

```json
{"id":"<uuid>","status":"failed","error":{"code":"AI_TIMEOUT","message":"AI processing timed out — capture was saved."}}
```

The single-record status response also includes `raw_content` as the recovery
field. It is retained for all states and is never replaced by AI output.
Non-processed responses do not include `result`.

Unknown IDs return HTTP 404 with `{ "error": { "code": "NOT_FOUND", ... } }`.
Validation, auth, rate-limit, and body-limit errors use the existing HTTP error
boundary and are not processing states.

## State semantics

```text
pending -> processing -> processed
                    \-> failed
```

`pending` means accepted but not started; `processing` means provider or
extraction work is active; `processed` means validated result and Markdown are
persisted; `failed` means processing ended with a useful sanitized error while
raw input remains recoverable.
