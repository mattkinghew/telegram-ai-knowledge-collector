# P1.5 Staging Deployment Checklist

Status: `PREPARED` / no deployment performed. Use fictional data only.

## Configuration

- [ ] Pin and record the exact Git commit; deploy one instance only.
- [ ] Set `APP_ENV=production` and `AUTH_MODE=token`.
- [ ] Generate a staging-only high-entropy `API_AUTH_TOKEN` of at least 16
  characters and store it in the platform secret manager.
- [ ] Start with `AI_PROVIDER=mock` and `ENABLE_LIVE_AI=false`; pass Backend ON
  Mock device acceptance before enabling Gemini.
- [ ] For the separate fictional Gemini smoke only, set `AI_PROVIDER=gemini`,
  `ENABLE_LIVE_AI=true`, an allowlisted `GEMINI_MODEL`, and store
  `GEMINI_API_KEY` only in the secret manager.
- [ ] Set `ALLOWED_ORIGINS` to the exact HTTPS Web/PWA origin; no wildcard.
- [ ] Attach one persistent disk/volume to the single service.
- [ ] Set `DATABASE_URL` to an absolute SQLite file on that mount.
- [ ] Confirm the service account can access only the mounted app-data path and
  has no Vault, Remotely Save, or personal filesystem access.

Record names and locations, never values:

| Item | Evidence reference |
|---|---|
| Commit / deployment ID | |
| Secret-manager entry names | |
| CORS origin | |
| Disk mount and SQLite path | |
| Platform region / plan | |

## Service and security checks

- [ ] HTTPS is enforced and `GET /health` returns HTTP 200 without content data.
- [ ] Every `/api/v1/*` route rejects missing and invalid bearer tokens.
- [ ] Valid auth works for capture, list, retry, review, and report preview.
- [ ] CORS permits only the recorded origin.
- [ ] Security headers and API `Cache-Control: no-store` are present.
- [ ] OpenAPI, Swagger UI, ReDoc, debug tracebacks, and directory listings are
  unavailable.
- [ ] Configure and record platform rate limits for capture, retry, list, and
  report routes. The application does not currently supply its own limiter.
- [ ] Confirm request-body capture is disabled and logs follow
  `P1_5_LOGGING_PRIVACY_POLICY.md`.
- [ ] Confirm secret access is restricted; rotate the staging token and verify
  the old value is rejected.

## Persistence, backup, and restore

- [ ] Create fictional captures and prove rows survive an app restart.
- [ ] Prove rows survive a code redeploy without changing the disk.
- [ ] Run `P1_5_BACKUP_RESTORE_DRILL.md` and record restore time.
- [ ] Configure backup retention and access; do not assume a platform snapshot
  is application-consistent until the drill proves recovery.

## Rollback

- [ ] Record the previous known-good commit/deployment.
- [ ] Take and verify a SQLite backup before code rollback.
- [ ] Roll back application code without assuming disk state is rolled back.
- [ ] Re-run health, auth, schema, capture/read, and raw-preservation checks.
- [ ] Document the go/no-go owner and the condition for abandoning staging.

## Result

Staging remains `PENDING` until the user supplies evidence for every required
item. This checklist does not authorize deployment, production data, or live
Gemini use.
