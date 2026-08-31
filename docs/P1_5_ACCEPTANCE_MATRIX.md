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
| Backend ON Mock | `AUTOMATED_PASS` | `PENDING` | `N/A` | `PENDING` | `PRODUCTION_PENDING` | Canonical Voice Flash and Content Capture iPhone runbook prepared; no device result |
| Capture/status/list/retry API | `AUTOMATED_PASS` | `PENDING` | `N/A` | `PENDING` | `PRODUCTION_PENDING` | Real local Uvicorn flow passes; HTTPS-only sanitized staging runner is `PREPARED` but not externally executed |
| Auth/CORS/security headers | `AUTOMATED_PASS` | `PENDING` | `N/A` | `PENDING` | `PRODUCTION_PENDING` | Production fail-closed tests and local Uvicorn auth/CORS checks; deployed headers/rotation pending |
| Application rate limits | `AUTOMATED_PASS` | `N/A` | `N/A` | `PENDING` | `PRODUCTION_PENDING` | Single-instance production buckets tested; deployed 429 evidence pending |
| SQLite raw/state preservation | `AUTOMATED_PASS` | `PENDING` | `N/A` | `PENDING` | `PRODUCTION_PENDING` | Processed and pending records preserve ID, raw content, status, retry/review metadata and timestamps across a real local Uvicorn restart |
| Backup/restore | `AUTOMATED_PASS` | `N/A` | `N/A` | `PENDING` | `PRODUCTION_PENDING` | Five-record local Online Backup/restore passes and the restored DB is readable through real local Uvicorn; staging restart/browser evidence pending |
| Mock processing modes | `AUTOMATED_PASS` | `PENDING` | `N/A` | `PENDING` | `N/A` | Deterministic fictional provider only |
| Gemini provider | `AUTOMATED_PASS` | `PENDING` | `PENDING` | `PENDING` | `PRODUCTION_PENDING` | Adapter plus guarded four-mode/failure/manual-retry runners pass fake-transport contracts only; no real call or credential |
| URL extraction / SSRF controls | `AUTOMATED_PASS` | `PENDING` | `PENDING` | `PENDING` | `PRODUCTION_PENDING` | DNS-rebinding residual risk remains |
| Markdown / local Obsidian delivery | `AUTOMATED_PASS` (render only) | `PENDING` | `PENDING` | `PENDING` | `PRODUCTION_PENDING` | Backend never writes the Vault; device delivery pending |
| Today / Inbox / Projects / Pending / Reports / Search | `AUTOMATED_PASS` | `PENDING` | `N/A` | `PENDING` | `PRODUCTION_PENDING` | Real local Uvicorn verifies backing APIs; static tests cover the shell/helpers; no browser or device evidence |
| PWA shell/installability | `AUTOMATED_PASS` (shell only) | `PENDING` | `N/A` | `PENDING` | `PRODUCTION_PENDING` | No device install or viewport evidence |
| Logging privacy | `AUTOMATED_PASS` | `PENDING` | `PENDING` | `PENDING` | `PRODUCTION_PENDING` | Local Uvicorn log excludes fictional token/raw marker; no deployed log sink/retention evidence |
| Render single-instance config | `AUTOMATED_PASS` (artifact) | `N/A` | `N/A` | `PENDING` | `PRODUCTION_PENDING` | Current official field/plan/disk/Python docs rechecked 2026-08-31; Blueprint not synced and region/cost/account require confirmation |

Current gates:

- Backend OFF fallback: `USER_REPORTED_DEVICE_PASS`
- Backend ON Mock: `PENDING`
- Live Gemini: `PENDING`
- Staging: `PENDING`
- Backup/restore staging drill: `PENDING`
- Web/PWA device: `PENDING`
- Production: `PRODUCTION_PENDING`
