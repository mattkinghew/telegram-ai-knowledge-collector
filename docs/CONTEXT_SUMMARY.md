# Context Summary

## Project Goal

Build a daily-use Business Knowledge Capture & Reporting MVP for the existing Obsidian vault. The MVP records text, URLs, and local file paths; extracts safe local metadata/readable text where supported; suggests one of four categories; preserves manual review; and generates New Role daily/weekly progress-report drafts.

## Current Architecture

Two complementary flows exist:

1. Existing no-code flow: Telegram → Make.com → optional Gemini processing → Google Sheets.
2. New local flow: CLI input → flat `00_Inbox` Markdown note → manual review → selected-note progress report.

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

## Not Implemented

- iPhone Shortcut and voice-input workflow.
- Voice transcription.
- Deduplication.
- Deadline notifications.
- Simple search/index UI.
- OCR.
- RAG, vector database, or chatbot.
- Automatic moves after classification.
- External AI activation, deployment, upload, or publication.

## Next Recommended Task

Complete and record the scoped P0 acceptance with non-sensitive sample data before selecting a separate P1 task.
