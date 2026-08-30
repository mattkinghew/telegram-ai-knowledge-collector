# P1.5 Device and Live Acceptance Runbook

Status: `PREPARED` / real-device evidence pending. Use fictional input only.
Do not record tokens, Vault names/paths, account names, or private screenshots.

## Preconditions

- [ ] Run the repository validation suite against the exact commit under test.
- [ ] Build both backend-aware Shortcuts without removing the P1.4 local branch.
- [ ] Use an HTTPS backend for device testing and store its bearer token only in
  the private Shortcut configuration.
- [ ] Enable Remotely Save on the test device and identify a fictional test note.
- [ ] Record device/iOS, Shortcut version, backend commit, endpoint host, and UTC
  test time below. Do not record secret values.

| Evidence | Record |
|---|---|
| Device / iOS | |
| Shortcut / version | |
| Backend commit | |
| Endpoint host | |
| Test time (UTC) | |

## Test A — Backend ON with MockProvider

Set `AI_PROVIDER=mock` and keep `ENABLE_LIVE_AI=false`. Reuse the exact
fictional payload from the accepted Backend-OFF session if that payload is
still available outside Git. If it was not retained, create one fictional
payload and repeat both ON and OFF paths with it; do not invent the earlier
payload in this document.

```text
iPhone Shortcut -> P1.5 backend -> processed response -> Markdown
                -> Obsidian -> Remotely Save
```

1. Start the accepted backend and confirm `GET /health` returns HTTP 200.
2. Run the matching Shortcut once and save the returned Markdown.
3. Record the HTTP result and `capture_id`; never record the bearer token.
4. Query `GET /api/v1/captures/{capture_id}` and compare the stored fictional
   raw input with the original input.
5. Confirm one local Obsidian note exists, then separately observe the same
   note after Remotely Save completes.

| Acceptance item | Expected | Observed | Evidence reference |
|---|---|---|---|
| Shortcut request sent | One request | | |
| API response | HTTP 2xx | | |
| Capture identifier | Non-empty opaque `capture_id` | | |
| Processing | `status = processed` | | |
| Markdown | Non-empty and visibly rendered | | |
| Local note | Exactly one note created | | |
| Remotely Save | Same note observed remotely | | |
| Raw preservation | Exact fictional input retained | | |
| Duplicate | No duplicate request or note | | |

Result: `PENDING` — Backend ON Mock requires user-supplied real-device evidence.

## Test B — Backend OFF (mandatory before live Gemini)

Repeat the exact fictional input used in Test A. Stop only the test backend; do
not disable the Shortcut's P1.4 local fallback.

```text
Shortcut -> backend unreachable -> P1.4 local fallback
         -> ai_status: pending / raw -> Obsidian
```

1. Stop the backend and confirm the test endpoint is unreachable.
2. Run that same fictional capture once. Do not manually repeat it after the
   failure.
3. Confirm the Shortcut takes its local fallback branch without looping.
4. Confirm exactly one local note contains the complete original input and
   `ai_status: pending` for requested processing, or the documented raw status.
5. Restore connectivity and separately observe Remotely Save for that note.

| Acceptance item | Expected | Observed | Evidence reference |
|---|---|---|---|
| Fallback | Triggered after bounded request failure | | |
| Local note | Exactly one note created | | |
| Raw preservation | Exact fictional input retained | | |
| Duplicate | No second note/request side effect | | |
| Stability | No crash or retry loop | | |
| Delayed sync | Same note observed after connectivity returns | | |

Result: `USER_REPORTED PASS`.

Evidence boundary: the user reported observing the following device flow:

```text
backend unreachable -> P1.4 local fallback -> raw/pending note
                    -> local Obsidian write -> Remotely Save observed by user
```

This is user-reported device evidence. It was not reproduced by repository
automation or Codex, and no timing, screenshot, device detail, or earlier
fictional payload is inferred. The table remains blank unless the user supplies
sanitized row-level evidence.

## Gate

Backend OFF has user-reported acceptance at the boundary above. Prove Test A
with MockProvider before starting live Gemini. A successful Obsidian URI or sync
notification alone is not evidence that the note exists remotely.
