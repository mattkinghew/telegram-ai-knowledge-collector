# P1.5 Gemini Live Smoke Test

Status: `PREPARED` / live service not enabled or tested. Use fictional or
public-safe content only. Do not commit credentials, prompts containing private
content, provider bodies, or request/response screenshots with secrets.

## Preconditions

- [ ] The mandatory backend-OFF device test in
  `P1_5_DEVICE_LIVE_ACCEPTANCE_RUNBOOK.md` has real evidence.
- [ ] A reviewed live Gemini adapter has replaced the current fail-safe adapter.
  The current `backend/providers/gemini.py` intentionally makes no live call,
  even when `GEMINI_API_KEY` is set.
- [ ] Provider model, timeout, schema parsing, safe error mapping, and logging
  controls have focused tests and review approval.
- [ ] `GEMINI_API_KEY` is stored only in the staging secret manager.
- [ ] Request/body and provider prompt/response logging are disabled.
- [ ] `APP_ENV=production`, `AUTH_MODE=token`, `AI_PROVIDER=gemini`, explicit
  `ALLOWED_ORIGINS`, and a disk-backed `DATABASE_URL` are configured.

Stop if any precondition is unresolved. Never add a real key to `.env`, shell
history, Git, a Shortcut note, or this evidence sheet.

## Success cases

Send one distinct fictional request for each supported mode below. Voice must
use `capture_type=voice` and `source_type=voice_transcript`; the other three may
use `capture_type=content` and `source_type=selected_text`.

| Mode | Fictional input label | HTTP | `capture_id` | Status | Schema valid | Raw preserved | Log review | Result |
|---|---|---:|---|---|---|---|---|---|
| `voice_structure` | FICTIONAL-LIVE-VOICE-01 | | | | | | | PENDING |
| `summary` | FICTIONAL-LIVE-SUMMARY-01 | | | | | | | PENDING |
| `recommendation` | FICTIONAL-LIVE-RECOMMEND-01 | | | | | | | PENDING |
| `short_article` | FICTIONAL-LIVE-ARTICLE-01 | | | | | | | PENDING |

For each row:

1. Require HTTP 200, `ok=true`, `status=processed`, a `capture_id`, and non-empty
   `result.markdown`.
2. Query `GET /api/v1/captures/{capture_id}` and confirm the provider result
   validates against `ProviderResult` for the requested mode.
3. Compare stored raw content with the original fictional input.
4. Inspect the approved log view by identifiers only. It must not contain raw
   content, source URL, Markdown, provider body, auth token, or API key.

## Controlled failure and retry

Use one provider-level timeout or an approved provider-unavailable test control;
do not simulate failure by exposing or corrupting credentials.

1. Submit `FICTIONAL-LIVE-FAILURE-01` once.
2. Require HTTP 202 with `status=pending` and `error_code=AI_TIMEOUT` or
   `AI_UNAVAILABLE`.
3. Query the capture and confirm raw content is exact, result/Markdown is absent,
   and no content appears in logs.
4. Remove the failure control, then call
   `POST /api/v1/captures/{capture_id}/retry` once.
5. Require HTTP 200, `status=processed`, the same `capture_id`, exact raw input,
   and `retry_count=1` in the stored record.

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
