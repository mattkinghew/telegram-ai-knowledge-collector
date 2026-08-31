# Context Summary

## Project Goal

Build a daily-use Business Knowledge Capture & Reporting MVP for the existing Obsidian vault. The MVP records text, URLs, and local file paths; extracts safe local metadata/readable text where supported; suggests one of four categories; preserves manual review; and generates New Role daily/weekly progress-report drafts.

## Current Architecture

Two complementary flows exist:

1. Existing no-code flow: Telegram → Make.com → optional Gemini processing → Google Sheets.
2. New local flow: CLI input → exact duplicate suggestion from flat Inbox metadata → flat `00_Inbox` Markdown note → metadata-only Inbox search and date review → manual review → explicitly selected events and notes → progress report.

The local CLI is the P0 core and does not require an API key.

The supported runtime is Python 3.9 or newer. CI validates Python 3.9, 3.10, 3.11, and 3.12; a system-wide Python 3.12 installation is not required.

## Vault Constraints

- The vault path is supplied at runtime; no hard-coded personal path.
- The CLI refuses to guess or create a duplicate vault when `00_Inbox` is missing.
- It reuses the one existing `14_New_Role_90_Day` project across the migrated or legacy project root and rejects a duplicate conflict.
- It does not perform vault-wide traversal or AI scanning.
- Protected paths are blocked before file access.
- `00_Inbox` remains flat.

## Implemented P0

- Text, URL, and local path registration.
- PDF, DOCX, TXT, MD, JPG/JPEG, PNG, MP3, and MP4 handling.
- PDF registration with optional local `pypdf` extraction.
- DOCX local text extraction through the standard library.
- Image metadata-only registration; OCR excluded.
- MP3/MP4 `awaiting_transcription`.
- Provider-agnostic summarizer interface: `manual`, `disabled`, disabled optional-AI adapter.
- Four-category suggestion: `重要知識`, `次要知識`, `資源`, `其他`.
- Human review command.
- Protected Paths file and enforcement.
- Non-destructive Protected Paths merging and stable `.v2` template conflict handling.
- Symlink rejection for source files, Vault notes, ancestors, and managed output targets.
- Vault-scoped Markdown validation for review and report inputs.
- Public URL validation, DNS-address checks, redirect validation, a 15-second timeout, a 2 MB response limit, and a fixed redirect limit.
- Single-line metadata sanitization and consistent manual classification metadata.
- New Role 90-day folder and progress-report template.
- Daily/weekly report draft from selected notes.
- External evidence links, including Google Drive URLs.
- Unit tests and operating instructions.

## P0 Acceptance

P0 acceptance completed on 2026-07-26 using Python 3.9.6. Thirty-three unit tests, an isolated 11-input Vault flow, protected-path and symlink rejection, manual review, and a scoped real-Vault daily report all passed. See `docs/P0_ACCEPTANCE_REPORT.md`.

## Implemented P1A

- Exact SHA-256 match against existing `Content Hash` metadata.
- Conservative HTTP/HTTPS normalization: lower-case scheme/IDNA hostname, remove default port and fragment, and use `/` for an empty path.
- Path case, non-empty trailing slash, query text/order/value, percent encoding, and HTTP/HTTPS remain distinct.
- Direct `00_Inbox/*.md` candidates only; metadata sections only; no recursive or Vault-wide scan.
- A 5,000-candidate safety limit and five recorded Vault-relative match paths.
- Duplicate metadata, stderr warning, and optional `--mark duplicate` manual review.
- No capture blocking, automatic deletion, merge, canonical selection, or movement.

P1A acceptance completed on 2026-07-26 using Python 3.9.6. All 33 P0 tests and 34 P1A tests passed, together with isolated and scoped real-Vault acceptance. See `docs/P1A_ACCEPTANCE_REPORT.md`.

## Implemented P1B

- Read-only `bkc search` over direct `00_Inbox/*.md` candidates.
- A bounded prefix reader exposes only H1 and the `## Metadata` section.
- Title, keyword allowlist, category, created/deadline, project/area, source/file type, processing/duplicate status, and action-presence filters.
- Repeated same-field values use OR; different fields use AND.
- Stable created, deadline, and title sorting with Vault-relative path tie-breaking.
- Human-readable text and UTF-8 JSON with a strict output allowlist.
- A 5,000-candidate hard stop, default 50 results, maximum 200 results, and 20 displayed malformed-note diagnostics.
- P0/P1A note compatibility without migration or Vault writes.

## Implemented P1C

- Strict `YYYY-MM-DD` validation for Deadline, Resource Expiry, and Reminder Date.
- Manual reminder metadata and newline-safe Reminder Note.
- Atomic review set/clear operations and a dates-review checkbox.
- Read-only `bkc due` over direct flat Inbox H1 and Metadata only.
- Dynamic overdue, due-today, due-soon, and upcoming status using explicit `as-of`.
- Same-field OR, different-field AND filters and deterministic sorting.
- Text and strict JSON output with Vault-relative paths only.
- P1B resource-expiry and reminder search filters.
- No background notification, Calendar integration, database, index, or note movement.

P1C acceptance completed on 2026-07-26 using Python 3.9.6. All 124 retained
tests and 23 P1C tests passed, together with isolated and scoped real-Vault
acceptance. See `docs/P1C_ACCEPTANCE_REPORT.md`.

## Implemented P1D

- Stable readable selection keys on all three due-event types.
- Repeatable, explicit `bkc report --due-selection`.
- Direct-Inbox, protected-path, regular-file, and symlink validation before
  selected Metadata is read.
- Stale protection for changed, cleared, malformed, or missing events.
- Stable duplicate-key removal, a 50-selection limit, deterministic event
  sorting, and dynamic status recalculation.
- Optional Date Review section with Vault-relative source traceability.
- Full validation before one atomic report write; selected notes stay unchanged.
- No automatic Inbox or project event inclusion.

## Implemented P1E

- Versioned, strict schema-v1 JSON for one reviewed mobile entry.
- `bkc handoff validate`, `preview`, and explicit single-file `import`.
- Text, URL-without-fetch, and device-produced voice transcript text.
- 256 KB exact-file limit, UTF-8, regular-file, extension, symlink-file, and
  symlink-ancestor enforcement.
- Duplicate-key, unknown/missing-field, type, length, date, timestamp, ID, and
  URL validation with no added dependency.
- Content-hidden preview with explicit 2,000-character display limit.
- Existing capture, exact duplicate, date, search, due, report, review, and
  atomic-write integration.
- Manual handoff and voice-transcript review flags with synchronized transcript
  review metadata.
- Anonymous samples and manual iPhone/AirDrop/user-approved transfer guidance.
- No watcher, batch import, automatic file consumption, network service,
  transcription engine, upload, credential, database, or external AI.

P1A through P1E are complete locally. P1 overall is complete at the tested
local branch boundary; no push, merge, deployment, or publication has occurred.

## Mobile-first P1.0 and P1.1

- Gate A and Gate B are accepted from the user's report; neither result was
  reproduced by Codex or repository automation.
- The user reports that P1.0 typed, voice, clipboard, blank optional fields,
  cancel, rapid double capture, direct save, and Remotely Save work on device.
- P1.0 is therefore device accepted at the user-report boundary.
- P1.1 Share Sheet support is implemented and validated offline for URL,
  shared text, image reference, and file/PDF reference inputs.
- P1.1 performs no webpage fetch, OCR, file parsing, attachment upload,
  Make.com call, Gemini call, or real Vault access.
- Gate C real-device Share Sheet acceptance remains pending.

## Not Implemented or Not Repository-verified

- Repository-verified iPhone Shortcut execution or Share Sheet routing.
- Audio transcription or audio-file handoff input.
- Semantic or fuzzy duplicate detection.
- Background deadline notifications.
- Search UI or persistent index.
- OCR.
- RAG, vector database, or chatbot.
- Automatic moves after classification.
- External AI activation, deployment, upload, or publication.

## Travel P1.2 RC Offline Implementation

- Plain-Markdown project status, mobile progress update, dashboard, daily
  report, period report, and processed-knowledge templates.
- A second, purpose-specific `更新專案進度` Shortcut action map; the capture
  Shortcut remains `收集靈感到 Obsidian`.
- Reference-only `video_url` and separately reviewed `video_transcript` source
  types; no download, scrape, OCR, parsing, or transcription.
- Additive V3 enrichment schemas/prompt for seven requested output modes while
  V2 remains unchanged.
- Deterministic, no-network V3 simulator plus selected-record progress report
  and manual dashboard reference builders. None accesses a Vault.
- Travel offline/recovery, Make setup, consolidated device acceptance, and
  conservative readiness documents.
- All real iPhone, Vault, Remotely Save, Make/Gemini, and network acceptance
  remains manual and pending unless explicitly marked user-reported above.

## Travel Setup Automation

- Literal build sheets now specify every action, variable, prompt, branch,
  expected result, and failure path for the two approved Shortcuts.
- A placeholder-only private config, explicit validator, current-doc map,
  three-scenario E2E pack, Make field worksheet, AI preview format, and compact
  travel quick-start reduce remaining setup interpretation.
- Seven fictional V3 request/expected-response pairs and four safe failure
  references support manual Make testing; project update/report samples show a
  concise travel baseline.
- `tools/travel_readiness_check.py` verifies repository artifacts, JSON,
  imports, fixtures, tests, placeholders, and selected privacy patterns only.
- Repository readiness does not verify the real iPhone, either Shortcut,
  Obsidian, Remotely Save, Make, Gemini, or live network behavior. Those remain
  manual, with live AI optional.

## P1.3 Voice-first Structured Capture

- Dedicated, additive voice request/response schemas preserve V1/V2/V3.
- One transcript can contain work, knowledge, learning, and content ideas.
- A standard-library validator and Markdown renderer retain the exact transcript,
  omit empty optional sections, and enforce the project allowlist.
- A deterministic development simulator covers structured, offline, unavailable,
  invalid-JSON, and schema-mismatch paths without AI, network, or Vault access.
- `語音快速記錄` is documented as an optional third Shortcut; it does not
  replace the two P1.2 Shortcuts.
- Real Siri, dictation, Obsidian, sync, Make, and Gemini acceptance remains
  manual and pending.

## P1.4 Simplified Two-entry Mobile Capture

- The recommended daily surface is now `語音閃念` and `收集內容`.
- Earlier capture, project-update, and voice Shortcuts remain fallback/reference;
  no P1.0–P1.3 schema, prompt, fixture, or workflow was deleted.
- Voice reuses the P1.3 strict contract with one dictation, optional correction,
  one final Save/Cancel decision, and lossless pending fallback.
- Content accepts URL, shared/selected text, video URL, image/file reference,
  and clipboard fallback, then asks only `整理`, `只收藏`, or `取消`.
- Local routing distinguishes article, social, video, selected text, clipboard,
  image, and file references without a manual category question.
- URL/reference-only processing stays `pending`; it is never presented as a
  completed summary. `只收藏` is `none`; validated output is `suggested`.
- The standard-library reference implementation performs no AI, network, URL
  fetch, OCR, file read, upload, video processing, Vault access, or retry.
- Real device, Shortcut, Obsidian, Remotely Save, Make, Gemini, and network
  acceptance remains manual and pending.

## P1.5 Hybrid Capture Platform

- FastAPI provides strict capture, status, paginated list, manual retry,
  dashboard, project, review/dismiss, and report-preview APIs.
- SQLite preserves immutable source/raw capture separately from result,
  Markdown, error, retry, and review metadata. It is an operational store, not
  the canonical knowledge base.
- Production mode supplies fixed single-instance application rate limits for
  capture, retry, read/list, report, and mutation routes. Health remains outside
  those buckets for platform health checks.
- MockProvider covers all processing modes offline. The Gemini adapter is
  guarded by production-only explicit configuration, a runtime secret, and a
  server-side model allowlist; tests use fake transport and make no live call.
- Public article/social extraction validates URL and DNS/redirect targets,
  time/redirect/byte/MIME/text limits, then parses readable text without a
  browser. Video stays a reference unless transcript text is supplied.
- A mobile-first static Web/PWA implements Today, Inbox, Projects, Pending, and
  Reports. It supports bounded search, review, project assignment, retry,
  dismissal without deletion, and human-selected report preview.
- P1.5 backend Shortcuts return Markdown to the device; only the Shortcut may
  invoke the local Obsidian write. Every backend/AI/Web failure retains the
  independent P1.4 local fallback.
- Tests use fictional data, local SQLite, local HTML fixtures, TestClient, two
  loopback-only production-mode Uvicorn flows, and Node's built-in runner. One
  flow exercises the Phase 4 backing APIs and restart persistence; the other
  serves a restored database containing three processed, one pending, and one
  failed record. Both include auth/log privacy checks. They are not browser or
  staging evidence. No browser automation, external AI, external site, real
  Vault, Remotely Save, or real device was used.
- Render with one paid web service and persistent disk is the one recommended
  deployment architecture; Railway with a volume is the one fallback. Neither
  was deployed.
- An unsynced Render staging Blueprint starts with MockProvider, one instance,
  one disk, generated token auth, manual CORS input, and auto-deploy disabled.
  A standard-library drill locally verifies Online Backup and clean restore for
  three processed, one pending, and one failed fictional capture; a real local
  Uvicorn process can read the restored records through authenticated APIs.
- An explicit-confirmation staging Mock smoke runner is prepared. It requires
  exact HTTPS origins, reads the token only from runtime environment state,
  creates two fixed fictional records, rejects redirects, and emits sanitized
  evidence. Automated tests use a fake transport; no external smoke was run.
- A separate explicit-confirmation live-Gemini acceptance runner is prepared
  for the four fixed fictional modes, one controlled pending failure, and one
  canonical-UUID manual retry. It strictly validates returned/stored provider
  results and emits no raw content or token. Automated tests use a fake
  transport; no Gemini or staging request was made.

## Current Known Risks

- DNS safety validation and the HTTP transport resolve separately, leaving a
  theoretical DNS-rebinding race. Production acceptance requires pinned-DNS
  egress or an outbound proxy/platform control.
- SQLite on a single persistent disk is appropriate only for the single-user
  MVP and prevents horizontal scale/zero-downtime disk deployments.
- Live Gemini, staging token/rate-limit/log/backup behavior, PWA device UX,
  iPhone Shortcut routing, local Obsidian creation, and Remotely Save remain
  manual acceptance items.

## Next Recommended Task

Obtain explicit authorization for Render account/region/paid-plan setup and for
making the exact local commit remotely deployable. Then deploy MockProvider
staging and complete `P1_5_BACKEND_ON_DEVICE_ACCEPTANCE.md`. Backend OFF is
`USER_REPORTED_DEVICE_PASS` only. Live Gemini, staging restore, Web/PWA device,
and production remain separate pending gates.
