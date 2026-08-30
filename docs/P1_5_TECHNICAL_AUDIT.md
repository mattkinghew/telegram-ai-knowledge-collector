# P1.5 Technical Audit

Audit date: 2026-08-31. Scope: P1.4 baseline `2430802` through the current P1.5
branch. Evidence is local/offline only.

## Severity result

- BLOCKER: 0 open.
- HIGH: 0 open.
- MEDIUM: 2 accepted offline residual risks.
- LOW: 3 evidence/operability limitations.
- INFO: live/device/production acceptance remains pending.

## Architecture

FastAPI routes, capture orchestration, provider adapters, bounded extraction,
SQLite storage, security middleware, Markdown/report services, and a static
ES-module Web/PWA have explicit boundaries. The backend does not import or call
the existing Vault CLI. P1.4 remains independently usable.

## API

Version-1 request and provider models are strict and reject extra fields,
incompatible modes, credential-bearing URLs, filesystem paths, oversized
strings, duplicate projects, and arbitrary nested provider data. Capture,
status, paginated list, bounded retry, review, project, dashboard, dismiss, and
report-preview routes have tests. No DELETE route exists.

## Storage

All data values use parameterized SQLite queries. Status and ordering fragments
are internal constants. Raw/source/request fields are never updated. Results,
Markdown, errors, retry metadata, and review metadata are separate. There is no
automatic deletion or cleanup.

## AI boundary

Standard tests use `MockProvider` or HTTPX MockTransport. The guarded Gemini
adapter has a fixed endpoint, server-side model allowlist, production-only
triple opt-in, minimal mode-specific request mapping, 20-second timeout,
256 KiB response cap, strict structured validation, and sanitized failures.
Provider output is revalidated before storage and Markdown rendering. No key is
persisted and no real Gemini call was made; live acceptance remains pending.

## URL security

HTTP/HTTPS only; credentials, malformed URLs, localhost, loopback, private,
link-local, metadata, multicast, reserved, unspecified, mixed public/private
DNS, unsafe schemes, and private redirects are rejected. Redirect count,
timeouts, response bytes, MIME, and extracted characters are bounded. HTML is
parsed without a browser and scripts/styles/navigation/footer are excluded.

**MEDIUM — DNS validation/fetch race:** the resolver check and HTTPX connection
perform separate resolution, so a hostile DNS service could theoretically
rebind between them. P1.5 is not deployed; the production checklist requires a
DNS-pinning outbound proxy or platform egress control before sensitive/untrusted
URL processing. This does not weaken the current offline fixture validation.

## Auth

Production refuses `AUTH_MODE=dev`; token mode requires a bounded secret and
uses constant-time comparison. All API routes except minimal `/health` require
auth. Static shell contains no data. OpenAPI/docs are disabled. CORS rejects
wildcards and uses explicit origins. Production-only fixed-window buckets limit
capture, retry, read/list, report, and mutation routes. Authorized and
unauthorized counters are separate; 429 responses retain no-store and security
headers. The limiter is deliberately single-process and resets on restart.

## Privacy

Logs are metadata-only and tested against raw/source/token leakage. API content
is no-store. The service has no Vault or Remotely Save integration. No real
data, credentials, webhook, Gemini call, or external upload was used. PWA caches
only its shell.

## Offline fallback

Backend failure is explicitly mapped to the unchanged P1.4 local raw/pending
builder in both current Shortcut sheets. Backend OFF is accepted only as
user-reported device evidence; Backend ON Mock and live Gemini remain pending.

## Web App

Five primary pages, bounded search/filtering, human review/assignment/retry,
pending dismissal without raw deletion, and report preview are implemented.
DOM creation uses `textContent`; no `innerHTML`, token persistence, API caching,
delete, send, or publish behavior exists. CSS includes 44 px controls and mobile
breakpoints.

**LOW — visual evidence:** browser automation is explicitly out of scope, so
real viewport, focus order, screen-reader, installability, and device latency
remain manual acceptance items.

## Testing

The earlier exact committed baseline was 461 Python tests. Guarded Gemini added
15 tests; final acceptance preparation adds four tests for rate limits and the
sanitized backup/restore drill. The full local suite passes 480 Python tests;
four Node Web helper tests also pass. Compile, CLI, readiness, JSON, Markdown,
privacy, security, and diff checks passed against the current worktree.

## Dependencies

- Required runtime: FastAPI 0.123.9, HTTPX 0.28.1, Uvicorn 0.36.1.
- Development/test: FastAPI TestClient uses the required HTTPX dependency; Node
  built-in test runner adds no package.
- Standard library: SQLite, HTML parsing, URL/IP/DNS handling, UUID, JSON,
  logging, and timestamps.
- Unnecessary/excluded: ORM, React/Next, browser automation, scraper, Docker,
  OCR, RAG/vector/agent packages.

**LOW — pinned aging:** pins preserve Python 3.9 compatibility but require a
future controlled update/security-advisory review. No unpinned production
dependency was added.

## Deployment

Render is the one recommended path; Railway is the one fallback. An unsynced
Render staging Blueprint prepares one paid Singapore service, one instance, one
disk, MockProvider, generated token auth, operator-supplied CORS, and disabled
auto-deploy. Region, plan, current cost, data location, remote commit, backup,
auth, and device acceptance still require the user. No external service was
created.

**MEDIUM — single-instance SQLite:** the recommended persistent disk prevents
horizontal scale and zero-downtime deployment. It is acceptable for a single-
user MVP, but a multi-user or high-availability product must migrate operational
storage before launch.

## Product boundary

P1.5 is not an LMS, task suite, full note editor, Obsidian replacement, RAG or
agent system, publishing system, or video downloader. It stores an operational
queue, returns portable Markdown, exposes narrow metadata edits, and preserves
human/device ownership of local knowledge delivery.

## Known low/information risks

- LOW: one bearer token is an intentionally narrow single-user design; rotation
  and recovery are manual until deployed.
- INFO: real iPhone, Vault, Remotely Save, live Gemini, public network, deployed
  rate limits, staging backup/restore, and rollback have no acceptance evidence.

## Verdict

Approve as **P1.5 offline implementation and staging preparation** after the
final committed-tree check confirms no uncommitted changes. Do not approve the
release candidate or production readiness; see
`P1_5_RELEASE_CANDIDATE_AUDIT.md`.
