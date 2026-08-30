# P1.5 Acceptance Matrix

Evidence states are deliberately non-interchangeable:

- `AUTOMATED_PASS`: current repository automation or an isolated local drill.
- `USER_REPORTED_DEVICE_PASS`: device observation supplied by the user and not
  reproduced by Codex.
- `LIVE_SERVICE_PASS`: real provider/service evidence with sanitized records.
- `STAGING_PASS`: evidence from the exact staging deployment.
- `PRODUCTION_PENDING`: production was not deployed or accepted.
- `PENDING`, `PREPARED`, and `N/A`: evidence missing, instructions only, or not
  applicable.

| Capability / gate | Automated | Device | Live service | Staging | Production | Evidence boundary |
|---|---|---|---|---|---|---|
| Backend OFF / P1.4 fallback | `AUTOMATED_PASS` | `USER_REPORTED_DEVICE_PASS` | `N/A` | `PENDING` | `PRODUCTION_PENDING` | User reported unreachable backend -> raw/pending local note -> Obsidian -> Remotely Save; not repository-verified |
| Backend ON Mock | `AUTOMATED_PASS` | `PENDING` | `N/A` | `PENDING` | `PRODUCTION_PENDING` | Canonical iPhone runbook prepared; no device result |
| Capture/status/list/retry API | `AUTOMATED_PASS` | `PENDING` | `N/A` | `PENDING` | `PRODUCTION_PENDING` | TestClient coverage plus one real local production-mode Uvicorn Mock capture/restart/read flow |
| Auth/CORS/security headers | `AUTOMATED_PASS` | `PENDING` | `N/A` | `PENDING` | `PRODUCTION_PENDING` | Production fail-closed tests and local Uvicorn auth/CORS checks; deployed headers/rotation pending |
| Application rate limits | `AUTOMATED_PASS` | `N/A` | `N/A` | `PENDING` | `PRODUCTION_PENDING` | Single-instance production buckets tested; deployed 429 evidence pending |
| SQLite raw/state preservation | `AUTOMATED_PASS` | `PENDING` | `N/A` | `PENDING` | `PRODUCTION_PENDING` | Fictional capture ID, raw content, status and timestamps survive a real local Uvicorn process restart |
| Backup/restore | `AUTOMATED_PASS` | `N/A` | `N/A` | `PENDING` | `PRODUCTION_PENDING` | Five-record local Online Backup drill passes; staging restart/Web read pending |
| Mock processing modes | `AUTOMATED_PASS` | `PENDING` | `N/A` | `PENDING` | `N/A` | Deterministic fictional provider only |
| Gemini provider | `AUTOMATED_PASS` | `PENDING` | `PENDING` | `PENDING` | `PRODUCTION_PENDING` | Mocked transport only; no real call or credential |
| URL extraction / SSRF controls | `AUTOMATED_PASS` | `PENDING` | `PENDING` | `PENDING` | `PRODUCTION_PENDING` | DNS-rebinding residual risk remains |
| Markdown / local Obsidian delivery | `AUTOMATED_PASS` (render only) | `PENDING` | `PENDING` | `PENDING` | `PRODUCTION_PENDING` | Backend never writes the Vault; device delivery pending |
| Today / Inbox / Projects / Pending / Reports / Search | `AUTOMATED_PASS` | `PENDING` | `N/A` | `PENDING` | `PRODUCTION_PENDING` | Static and API tests only |
| PWA shell/installability | `AUTOMATED_PASS` (shell only) | `PENDING` | `N/A` | `PENDING` | `PRODUCTION_PENDING` | No device install or viewport evidence |
| Logging privacy | `AUTOMATED_PASS` | `PENDING` | `PENDING` | `PENDING` | `PRODUCTION_PENDING` | Local Uvicorn log excludes fictional token/raw marker; no deployed log sink/retention evidence |
| Render single-instance config | `AUTOMATED_PASS` (artifact) | `N/A` | `N/A` | `PENDING` | `PRODUCTION_PENDING` | Blueprint not synced; region/plan/cost require confirmation |

Current gates:

- Backend OFF fallback: `USER_REPORTED_DEVICE_PASS`
- Backend ON Mock: `PENDING`
- Live Gemini: `PENDING`
- Staging: `PENDING`
- Backup/restore staging drill: `PENDING`
- Web/PWA device: `PENDING`
- Production: `PRODUCTION_PENDING`
