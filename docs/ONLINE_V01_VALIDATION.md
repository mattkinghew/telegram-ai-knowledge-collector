# OB Editor V0.1 Online Validation

Status: `PARTIAL / BLOCKED BEFORE DEPLOYMENT`

## Environment

| Environment | Entry point | Runtime | Persistence | AI |
|---|---|---|---|---|
| Local | `http://127.0.0.1:8000` | FastAPI/Uvicorn from worktree | SQLite | MockProvider/fakes in tests |
| Online | `https://capture.lamlab.cc` | macOS LaunchAgent + Uvicorn through Cloudflare Named Tunnel | Application Support SQLite | Existing runtime is configured for Gemini |

## Current evidence

| Check | Result | Evidence |
|---|---|---|
| Existing platform identified | MATCH | LaunchAgent, Cloudflare hostname, runtime wrapper |
| `/health` reachable | MATCH | HTTP 200, `{"ok":true,"status":"healthy"}` |
| Anonymous API rejected | MATCH | `GET /api/v1/captures` returns HTTP 401 |
| Local stabilized backend | MATCH | 37/37 V0.1/API acceptance tests |
| Online runtime equals worktree | DIFFERENT before update | Installed `captures.py` and `services/capture.py` differ |
| Exact deployed commit | NOT VERIFIED | Runtime has no commit manifest |
| Authenticated online POST/GET | NOT VERIFIED | Pending checkpoint and bounded fictional smoke |
| Raw recovery online | NOT VERIFIED | Requires authenticated fictional capture |
| Failure injection online | NOT VERIFIED | No safe public fixture; automated fake tests cover it |
| Production token / Gemini Keychain items | BLOCKED | Both required items returned missing_or_unknown in a value-suppressed presence check |
| Git checkpoint | BLOCKED | Sandbox rejected `.git/index.lock` creation; no commit was made |

## Contract comparison

The local stabilized contract is the reference in `docs/API_CONTRACT.md` and
`docs/SHORTCUT_COMPATIBILITY.md`: only `pending`, `processing`, `processed`, and
`failed`; canonical `id`; compatibility `capture_id`; `result` only when
processed; `error` only when failed; unknown ID HTTP 404. These fields cannot
be claimed online until the updated runtime is restarted and authenticated
POST/GET evidence is recorded. The existing runtime must not be restarted or
overwritten while the required Keychain items are unavailable.

## Persistence risk

SQLite is outside the repository and therefore can survive a code-only runtime
copy, but this has not yet been proven by an online restart/redeploy drill.
FastAPI `BackgroundTasks` is process-local: a restart can leave a deferred row
permanently `pending`. No new queue system is introduced in V0.1.

## Failure behaviour

No production debug endpoint or failure injection was added. Online failure
injection remains `NOT VERIFIED`; fake-provider tests are the safe evidence for
AI failure, malformed result, and timeout. Current processing failures are
documented as HTTP 500 plus a JSON `failed` body, while GET of a persisted
failed capture is HTTP 200.
