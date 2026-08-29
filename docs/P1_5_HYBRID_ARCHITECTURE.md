# P1.5 Hybrid Capture Architecture

Status: `ACCEPTED_FOR_OFFLINE_IMPLEMENTATION`

## Decision

P1.5 uses one FastAPI application for the Capture API and static Web/PWA,
SQLite for operational processing records, and a provider interface with a
deterministic mock implementation. The browser UI uses dependency-free HTML,
CSS, and ES modules rather than React/Next.js.

```text
iPhone Shortcuts
  -> authenticated Capture API
  -> strict request model
  -> optional bounded URL extraction
  -> configured provider adapter
  -> SQLite operational record
  -> structured JSON and deterministic Markdown
  -> Shortcut-controlled obsidian://new handoff

Web/PWA
  -> same authenticated API
  -> Today / Inbox / Projects / Pending / Reports
```

The backend never receives a Vault path and never writes into a Vault. Markdown
remains the canonical portable artifact; SQLite is only an operational queue
and review index.

## Why this stack

| Criterion | Decision impact |
|---|---|
| Existing Python investment | FastAPI reuses Python contracts and test conventions. |
| Validation | Pydantic models reject unknown fields and invalid types at the HTTP boundary. |
| Testability | FastAPI TestClient, temporary SQLite, and MockProvider allow local E2E tests. |
| Mobile latency | One service avoids a separate frontend deployment and API preflight in the default setup. |
| Dependencies | FastAPI, Uvicorn, and test-only HTTPX are the only new direct packages. |
| Python 3.9 | Versions are pinned to releases that still support the repository runtime. |
| Web scope | A small ES-module SPA is sufficient for five operational views and avoids a Node production toolchain. |
| Portfolio value | The system demonstrates API contracts, provider abstraction, SSRF controls, state transitions, and a usable mobile review surface. |

## Alternatives considered

- Flask: smaller surface, but explicit request/response schemas and generated
  OpenAPI would require additional conventions or packages.
- Next.js API routes plus React: strong full-stack UI, but duplicates the
  repository's Python contracts and adds a large dependency tree for a
  single-user operational MVP.
- Cloudflare Workers: attractive edge deployment, but Python/SQLite portability
  and current local contracts would require a larger rewrite.
- FastAPI with Jinja: viable, but the UI needs client-side filters, page states,
  and retry actions; static ES modules keep those interactions explicit without
  a template dependency.

## Package boundaries

```text
backend/
  app.py          application composition and static UI
  config.py       environment validation and safe defaults
  models.py       public request/response and provider schemas
  routes/         HTTP boundary only
  services/       capture orchestration, extraction, Markdown
  providers/      provider interface, mock, disabled Gemini boundary
  storage/        parameterized SQLite operations
  security/       auth, URL/SSRF, logging redaction
web/              static mobile-first UI and PWA assets
```

Routes call services; services call provider/storage/security components.
Provider output is untrusted and is validated before storage or rendering.
Storage does not import FastAPI and does not know about Obsidian.

## Trust boundaries and abuse cases

- HTTP JSON, query strings, auth headers, URL content, redirects, DNS answers,
  and AI output are untrusted.
- Capture requests have an explicit schema, total body limit, field limits,
  flat allowlisted structures, and bounded project lists.
- User-influenced URLs allow only HTTP/HTTPS, reject credentials and non-public
  targets, validate every redirect, enforce time/redirect/byte/MIME/text caps,
  and never download arbitrary binaries.
- Deployed mode fails closed without authentication configuration. Development
  mode may use explicit `AUTH_MODE=dev` only on a local interface.
- Logs contain capture ID, state, processing mode, duration, and error code;
  they exclude raw content, source URLs, auth values, and provider prompts.
- Provider failure creates or updates a pending record while preserving raw
  input. Retry is explicit and bounded; no background loop exists.

## State model

```text
pending -> processing -> processed
                    \-> failed
failed  -> processing        (manual retry)
pending -> processing        (manual retry)
```

`raw_content`, `source`, capture ID, and requested processing are immutable.
Processed output is stored separately. Review and dismissal update only
operational metadata. P1.5 performs no automatic deletion.

## Offline and product boundary

Backend, provider, Web App, or network failure must never block P1.4 local
capture. Shortcut build sheets keep the complete local Markdown fallback and
use backend output only after a validated success response.

P1.5 is not a Vault replacement, note editor, LMS, task-management suite, RAG
system, agent system, publishing platform, or video downloader.

## Dependency decision

- Required for P1.5: `fastapi==0.123.9`, `uvicorn==0.36.1`.
- Development/test only: `httpx==0.28.1` for the ASGI TestClient.
- Standard library: SQLite, URL parsing/fetching, IP classification, HTML text
  extraction, JSON, UUIDs, hashing, logging, and timestamps.
- Unnecessary and excluded: React, Next.js, ORM, browser automation, Beautiful
  Soup, requests for production fetches, Docker, RAG/vector/agent packages.

## Evidence boundary

Offline tests may prove local API, database, mock provider, extraction fixtures,
Markdown, Web assets, and error behavior. They do not prove real iPhone
Shortcuts, a real Vault, Remotely Save, live Gemini, public hosting, production
authentication, production persistence, or device latency.
