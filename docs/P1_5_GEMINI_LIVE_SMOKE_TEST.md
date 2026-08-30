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

## Exact fictional success cases

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
