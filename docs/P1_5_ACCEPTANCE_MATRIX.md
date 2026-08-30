# P1.5 Acceptance Matrix

Evidence states are `VERIFIED` (current repository automation), `PREPARED`
(runbook/checklist only), `PENDING` (real evidence required), and `N/A`.
No device, live-service, staging, or production item is passed by this document.

| Capability / gate | Automated | Device | Live service | Staging | Production | Evidence boundary |
|---|---|---|---|---|---|---|
| P1.4 local fallback | VERIFIED | PENDING | PENDING | PENDING | PENDING | Offline contract only; Backend-OFF test required before Gemini |
| Capture/status/list/retry API | VERIFIED | PENDING | N/A | PENDING | PENDING | Local TestClient only |
| Strict request/payload validation | VERIFIED | PENDING | N/A | PENDING | PENDING | 128 KiB request and bounded fields covered locally |
| SQLite state/raw preservation | VERIFIED | PENDING | N/A | PENDING | PENDING | Local tests; backup/restore drill only PREPARED |
| Mock processing modes | VERIFIED | PENDING | N/A | PENDING | N/A | Deterministic fictional provider only |
| Gemini provider | VERIFIED (fail-safe boundary) | PENDING | PENDING | PENDING | PENDING | Live adapter/calls remain disabled; smoke pack PREPARED |
| URL extraction / SSRF controls | VERIFIED | PENDING | PENDING | PENDING | PENDING | Local fake transport; DNS-rebinding residual risk remains |
| Markdown and local Obsidian delivery | VERIFIED (rendering only) | PENDING | PENDING | PENDING | PENDING | Backend never writes the Vault; device delivery pending |
| Shortcut backend/fallback flow | PREPARED | PENDING | PENDING | PENDING | PENDING | ON/OFF runbook created; no real Shortcut evidence |
| Today / Inbox / Projects / Pending / Reports | VERIFIED | PENDING | N/A | PENDING | PENDING | Static/API tests only; iPhone pack PREPARED |
| Search/review/retry/report preview | VERIFIED | PENDING | N/A | PENDING | PENDING | No real-browser or deployed evidence |
| PWA shell/installability | VERIFIED (shell only) | PENDING | N/A | PENDING | PENDING | No device install or viewport evidence |
| Auth/CORS/security headers | VERIFIED | PENDING | N/A | PENDING | PENDING | Production fail-closed config covered locally |
| Logging privacy | VERIFIED (local tests) | PENDING | PENDING | PENDING | PENDING | No deployed log sink/retention evidence |
| Persistent deployment/rollback | PREPARED | N/A | N/A | PENDING | PENDING | Staging checklist only; no service created |
| Backup/restore | PREPARED | N/A | N/A | PENDING | PENDING | Drill instructions only; restore not executed |

Manual evidence must include the exact commit/deployment, UTC time, observed
result, and a safe evidence reference. Do not store tokens, raw private data,
Vault paths, account identifiers, or confidential screenshots in Git.
