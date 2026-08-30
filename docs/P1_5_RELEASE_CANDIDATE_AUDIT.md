# P1.5 Release Candidate Audit

Status: `NOT ACCEPTED`. Audit scope is the current P1.5 branch. Automated and
local drill evidence is distinct from device, live-service, staging, and
production evidence.

## Severity summary

- `BLOCKER`: five required acceptance gates have no external evidence: Backend
  ON device, Live Gemini, staging persistence/security, staging backup/restore,
  and Web/PWA device UX.
- `HIGH`: none identified in the current offline implementation.
- `MEDIUM`: DNS validation/fetch race remains conditional on the final staging
  exposure model; SQLite remains single-instance only.
- `LOW`: the in-memory application limiter resets on restart and is suitable
  only for the documented single-instance staging shape.
- `INFO`: production deployment remains explicitly pending.

## Audit matrix

| Area | Current evidence | Result / residual risk |
|---|---|---|
| Architecture | FastAPI + static PWA + one SQLite store; P1.4 remains independent | `AUTOMATED_PASS` |
| Device acceptance | Backend OFF is user-reported only; Backend ON is not run | `BLOCKER / PENDING` |
| Gemini acceptance | Guarded adapter and fake transport pass; no real call | `BLOCKER / PENDING` |
| Storage | Raw/source/request fields are immutable; processed and pending records retain ID, raw, status, retry/review metadata and timestamps across a real local Uvicorn restart | `AUTOMATED_PASS` locally; staging persistence pending |
| Backup/restore | Online backup preserves five fictional records and real local Uvicorn reads the restored database by ID/list | `AUTOMATED_PASS` locally; staging/browser `BLOCKER / PENDING` |
| Authentication | Production token mode fails closed in tests and a local Uvicorn process rejects missing auth | `AUTOMATED_PASS`; staging rotation pending |
| CORS | Wildcard is rejected; local Uvicorn allows only the configured fictional origin; Blueprint requires the real exact origin | `AUTOMATED_PASS`; staging header evidence pending |
| Rate limits | Production-only buckets cover capture, retry, read, report, mutation | `AUTOMATED_PASS`; staging 429 evidence pending |
| URL / SSRF | Private/reserved targets and redirects are rejected | `MEDIUM`: DNS rebind race remains |
| Logging | Application and local Uvicorn logs exclude the fictional token/raw marker | `AUTOMATED_PASS`; deployed log sink review pending |
| Privacy | No Vault access, API response caching, analytics, or real content | `AUTOMATED_PASS` at repository boundary |
| PWA UX | Static/mobile rules pass; no iPhone viewport/install evidence | `BLOCKER / PENDING` |
| Fallback | P1.4 path unchanged; Backend OFF observed by user | `USER_REPORTED_DEVICE_PASS` only |

## Staging architecture decision

The prepared Render Blueprint is one paid Web Service, one instance, and one
persistent disk. It starts with `AI_PROVIDER=mock`, disables live AI and
auto-deploys, pins a tested Python series, generates the auth token at runtime,
and requires the exact CORS origin at setup. The selected `singapore` region and
paid plan must be confirmed for cost and data-location suitability before sync.
No Blueprint was synced by this audit.

## Medium-risk decisions

### DNS rebinding race

Conditional classification: acceptable only for an authenticated, private-use,
single-user staging acceptance with fictional/public-safe URL input. It becomes
`must-fix before public or multi-user exposure`; add pinned-DNS egress or an
outbound filtering proxy as a separate P1.5.x hardening item. Final
classification awaits real staging evidence.

### SQLite single instance

Accepted for the single-user MVP only. The Blueprint fixes `numInstances=1`
and mounts one disk. Do not horizontally scale or claim zero-downtime disk
deploys. A real local Uvicorn restart preserves processed and pending records;
a second process test serves a restored five-record database containing three
processed, one pending, and one failed record. Exact staging-disk restart,
restore, and browser evidence are still required.

## RC verdict

P1.5 release candidate is `NOT ACCEPTED`. There are no known offline
implementation HIGH issues, but all five mandatory manual/live/staging gates
must pass before the RC status can change.
