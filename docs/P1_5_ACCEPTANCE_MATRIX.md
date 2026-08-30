# P1.5 Acceptance Matrix

Evidence states are `VERIFIED` (current repository automation),
`USER_REPORTED PASS` (device observation supplied by the user but not reproduced
by Codex), `PREPARED` (runbook/checklist only), `PENDING` (real evidence
required), and `N/A`.

| Capability / gate | Automated | Device | Live service | Staging | Production | Evidence boundary |
|---|---|---|---|---|---|---|
| Backend OFF fallback / P1.4 local fallback | VERIFIED | USER_REPORTED PASS | N/A | PENDING | PENDING | User reported backend unreachable → raw/pending local note → Obsidian write → Remotely Save; not repository-verified |
| Backend ON Mock | VERIFIED | PENDING | N/A | PENDING | PENDING | Exact iPhone MockProvider flow remains manual |
| Capture/status/list/retry API | VERIFIED | PENDING | N/A | PENDING | PENDING | Local TestClient only |
| Strict request/payload validation | VERIFIED | PENDING | N/A | PENDING | PENDING | 128 KiB request and bounded fields covered locally |
| SQLite state/raw preservation | VERIFIED | PENDING | N/A | PENDING | PENDING | Local tests; backup/restore drill only PREPARED |
| Mock processing modes | VERIFIED | PENDING | N/A | PENDING | N/A | Deterministic fictional provider only |
| Gemini provider | VERIFIED (offline mocked transport) | PENDING | PENDING | PENDING | PENDING | Guarded adapter implemented; no real Gemini call or credential used |
| URL extraction / SSRF controls | VERIFIED | PENDING | PENDING | PENDING | PENDING | Local fake transport; DNS-rebinding residual risk remains |
| Markdown and local Obsidian delivery | VERIFIED (rendering only) | PENDING | PENDING | PENDING | PENDING | Backend never writes the Vault; device delivery pending |
| Shortcut backend/fallback flow | PREPARED | USER_REPORTED PASS (OFF only) | PENDING | PENDING | PENDING | Backend ON Mock remains pending |
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

Current manual gate state:

- Backend OFF fallback: `USER_REPORTED PASS`
- Backend ON Mock: `PENDING`
- Live Gemini: `PENDING`
- Staging: `PENDING`
