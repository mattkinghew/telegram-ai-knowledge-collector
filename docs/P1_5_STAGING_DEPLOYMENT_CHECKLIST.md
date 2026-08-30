# P1.5 Staging Deployment Checklist

Status: `PREPARED` / no deployment performed. Use fictional data only.

The reviewed starting artifact is `deploy/render-staging.yaml`. It disables
auto-deploys, fixes one instance, attaches one disk, starts with MockProvider,
and leaves the exact CORS origin for operator input. Synchronizing the Blueprint
creates paid external resources and requires separate user authorization.

## Configuration

- [ ] Confirm the Blueprint's `singapore` region, `0.5c-512mb` paid plan, disk
  size, current cost, and data-location suitability before any sync.
- [ ] Pin and record the exact Git commit and remotely available branch; deploy
  one instance only. Do not deploy an unpushed local commit.
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

After the first MockProvider boot, run the repository smoke runner. It creates
exactly two fixed fictional records (one processed voice capture and one
pending video reference). The token is read only from
`P1_5_ACCEPTANCE_TOKEN`; never pass it as a command argument, save it in a
shell script, or commit the JSON output.

```bash
# Set P1_5_ACCEPTANCE_TOKEN in the current shell using a non-echoing secret
# injection method, then run explicitly:
PYTHONPATH=src python3 tools/p1_5_staging_smoke.py \
  --base-url https://STAGING_HOST \
  --expected-origin https://STAGING_WEB_ORIGIN \
  --confirm-fictional-write
```

The runner requires exact HTTPS origins, rejects redirects, uses no arbitrary
provider/model/payload input, and returns sanitized JSON. It verifies health,
missing/invalid auth, capture/get/list/retry/review, Today, Projects, Pending,
Reports, CORS, security headers, disabled API docs, and the Web shell. Retain
the opaque IDs/timestamps outside Git for the restart check. Its
`operator_checks_pending` field deliberately leaves runtime config, server
logs, restart/disk persistence, rate limits, device behavior, and P1.4 fallback
for separate human/platform evidence.

- [ ] HTTPS is enforced and `GET /health` returns HTTP 200 without content data.
- [ ] Every `/api/v1/*` route rejects missing and invalid bearer tokens.
- [ ] Valid auth works for capture, list, retry, review, and report preview.
- [ ] CORS permits only the recorded origin.
- [ ] Security headers and API `Cache-Control: no-store` are present.
- [ ] OpenAPI, Swagger UI, ReDoc, debug tracebacks, and directory listings are
  unavailable.
- [ ] Prove application 429 behavior for capture (30/min), retry (10/min),
  read/list (120/min), report (10/min), and other mutation (30/min). Render DDoS
  protection is not a substitute for these application limits.
- [ ] Confirm request-body capture is disabled and logs follow
  `P1_5_LOGGING_PRIVACY_POLICY.md`.
- [ ] Confirm secret access is restricted; rotate the staging token and verify
  the old value is rejected.

## Persistence, backup, and restore

- [ ] Create at least three processed, one pending, and one failed fictional
  capture and prove all rows survive an app restart.
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
item. The smoke runner is prepared but has not been run against an external
service. This checklist and tool do not authorize deployment, production data,
or live Gemini use.
