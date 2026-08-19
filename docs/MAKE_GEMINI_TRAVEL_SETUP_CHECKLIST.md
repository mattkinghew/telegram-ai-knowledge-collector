# Make + Gemini Travel Setup Checklist

This is an implementation map, not evidence of a live service. Use placeholders and approved Make/Gemini connections only. Never store credentials, private webhook URLs, or client data in Git.

## Module 1 — Custom Webhook

- Module: Make Custom Webhook at `[MAKE_WEBHOOK_URL]`.
- Field mapping: accept exactly the V3 request schema fields.
- Input: one JSON request; maximum Raw Content 50,000 characters.
- Output: unmodified request for validation.
- Error handling: reject missing, extra, oversized, credential-bearing URL, or invalid enum fields as `INVALID_REQUEST`.
- Expected test payload: `tests/fixtures/travel_ai/01_article_summary.json` → `request`.
- Expected response: validated request object only; no provider call on failure.

## Module 2 — JSON Schema Validation

- Module: JSON parse/validation using `mobile-insight-request-v3.schema.json`.
- Field mapping: all request fields; `related_project` remains allowlist-constrained later.
- Input: Module 1 output.
- Output: validated V3 object.
- Error handling: HTTP 400, `INVALID_REQUEST`, `quick_save_available: true`.
- Expected test payload: the same fictional article request.
- Expected response: schema version `3`, requested output `summary`.

## Module 3 — Gemini Structured Output

- Module: approved Gemini connection with JSON structured output.
- Field mapping: pass the validated fields to `gemini-mobile-enrichment-v3.md`; never append fetched URL/file content.
- Input: Module 2 output.
- Output: exactly the V3 `enrichment_result` keys.
- Error handling: timeout → `AI_TIMEOUT`; network/provider error → `AI_UNAVAILABLE`; do not return partial prose.
- Expected test payload: `04_short_article.json` for mode-specific output.
- Expected response: `short_article_draft` begins `AI draft`; other modes return null for that field.

## Module 4 — Response Parse and Validation

- Module: strict JSON parse plus `mobile-insight-response-v3.schema.json` validation.
- Field mapping: wrap the model result in `ok`, `schema_version`, `result`.
- Input: untrusted complete provider output plus request allowlist and requested output.
- Output: one success envelope.
- Error handling: invalid JSON → `INVALID_AI_JSON`; unknown field/bound/project mismatch → `SCHEMA_MISMATCH`; never repair by guessing.
- Expected test payload: `10_invalid_json.json` and `11_schema_mismatch.json`.
- Expected response: safe failure with `quick_save_available: true` and no raw provider prose.

## Module 5 — Webhook Response

- Module: one synchronous JSON response.
- Field mapping: success or common failure only.
- Input: Module 4 validated envelope/error.
- Output: HTTP 200 success; 400 invalid request; 422 schema mismatch; 502 unavailable/invalid JSON; 504 timeout.
- Error handling: generic `INTERNAL_ERROR` if no safer code applies.
- Expected test payload: `12_offline_fallback.json` represents the client fallback, not a live call.
- Expected response: bounded message, no stack trace, module ID, connection ID, request content, or credential.

## Device wiring checklist

- Configure webhook URL/token privately on the device.
- AI is opt-in and only for content permitted to leave the device.
- On every failure show `保存原始筆記 / 重試 / 取消`.
- Run live AI tests separately from offline/device capture acceptance.
