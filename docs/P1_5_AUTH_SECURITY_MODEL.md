# P1.5 Authentication and Security Model

## Decision

P1.5 is a single-user MVP with two explicit modes:

- `AUTH_MODE=dev` is allowed only when `APP_ENV` is `development` or `test` and
  the server binds to loopback.
- `AUTH_MODE=token` requires a bearer token of at least 16 characters.
  `APP_ENV=production` refuses to start in any other mode.

The repository contains only the `API_AUTH_TOKEN` variable name. A real value
must be generated and stored in the deployment platform secret manager and in
the user's private Shortcut configuration. It must not appear in Git, a note,
URL query string, screenshot, support log, or analytics event.

Live Gemini is a separate fail-closed boundary. It requires
`APP_ENV=production`, `AI_PROVIDER=gemini`, `ENABLE_LIVE_AI=true`, a runtime-only
`GEMINI_API_KEY`, and a server-side allowlisted `GEMINI_MODEL`. Test mode requires
MockProvider. Clients cannot select a provider, model, endpoint, or arbitrary
provider parameter.

## Protected surface

`GET /health` is public and returns only basic health. Every `/api/v1/*`
endpoint checks authentication, including read-only list/dashboard/project
routes. OpenAPI, Swagger UI, and ReDoc are disabled.

The static Web/PWA shell is public, but it contains no capture data. The user
enters the token into a password field; JavaScript keeps it in memory only and
does not use localStorage, sessionStorage, IndexedDB, or service-worker cache.

## Deployed single-user choice

The implemented P1.5 path uses a high-entropy single-user secret because it is
the smallest auditable contract for both iPhone Shortcuts and the Web App.
Platform access control may be added in front of the service as defense in
depth, but it must not silently replace API authentication unless Shortcuts are
proven compatible.

Magic links and OAuth are deferred: they add identity persistence, callback,
session, and recovery surfaces that are not justified for one user. If the
product expands beyond one trusted user, token auth must be replaced by a
reviewed identity/session design rather than copied per user.

## Additional controls

- Constant-time token comparison.
- Explicit CORS origins; wildcard origins are rejected.
- 128 KiB ASGI body cap, strict Pydantic models, bounded lists and strings.
- API responses use `Cache-Control: no-store`; all responses receive CSP,
  frame, referrer, and MIME-sniffing headers.
- Deployment must add HTTPS, platform rate limiting, secret rotation, database
  backups, and an incident procedure before real-data use.

Production is not accepted until the checklist in
`docs/P1_5_PRODUCTION_CHECKLIST.md` is completed with real evidence.
