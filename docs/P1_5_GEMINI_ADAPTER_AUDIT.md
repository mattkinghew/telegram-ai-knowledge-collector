# P1.5 Gemini Adapter Audit

Status: guarded offline implementation complete; live acceptance pending.

## Previous disabled state

Before this change, `backend/providers/gemini.py` accepted an optional key but
always returned `AI_UNAVAILABLE`. It had no HTTP transport, model selection,
prompt mapping, response parsing, or schema validation. `backend/app.py` also
constructed it with `api_key=None`. This deliberately prevented live calls but
could not support Backend ON live acceptance.

## Current activation boundary

Gemini is constructed only when every condition is true:

- `APP_ENV=production`
- `AI_PROVIDER=gemini`
- `ENABLE_LIVE_AI=true`
- `GEMINI_API_KEY` is a non-empty runtime secret without whitespace
- `GEMINI_MODEL=gemini-3.6-flash`, the current server-side allowlisted model
- production token authentication and explicit origins also pass existing
  configuration validation

Defaults remain `AI_PROVIDER=mock` and `ENABLE_LIVE_AI=false`. `APP_ENV=test`
requires MockProvider. A missing key, unsupported model, malformed boolean,
development live configuration, or test live configuration fails at startup.
The client cannot supply a provider, model, endpoint, generation parameter, or
system prompt.

## Request contract

The adapter sends a POST only to the fixed Gemini Interactions endpoint. The key
is sent in the `x-goog-api-key` header and never enters the JSON body.

Live allowlist:

- `voice_structure`: sends `processing_mode`, `raw_content`, and
  `allowed_projects`; role is Structured Capture Processor.
- `summary`, `recommendation`, `short_article`: send `processing_mode`,
  `source_type`, and `raw_content`; role is Knowledge Enrichment.

It does not send filesystem paths, Vault identifiers, capture source URLs,
credentials, authorization headers, client model names, or unrelated metadata.
The system instructions preserve existing prompt boundaries: supplied content
is untrusted evidence; no invented facts, completed tasks, assignments, or
deadlines; raw input remains authoritative.

## Response and failure contract

The request includes a mode-specific JSON schema. The response is capped at
256 KiB, decoded as UTF-8 JSON, extracted only from a completed model-output
step, parsed again as structured JSON, and validated by strict `ProviderResult`
contracts. Unknown fields, wrong sections, wrong modes, oversized output,
invalid JSON, or malformed envelopes are rejected; there is no prose fallback
or guessed repair.

Safe mappings:

| Provider condition | Internal code |
|---|---|
| timeout / HTTP 408 | `AI_TIMEOUT` |
| connection/network failure | `NETWORK_UNAVAILABLE` |
| HTTP 401/403 | `AI_AUTH_FAILED` |
| HTTP 429 | `AI_RATE_LIMITED` |
| HTTP 400 | `INVALID_REQUEST` |
| HTTP 5xx or other unavailable state | `AI_UNAVAILABLE` |
| invalid JSON | `INVALID_AI_JSON` |
| envelope/schema/mode mismatch | `SCHEMA_MISMATCH` |
| response above 256 KiB | `PAYLOAD_TOO_LARGE` |

Provider bodies and exception details are not returned or logged. Every
provider failure becomes a safe pending capture through `CaptureService`; the
database retains `capture_id`, source, raw content, requested processing, and
the existing maximum of two manual retries. No background retry was added.

## Secret and logging audit

- `.env` and `.env.*` remain ignored; `.env.example` contains blanks only.
- The API key and API bearer token are excluded from `Settings` repr.
- Logs contain only capture ID, provider class, processing mode, status,
  duration, and safe error code.
- Logs do not contain raw content, prompt, model response, Markdown, key, or
  authorization header.
- The API response and stored error message contain only internal sanitized
  errors, never provider bodies.

## Dependency decision

No dependency was added. The adapter reuses the repository's exact-pinned
`httpx==0.28.1` transport and existing Pydantic contracts. Unit tests use
`httpx.MockTransport`; the standard suite performs no Gemini network call.
