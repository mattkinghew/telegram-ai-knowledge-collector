# Telegram AI Knowledge Collector

A personal signal-intelligence and Obsidian knowledge-capture project for turning text, links, and files into reviewable knowledge records and work-progress drafts.

## Current Product Scope

This repository contains two complementary workflows:

1. **Existing no-code prototype**
   Telegram Bot → Make.com → optional Gemini processing → Google Sheets.

2. **Business Knowledge Capture & Reporting MVP**
   CLI input → flat Obsidian `00_Inbox` note → classification suggestion → human review → selected-note daily/weekly progress report.

The local MVP runs without an API key and never invents an AI summary when no approved provider is configured.

P1.4 reduces the recommended daily mobile surface to two Shortcuts:
`語音閃念` for one-shot speech and `收集內容` for shared external material.
The offline reference contract reuses P1.3 voice structure, classifies content
without a category question, and preserves raw/pending saves when AI or source
content is unavailable. It does not transcribe audio, fetch URLs, call AI,
access a Vault, or prove an installed Shortcut.

P1.5 adds a local/offline hybrid platform around that fallback:

```text
iPhone Shortcut -> authenticated Capture API -> bounded processing/SQLite
                -> Markdown response -> Shortcut-owned local Obsidian write

Web/PWA -> Today -> Inbox -> Projects -> Pending -> Reports
```

The backend uses FastAPI, a deterministic mock AI provider, a production-only
explicitly guarded Gemini adapter, bounded public-URL extraction, and an
operational SQLite queue. The Web App is a mobile-first static ES-module client
served by the same application. The Gemini adapter is tested only with fake
transport; real iPhone Backend ON, live Gemini, real Vault/Remotely Save, and
deployment remain unverified and pending.

## Local MVP Features

- Capture one text item, URL, or local file path.
- Register PDF, DOCX, TXT, MD, JPG/JPEG, PNG, MP3, and MP4.
- Extract readable local text from TXT, MD, and DOCX.
- Optionally extract PDF text with the `pypdf` extra.
- Register images without OCR.
- Mark MP3/MP4 as `awaiting_transcription`.
- Store filename, MIME type, file size, processing status, original path/link, and optional Google Drive evidence link.
- Suggest `重要知識`, `次要知識`, `資源`, or `其他`.
- Keep all decisions subject to human review.
- Enforce Protected Paths before file access.
- Generate New Role daily/weekly progress-report Markdown from selected notes.
- Keep `00_Inbox` flat.
- Avoid vault-wide scanning, RAG, vector databases, and automatic file moves.
- Suggest exact duplicates using a complete content hash or conservatively normalized HTTP/HTTPS URL.
- Record duplicate status, match type, count, and up to five Vault-relative matching note paths.
- Keep duplicate decisions manual; captures are never blocked, deleted, merged, or moved.
- Search only the H1 title and an explicit metadata allowlist in direct `00_Inbox/*.md` notes.
- Combine repeated filters with OR, different filter fields with AND, and return stable text or JSON results.
- Keep search read-only and bounded to 5,000 candidates and 200 returned results.
- Validate deadline, resource-expiry, and reminder dates as `YYYY-MM-DD`.
- Review date events with a bounded, read-only `bkc due` command.
- Calculate overdue, due-today, due-soon, and upcoming status at query time.
- Copy stable due-event selection keys into an explicit progress-report handoff.
- Reject stale or unsafe selections before atomically creating a report.
- Validate, safely preview, and explicitly import one versioned mobile handoff JSON file.
- Accept reviewed text, URL, or voice-transcript text without a watcher, network service, or automatic file consumption.

## Safety Boundary

The CLI blocks:

- `20_Areas/25_Self_Management/**`
- `25_Self_Management/**`
- `Private/**`
- `Credentials/**`
- `.env`
- `.obsidian/**`

It does not request credentials, upload files, auto-publish, or process private company documents.

## Install

Python 3.9 or newer. A system-wide Python 3.12 installation is not required:

```bash
python3 -m pip install -e .
```

Optional local PDF text extraction:

```bash
python3 -m pip install -e ".[pdf]"
```

P1.5 local backend and Web/PWA:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[hybrid]"
P1_5_PYTHON=.venv/bin/python ./scripts/dev.sh
```

Open `http://127.0.0.1:8000/app/`. Development defaults use the mock provider
and explicit local dev auth. Never bind dev auth to a public interface. Copy
only variable names from `.env.example`; do not commit a real `.env` or secret.

## Initialize the Existing Vault

Do not point this at a new or guessed directory.

```bash
bkc init --vault "/absolute/path/to/Example_Business_Vault"
```

The initializer requires an existing `00_Inbox`. It detects migrated `10_Work/11_Projects` first and falls back to an existing `10_Projects`. It refuses to create a speculative duplicate project root.

## Capture Examples

```bash
bkc capture \
  --vault "/absolute/path/to/Example_Business_Vault" \
  --text "AI PM onboarding note" \
  --title "Week 1 onboarding"
```

```bash
bkc capture \
  --vault "/absolute/path/to/Example_Business_Vault" \
  --url "https://example.com/public-resource" \
  --title "Public resource" \
  --deadline "2026-08-31" \
  --resource-expiry "2026-09-15" \
  --reminder-date "2026-08-24" \
  --reminder-note "Review requirements before the deadline"
```

```bash
bkc capture \
  --vault "/absolute/path/to/Example_Business_Vault" \
  --file "/absolute/path/to/document.docx" \
  --external-file-link "https://drive.google.com/..."
```

## Manual Review

```bash
bkc review \
  --vault "/absolute/path/to/Example_Business_Vault" \
  --note "/absolute/path/to/Example_Business_Vault/00_Inbox/NOTE.md" \
  --category "重要知識" \
  --mark summary \
  --mark classification \
  --mark duplicate \
  --mark dates
```

Date fields can be set with `--deadline`, `--resource-expiry`,
`--reminder-date`, and `--reminder-note`. Use `--clear-deadline`,
`--clear-resource-expiry`, or `--clear-reminder` for explicit clearing.

## Deadline and Resource-expiry Review

```bash
bkc due \
  --vault "/absolute/path/to/Example_Business_Vault" \
  --as-of "2026-07-26" \
  --window-days 14
```

The default result includes overdue, due-today, and due-soon events. Add
`--include-upcoming` to include later events. Status is calculated dynamically;
it is never saved into a note. Text and JSON return Vault-relative paths only.

Each event also exposes a readable key such as:

```text
deadline::2026-08-15::00_Inbox/example.md
```

This is a foreground, read-only review command. It does not send notifications,
write Calendar events, modify notes, move files, or create an index.

## Progress Report

```bash
bkc report \
  --vault "/absolute/path/to/Example_Business_Vault" \
  --type weekly \
  --period "2026-07-20 to 2026-07-26" \
  --completed "/absolute/path/to/completed-note.md" \
  --in-progress "/absolute/path/to/in-progress-note.md" \
  --blocker "Awaiting access approval" \
  --commitment "Complete stakeholder map"
```

Date events enter a report only through repeated explicit `--due-selection`
arguments. The command revalidates current selected-note Metadata before
writing:

```bash
bkc report \
  --vault "/absolute/path/to/Example_Business_Vault" \
  --type daily \
  --period "2026-08-01" \
  --as-of "2026-08-01" \
  --window-days 14 \
  --due-selection "deadline::2026-08-15::00_Inbox/example.md"
```

No selection means no `Date Review` section. Any invalid or stale selection
stops the full report. Duplicate keys appear once with a stderr warning; at
most 50 keys may be supplied.

## Mobile Handoff

Create and review one schema-version-1 JSON file on the mobile device, transfer
it manually, then validate and explicitly import the exact file:

```bash
bkc handoff validate --file "/path/to/handoff.json"
bkc handoff preview --file "/path/to/handoff.json"
bkc handoff import \
  --vault "/absolute/path/to/Example_Business_Vault" \
  --file "/path/to/handoff.json"
```

Preview hides content by default. `--show-content` displays at most 2,000
characters and may leave sensitive text in terminal history or screen
recordings. Import never deletes, moves, archives, uploads, or watches the
handoff file. URL handoffs are recorded without fetching the URL.

Voice transcription privacy depends on the device, operating-system settings,
keyboard/dictation provider and user configuration. This repository only
receives the resulting text file and does not perform transcription.

## Metadata-only Inbox Search

```bash
bkc search \
  --vault "/absolute/path/to/Example_Business_Vault" \
  --category "資源" \
  --has-resource-expiry \
  --reminder-from "2026-07-26" \
  --sort deadline-asc
```

Repeated category, source-type, file-type, processing-status, and duplicate-status filters use OR. Different filter fields use AND. `--query` searches only the title and documented metadata fields; it is not full-text search and never searches Source Notes.

Use `--format json` for bounded machine-readable output. Both text and JSON expose Vault-relative note paths only.

## Validation

```bash
python3 -m compileall -q src tests tools backend
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m business_knowledge_capture.cli --help
PYTHONPATH=src python3 -m business_knowledge_capture.cli due --help
PYTHONPATH=src python3 -m business_knowledge_capture.cli search --help
bkc validate --vault "/absolute/path/to/Example_Business_Vault"
node --test web/tests/lib.test.mjs
node --check web/app.js
node --check web/lib.mjs
node --check web/sw.js
```

CI runs compile, unit tests, CLI help, and Web helper/syntax tests on Python 3.9
through 3.12. The core CLI still has no required dependency or API key. Install
the explicit `hybrid` extra only for P1.5.

## Documentation

Start with `docs/CURRENT_DOCS_MAP.md`. The P1.5 backend build sheets are current
for hybrid use; the P1.4 V2 sheets remain the current local fallback. Earlier
P1.0–P1.3 material remains reference only.

- `docs/CONTEXT_SUMMARY.md`
- `docs/WORKFLOW.md`
- `docs/PRIVACY_AND_PROTECTED_PATHS.md`
- `docs/TESTING.md`
- `docs/P0_ACCEPTANCE_REPORT.md`
- `docs/P1A_DUPLICATE_DETECTION.md`
- `docs/P1A_ACCEPTANCE_REPORT.md`
- `docs/P1B_METADATA_SEARCH.md`
- `docs/P1B_ACCEPTANCE_REPORT.md`
- `docs/P1C_DATE_REVIEW.md`
- `docs/P1C_ACCEPTANCE_REPORT.md`
- `docs/P1D_DUE_REPORT_HANDOFF.md`
- `docs/P1D_ACCEPTANCE_REPORT.md`
- `docs/HANDOFF_SCHEMA_V1.md`
- `docs/IPHONE_SHORTCUT_HANDOFF.md`
- `docs/P1E_MOBILE_HANDOFF.md`
- `docs/P1E_ACCEPTANCE_REPORT.md`
- `docs/P1_4_SIMPLIFIED_MOBILE_PRODUCT_DECISION.md`
- `docs/P1_4_OFFLINE_BEHAVIOR.md`
- `docs/PENDING_ENRICHMENT_CONTRACT_V1.md`
- `docs/P1_4_TWO_SHORTCUT_DEVICE_ACCEPTANCE.md`
- `docs/P1_5_HYBRID_ARCHITECTURE.md`
- `docs/SHORTCUT_BACKEND_API_CONTRACT.md`
- `docs/P1_5_AUTH_SECURITY_MODEL.md`
- `docs/P1_5_DEPLOYMENT_OPTIONS.md`
- `docs/P1_5_ACCEPTANCE_MATRIX.md`
- `docs/P1_5_TECHNICAL_AUDIT.md`
- `samples/sample_capture_commands.md`
- `samples/handoff-text-v1.json`
- `samples/handoff-url-v1.json`
- `samples/handoff-voice-transcript-v1.json`
- `samples/handoff-invalid-examples.md`

## Not Included

Repository-verified iPhone Shortcut execution, audio transcription, OCR,
full-text/semantic search, fuzzy duplicate detection, deadline notifications,
Calendar integration, scheduled/background reports, watcher, batch import,
automatic classification moves, live Gemini, production deployment/publication,
chatbot, RAG, vector database, autonomous agents, arbitrary video downloading,
or direct backend Vault access.
