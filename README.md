# Telegram AI Knowledge Collector

A personal signal-intelligence and Obsidian knowledge-capture project for turning text, links, and files into reviewable knowledge records and work-progress drafts.

## Current Product Scope

This repository contains two complementary workflows:

1. **Existing no-code prototype**  
   Telegram Bot → Make.com → optional Gemini processing → Google Sheets.

2. **Business Knowledge Capture & Reporting MVP**  
   CLI input → flat Obsidian `00_Inbox` note → classification suggestion → human review → selected-note daily/weekly progress report.

The local MVP runs without an API key and never invents an AI summary when no approved provider is configured.

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

## Initialize the Existing Vault

Do not point this at a new or guessed directory.

```bash
bkc init --vault "/absolute/path/to/Matt_Space"
```

The initializer requires an existing `00_Inbox`. It detects migrated `10_Work/11_Projects` first and falls back to an existing `10_Projects`. It refuses to create a speculative duplicate project root.

## Capture Examples

```bash
bkc capture \
  --vault "/absolute/path/to/Matt_Space" \
  --text "AI PM onboarding note" \
  --title "Week 1 onboarding"
```

```bash
bkc capture \
  --vault "/absolute/path/to/Matt_Space" \
  --url "https://example.com/public-resource" \
  --title "Public resource" \
  --deadline "2026-08-31"
```

```bash
bkc capture \
  --vault "/absolute/path/to/Matt_Space" \
  --file "/absolute/path/to/document.docx" \
  --external-file-link "https://drive.google.com/..."
```

## Manual Review

```bash
bkc review \
  --vault "/absolute/path/to/Matt_Space" \
  --note "/absolute/path/to/Matt_Space/00_Inbox/NOTE.md" \
  --category "重要知識" \
  --mark summary \
  --mark classification \
  --mark duplicate
```

## Progress Report

```bash
bkc report \
  --vault "/absolute/path/to/Matt_Space" \
  --type weekly \
  --period "2026-07-20 to 2026-07-26" \
  --completed "/absolute/path/to/completed-note.md" \
  --in-progress "/absolute/path/to/in-progress-note.md" \
  --blocker "Awaiting access approval" \
  --commitment "Complete stakeholder map"
```

## Metadata-only Inbox Search

```bash
bkc search \
  --vault "/absolute/path/to/Matt_Space" \
  --category "資源" \
  --has-deadline \
  --sort deadline-asc
```

Repeated category, source-type, file-type, processing-status, and duplicate-status filters use OR. Different filter fields use AND. `--query` searches only the title and documented metadata fields; it is not full-text search and never searches Source Notes.

Use `--format json` for bounded machine-readable output. Both text and JSON expose Vault-relative note paths only.

## Validation

```bash
python3 -m compileall -q src tests
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m business_knowledge_capture.cli --help
PYTHONPATH=src python3 -m business_knowledge_capture.cli search --help
bkc validate --vault "/absolute/path/to/Matt_Space"
```

CI runs compile, unit tests, and the CLI help smoke test on Python 3.9 through 3.12. The core flow has no required dependencies and does not require an API key.

## Documentation

- `docs/CONTEXT_SUMMARY.md`
- `docs/WORKFLOW.md`
- `docs/PRIVACY_AND_PROTECTED_PATHS.md`
- `docs/TESTING.md`
- `docs/P0_ACCEPTANCE_REPORT.md`
- `docs/P1A_DUPLICATE_DETECTION.md`
- `docs/P1A_ACCEPTANCE_REPORT.md`
- `docs/P1B_METADATA_SEARCH.md`
- `docs/P1B_ACCEPTANCE_REPORT.md`
- `samples/sample_capture_commands.md`

## Not Included

iPhone Shortcut, voice transcription, OCR, full-text or semantic search, fuzzy duplicate detection, deadline notifications, search UI, persistent index, automatic classification moves, chatbot, RAG, vector database, external AI activation, deployment, and publication.
