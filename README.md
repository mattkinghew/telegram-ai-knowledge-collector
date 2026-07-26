# Telegram AI Knowledge Collector

A personal signal-intelligence and Obsidian knowledge-capture project for turning text, links, and files into reviewable knowledge records and work-progress drafts.

## Current Product Scope

This repository contains two complementary workflows:

1. **Existing no-code prototype**  
   Telegram Bot → Make.com → optional Gemini processing → Google Sheets.

2. **Business Knowledge Capture & Reporting MVP**  
   CLI input → flat Obsidian `00_Inbox` note → classification suggestion → human review → selected-note daily/weekly progress report.

The local MVP runs without an API key and never invents an AI summary when no approved provider is configured.

## P0 Features

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

Python 3.12 or newer:

```bash
python -m pip install -e .
```

Optional local PDF text extraction:

```bash
python -m pip install -e ".[pdf]"
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
  --mark classification
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

## Validation

```bash
python -m compileall -q src tests
PYTHONPATH=src python -m unittest discover -s tests -v
bkc validate --vault "/absolute/path/to/Matt_Space"
```

## Documentation

- `docs/CONTEXT_SUMMARY.md`
- `docs/WORKFLOW.md`
- `docs/PRIVACY_AND_PROTECTED_PATHS.md`
- `docs/TESTING.md`
- `samples/sample_capture_commands.md`

## Not Included in P0

iPhone Shortcut, voice transcription, OCR, deduplication, deadline notifications, simple search UI, automatic classification moves, chatbot, RAG, vector database, external AI activation, deployment, and publication.
