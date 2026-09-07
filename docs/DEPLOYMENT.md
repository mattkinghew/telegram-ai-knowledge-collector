# OB Editor V0.1 Deployment

## Current platform and architecture

The existing online deployment is a macOS LaunchAgent running one Uvicorn
FastAPI process on `127.0.0.1:8000`, exposed through the Cloudflare Named
Tunnel hostname `https://capture.lamlab.cc`. The runtime application is copied
to:

```text
~/Library/Application Support/business-knowledge-capture/runtime/app
```

SQLite is stored outside the repository under the user's Application Support
directory. The process is single-instance and uses process-local FastAPI
`BackgroundTasks`; a restart can strand a deferred capture in `pending`.

Render configuration exists only as an unsynced staging preparation artifact;
it is not the current production deployment method.

## Runtime requirements

Required variable names:

| Variable | Required | Environment | Status source |
|---|---|---|---|
| `APP_ENV` | Yes | production | LaunchAgent wrapper sets it |
| `AUTH_MODE` | Yes | production | LaunchAgent wrapper sets `token` |
| `API_AUTH_TOKEN` | Yes | production | macOS Keychain at process start |
| `AI_PROVIDER` | Yes | production | LaunchAgent wrapper sets `gemini` |
| `ENABLE_LIVE_AI` | Yes | production | LaunchAgent wrapper sets `true` |
| `GEMINI_MODEL` | Yes for live Gemini | production | LaunchAgent wrapper sets allowlisted model |
| `GEMINI_API_KEY` | Yes for live Gemini | production | macOS Keychain at process start |
| `ALLOWED_ORIGINS` | Yes | production | LaunchAgent wrapper sets explicit origins |
| `DATABASE_URL` | Yes | production | LaunchAgent wrapper sets SQLite path |

Secret values are intentionally not documented.

Current local audit status (2026-09-07): value-suppressed Keychain presence
checks returned `missing_or_unknown` for both `API_AUTH_TOKEN` and
`GEMINI_API_KEY`. No secret value was read or printed. Authenticated deployment
and Gemini smoke testing must wait until the operator confirms both items exist
in the login Keychain.

## Update procedure

1. Run local tests and record the exact commit.
2. Confirm the working tree contains no secret, `.env`, `.venv`, or
   `*.egg-info` file staged for deployment.
3. Back up the installed `backend/` and `web/` runtime directories and record
   the previous commit/runtime checksum outside Git.
4. From the repository, run the existing operator installer:

   ```sh
   "$HOME/Library/Application Support/business-knowledge-capture/install-p1-5-runtime.sh"
   ```

   It copies only `backend/` and `web/` and does not copy `.git`, `.env`, data,
   or `.venv`.
5. Restart the existing service:

   ```sh
   /bin/launchctl kickstart -k "gui/$(id -u)/com.business-knowledge-capture.p1-5.backend"
   ```

6. Verify `/health`, unauthenticated 401, then run the bounded fictional
   authenticated smoke test. Do not use personal, company, Vault, or Obsidian
   content.

## Rollback

Stop the LaunchAgent, restore the backed-up runtime `backend/` and `web/`
directories, then restart the same LaunchAgent and repeat health, auth, GET,
and fictional capture checks. Code rollback does not roll back SQLite data;
restore SQLite only from a separately verified application-consistent backup.

The current runtime installer has no built-in version manifest. Until a commit
and runtime checksum are recorded, rollback is operator-managed and the exact
previous runtime must be preserved before update.

## Troubleshooting

- Health 200 but API 401: expected without the private bearer token.
- Service not running: inspect `launchctl print` and the LaunchAgent stderr log;
  missing Keychain items must fail closed.
- Capture stays `pending` after restart: this is the documented process-local
  `BackgroundTasks` limitation; recover the raw capture with GET and use the
  bounded manual retry path.
- POST processing failure returns HTTP 500 with a JSON `failed` body. Confirm
  iPhone Shortcut handling in real-device acceptance before changing this
  contract.
