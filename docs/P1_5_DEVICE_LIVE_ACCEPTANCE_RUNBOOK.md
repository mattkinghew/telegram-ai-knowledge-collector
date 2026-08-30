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

## Test A — Backend ON

Use one fictional voice transcript or fictional selected text.

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

Result: `PENDING` — user must supply real-device evidence.

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

Result: `PENDING` — user must supply real-device evidence.

## Gate

Do not start live Gemini acceptance until Test B has real evidence for every
row. A successful Obsidian URI or sync notification alone is not evidence that
the note exists remotely.
