# Context Summary

## Project Goal

Build a daily-use Business Knowledge Capture & Reporting MVP for the existing Obsidian vault. The MVP records text, URLs, and local file paths; extracts safe local metadata/readable text where supported; suggests one of four categories; preserves manual review; and generates New Role daily/weekly progress-report drafts.

## Current Architecture

Two complementary flows exist:

1. Existing no-code flow: Telegram → Make.com → optional Gemini processing → Google Sheets.
2. New local flow: CLI input → flat `00_Inbox` Markdown note → manual review → selected-note progress report.

The local CLI is the P0 core and does not require an API key.

## Vault Constraints

- The vault path is supplied at runtime; no hard-coded personal path.
- The CLI refuses to guess or create a duplicate vault when `00_Inbox` is missing.
- It detects migrated `10_Work/11_Projects` first, then legacy `10_Projects`.
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
- New Role 90-day folder and progress-report template.
- Daily/weekly report draft from selected notes.
- External evidence links, including Google Drive URLs.
- Unit tests and operating instructions.

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

Install and smoke-test P0 with non-sensitive sample data in the actual vault. After acceptance, implement P1 deduplication and simple metadata search without changing the protected-path boundary.
