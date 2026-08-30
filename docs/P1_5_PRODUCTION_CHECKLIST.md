# P1.5 Production Checklist

All items are unchecked because P1.5 has not been deployed or tested with real
credentials, Gemini, iPhone Shortcuts, Remotely Save, or a real Vault.

## Account and deployment

- [ ] Confirm current Render plan, persistent-disk, bandwidth, backup, region,
  and outbound API costs.
- [ ] Create exactly one production web service and one persistent disk.
- [ ] Pin the deployed Git commit and record the previous known-good commit.
- [ ] Configure `/health`, HTTPS, custom domain, and platform request/rate limits.
- [ ] Verify code rollback and a separate SQLite backup/restore procedure.

## Authentication and secrets

- [ ] Set `APP_ENV=production` and `AUTH_MODE=token`.
- [ ] Generate a high-entropy API token and store it only in platform secrets
  and private Shortcut configuration.
- [ ] Keep `AI_PROVIDER=mock` and `ENABLE_LIVE_AI=false` until Backend ON Mock
  passes; for approved live acceptance require `AI_PROVIDER=gemini`,
  `ENABLE_LIVE_AI=true`, allowlisted `GEMINI_MODEL`, and a secret-manager-only
  `GEMINI_API_KEY`.
- [ ] Confirm logs, support exports, screenshots, and analytics contain no token,
  key, raw capture, source URL, or provider body.
- [ ] Test secret rotation and invalid/expired token behavior.

## Database and privacy

- [ ] Point `DATABASE_URL` to the mounted disk and prove data survives restart
  and redeploy.
- [ ] Define retention, explicit deletion, incident export, and user recovery
  procedures before real-data use.
- [ ] Test a consistent SQLite backup and restore using fictional data.
- [ ] Confirm the service has no filesystem/Vault/Remotely Save access.
- [ ] Review platform region and data-processing terms for the user's actual
  jurisdiction and data class; obtain professional confirmation if required.

## Security

- [ ] Review explicit production CORS origins; no wildcard.
- [ ] Re-run SSRF, redirect-to-private-IP, payload, MIME, auth, retry, and logging
  tests against the deployment.
- [ ] Add platform egress control or a DNS-pinning outbound proxy before
  processing sensitive/untrusted URLs; current validate-then-fetch DNS has a
  documented rebinding residual risk.
- [ ] Confirm debug docs, stack traces, directory listings, and anonymous API
  access are disabled.
- [ ] Set and verify rate limits for capture, retry, list, and report routes.

## Live acceptance

- [ ] Complete a fictional-data Gemini smoke test for every processing mode and
  every documented failure code.
- [ ] Update both Shortcuts to the HTTPS endpoint without removing P1.4 fallback.
- [ ] Test backend success, backend unreachable, AI unavailable, invalid auth,
  oversized input, URL extraction failure, and local raw recovery on a real
  iPhone.
- [ ] Confirm local Obsidian creation and Remotely Save behavior on the real
  device without giving the backend Vault access.
- [ ] Test Web/PWA Today, Inbox, Projects, Pending, Reports, search, retry,
  review, project assignment, and preview at phone and desktop viewports.
- [ ] Record rollback, incident, and go/no-go evidence. Do not declare production
  ready while any required item remains unchecked.
