# P1.5 Gemini Live Smoke Test

Status: `PREPARED` / guarded adapter implemented offline; no live service tested.
Use fictional or public-safe content only. Do not commit credentials, prompts
containing private content, provider bodies, or screenshots with secrets.

## Preconditions

- [x] Backend-OFF device fallback is accepted from user-reported evidence at the
  boundary recorded in `P1_5_DEVICE_LIVE_ACCEPTANCE_RUNBOOK.md`.
- [ ] Backend ON with `AI_PROVIDER=mock` has passed on iPhone before live AI.
- [x] The guarded adapter, strict contracts, safe error mapping, and mocked
  transport tests have been reviewed locally.
- [x] Provider model, timeout, schema parsing, safe error mapping, and logging
  controls have focused tests and review approval.
- [ ] `GEMINI_API_KEY` is stored only in the staging secret manager.
- [ ] Request/body and provider prompt/response logging are disabled.
- [ ] `APP_ENV=production`, `AUTH_MODE=token`, `AI_PROVIDER=gemini`,
  `ENABLE_LIVE_AI=true`, allowlisted `GEMINI_MODEL`, explicit
  `ALLOWED_ORIGINS`, and a disk-backed `DATABASE_URL` are configured.

Stop if any precondition is unresolved. Never add a real key to `.env`, shell
history, Git, a Shortcut note, or this evidence sheet.

## Guarded runner

### Direct Gemini diagnostic

Use the direct diagnostic before the application-level runner when a runtime
key is independently available. It calls the official Gemini Interactions API
directly; Cloudflare and the application adapter are not involved:

```text
Direct Gemini diagnostic → App adapter diagnostic → Device end-to-end
```

The command sends only the fixed fictional prompt `Reply with exactly:
GEMINI_OK`, requires the allowlisted `GEMINI_MODEL`, uses a bounded timeout, and
prints only sanitized status/category metadata. It never prints or persists a
key or response body:

```bash
.venv/bin/python -m tools.p1_5_gemini_direct_smoke
```

Transport diagnostics use content-free codes: `PROVIDER_DNS`, `PROVIDER_TLS`,
`PROVIDER_TIMEOUT`, `PROVIDER_RESET`, `PROVIDER_CONNECT`, or
`PROVIDER_NETWORK`. Invalid URL/protocol/request construction is reported as
`REQUEST/MALFORMED_REQUEST`, while provider HTTP responses retain their HTTP
status and a sanitized provider code. No exception text, headers, key, prompt,
or response body is emitted.

If `GEMINI_API_KEY` is unavailable, the command reports `LIVE CALL BLOCKED` and
does not make a network request. A direct failure must not be used to weaken
the guarded adapter or its fail-closed configuration.

`tools/p1_5_gemini_live_smoke.py` performs only the fixed cases in this file.
It accepts an exact HTTPS origin, reads `P1_5_ACCEPTANCE_TOKEN` only from the
runtime environment, rejects redirects, validates each stored result with the
strict `ProviderResult` contract, and prints content-free evidence. It cannot
set a provider, model, API key, prompt, or arbitrary payload.

After the operator has independently verified the live runtime configuration
and the Backend ON Mock gate, run the four success writes:

```bash
PYTHONPATH=src:. .venv/bin/python tools/p1_5_gemini_live_smoke.py \
  --base-url "https://replace-with-exact-staging-origin.example" \
  --confirm-four-fictional-writes
```

The command does not prove the runtime uses Gemini. Correlate each returned
`capture_id` with metadata-only provider traces and inspect the server logs.
Keep `runtime_gemini_config`, `provider_trace`, and `server_logs` pending until
that independent operator review is recorded.

## Single-capture local smoke (daily_control)

For a quick local Quick Look check, use the exact fictional payload below after
the backend has started with the guarded live configuration. Replace only the
URL and token placeholder; never paste a token into this document or shell
history. The bearer token is read from a local environment variable and is not
printed by the command.

```bash
export P1_5_ACCEPTANCE_TOKEN="<LOCAL_TOKEN_NOT_FOR_CHAT>"
curl --fail-with-body --silent --show-error \
  -H "Authorization: Bearer ${P1_5_ACCEPTANCE_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "schema_version": "1",
    "capture_type": "voice",
    "source_type": "voice_transcript",
    "raw_content": "今日主要測試每日控制台。AI 學習要完成 Gemini smoke test，英文口語五分鐘已完成，Cloud 課程未做。今日卡點係確認 AI 不會自行加入 deadline、負責人或完成狀態。下一步係檢查 structured output。",
    "requested_processing": "voice_structure",
    "record_type": "daily_control"
  }' \
  "http://127.0.0.1:8000/api/v1/capture"
unset P1_5_ACCEPTANCE_TOKEN
```

The live provider may return HTTP 202 with `status=pending` and
`error_code=PROCESSING_QUEUED`. In that case poll the authenticated
`GET /api/v1/captures/{capture_id}` endpoint every 2 seconds for at most 15
attempts. Require the terminal GET to be `status=processed`, with a non-empty
`result.markdown` (or `markdown` field), and an exactly preserved `raw_content`.
An immediate MockProvider response may still be HTTP 200. The
deterministic renderer remains responsible for the Markdown format; do not
accept invented deadlines, owners, completion states, or other unsupported
facts. This check is fictional only and is not device, staging, or production
evidence.

## Local launch and rollback

Start locally with placeholders only:

```bash
export APP_ENV=production
export AUTH_MODE=token
# Generate a local-only bearer token without printing or persisting its value.
export API_AUTH_TOKEN="$(.venv/bin/python -c 'import secrets; print(secrets.token_urlsafe(24))')"
export AI_PROVIDER=gemini
export ENABLE_LIVE_AI=true
export GEMINI_API_KEY="<SET_LOCALLY_DO_NOT_PASTE_INTO_CHAT>"
export GEMINI_MODEL="<EXISTING_ALLOWLISTED_MODEL>"
export ALLOWED_ORIGINS="http://127.0.0.1:8000"
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

The `API_AUTH_TOKEN` line is required because production mode intentionally
fails closed when token authentication is not configured. Use the same
runtime variable for the smoke request, without copying the value into this
document or printing it:

```bash
export P1_5_ACCEPTANCE_TOKEN="$API_AUTH_TOKEN"
```

Rollback is a process restart, not a code revert:

```bash
unset GEMINI_API_KEY GEMINI_MODEL P1_5_ACCEPTANCE_TOKEN API_AUTH_TOKEN
export AI_PROVIDER=mock
export ENABLE_LIVE_AI=false
```

If the live key, model, or boolean is missing/invalid, the application must
fail closed at startup. Do not retry configuration failures automatically.

## Exact fictional success cases

Send one distinct fictional request for each supported mode below. Voice must
use `capture_type=voice` and `source_type=voice_transcript`; the other three may
use `capture_type=content` and `source_type=selected_text`.

| Mode | Fictional input label | POST HTTP | `capture_id` | Terminal status | Schema valid | Raw preserved | Log review | Result |
|---|---|---:|---|---|---|---|---|---|
| `voice_structure` | FICTIONAL-LIVE-VOICE-01 | | | | | | | PENDING |
| `summary` | FICTIONAL-LIVE-SUMMARY-01 | | | | | | | PENDING |
| `recommendation` | FICTIONAL-LIVE-RECOMMEND-01 | | | | | | | PENDING |
| `short_article` | FICTIONAL-LIVE-ARTICLE-01 | | | | | | | PENDING |

For each row:

1. Require HTTP 200/202 and a `capture_id`. For HTTP 202, poll as described
   above; for HTTP 200, consume the result immediately.
2. Query `GET /api/v1/captures/{capture_id}` and confirm the provider result
   validates against `ProviderResult` for the requested mode.
3. Compare stored raw content with the original fictional input.
4. Inspect the approved log view by identifiers only. It must not contain raw
   content, source URL, Markdown, provider body, auth token, or API key.

### A. `voice_structure`

```text
今日完成 Project Alpha 嘅 CSV mapping，
下一步要測 invalid URL，
另外想到可以寫一篇 AI pricing short post。
```

Expected validated sections include `completed`, `next_actions`, and
`content_ideas`; the exact raw transcript remains separately preserved. Do not
accept invented projects or deadlines.

### B. `summary`

Supply this fictional article text directly as `selected_text`; do not fetch a
URL:

```text
Project Lantern is a fictional school workshop pilot. The team tested one CSV
mapping with synthetic records. The pilot has not been deployed. The next
review will compare invalid-row handling with the documented acceptance rules.
```

Expected: a bounded summary derived only from these sentences, with no claim of
deployment and no external facts.

### C. `recommendation`

```text
Project Cedar is fictional. The team has two prototype import paths and only
three hours for validation. One path is already covered by synthetic tests; the
other has no evidence. Recommend the smallest next validation step.
```

Expected: the exact recommendation contract sections, with risk/verification
language and no invented assignment or deadline.

### D. `short_article`

```text
Fictional source note: AI pricing comparisons are easier to review when the
author records the unit, included limits, date checked, and source link. Prices
can change, so the draft must avoid claiming that a snapshot is permanent.
```

Expected: one bounded draft based only on the supplied public-safe material.

## Controlled failure and retry

### E. Failure

Use one provider-level timeout or an approved provider-unavailable test control
while valid configuration remains loaded. Do not expose or corrupt credentials.
Separately confirm that missing/invalid live configuration fails at startup and
therefore cannot create a live capture.

1. Submit `FICTIONAL-LIVE-FAILURE-01` once.
2. Require HTTP 202 with `status=pending` and a safe code such as
   `AI_TIMEOUT`, `AI_UNAVAILABLE`, `AI_RATE_LIMITED`, or `AI_AUTH_FAILED`.
3. Query the capture and confirm raw content is exact, result/Markdown is absent,
   and no content appears in logs.
4. Remove the failure control, then call
   `POST /api/v1/captures/{capture_id}/retry` once.
5. Require HTTP 200, `status=processed`, the same `capture_id`, exact raw input,
   and `retry_count=1` in the stored record.

The fixed failure input is:

```text
FICTIONAL-LIVE-FAILURE-01: Project Harbor uses synthetic records only. Summarize the recorded validation boundary.
```

First enable an approved provider timeout/unavailable control outside the
runner, then create exactly one failure record:

```bash
PYTHONPATH=src:. .venv/bin/python tools/p1_5_gemini_live_smoke.py \
  --base-url "https://replace-with-exact-staging-origin.example" \
  --controlled-failure \
  --confirm-fictional-failure-write
```

Restore the valid provider configuration manually. Use the returned UUID for
one explicit retry; the runner never retries in the background:

```bash
PYTHONPATH=src:. .venv/bin/python tools/p1_5_gemini_live_smoke.py \
  --base-url "https://replace-with-exact-staging-origin.example" \
  --retry-capture-id "replace-with-controlled-failure-capture-uuid" \
  --confirm-manual-retry
```

Do not run success, failure, and retry phases concurrently. Do not use a
production endpoint.

| Failure evidence | Expected | Observed | Evidence reference |
|---|---|---|---|
| Initial response | HTTP 202 / pending | | |
| Safe error | `AI_TIMEOUT` or `AI_UNAVAILABLE` | | |
| Raw content | Exact fictional input retained | | |
| Log content | No user/provider/secret data | | |
| Manual retry | Same ID, processed, retry count 1 | | |

## Acceptance

Live Gemini remains `PENDING` until all five cases have user-supplied evidence.
Do not treat mock-provider output, a repository test, or a configured key as a
live-service pass.
