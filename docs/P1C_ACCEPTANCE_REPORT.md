# Business Knowledge Capture P1C Acceptance Report

## Acceptance summary

- Acceptance date: 2026-07-26
- Repository branch: private accepted development branch (name redacted)
- Starting commit: `845826a`
- Local Python: 3.9.6
- Minimum supported Python: 3.9
- CI matrix retained: Python 3.9, 3.10, 3.11, and 3.12
- External AI, API key, network, upload, notification, Calendar write,
  deployment, publication, merge, and push: None

## Implemented

- Deadline, Resource Expiry, Reminder Date, and Reminder Note metadata.
- Strict `YYYY-MM-DD` validation before capture or review writes.
- Atomic review set/clear operations and manual dates-review checkbox.
- Three independent date events per note.
- Dynamic overdue, due-today, due-soon, and upcoming calculation.
- Explicit `as-of`, configurable window, filters, deterministic sorting, and
  bounded result limits.
- Read-only direct-Inbox H1+Metadata processing.
- Text and allowlisted JSON output.
- Resource-expiry and reminder integration with P1B metadata search.
- P0, P1A, and P1B backward compatibility without note migration.

## Validation

- Compile: passed
- P0/P1A/P1B baseline: 124/124 passed
- P1C tests: 23 passed
- Total unit tests: 147/147 passed
- CLI help, due help, and search help: passed
- Isolated E2E: passed with nine direct notes and one excluded nested fixture
- All five sort modes, filters, text, JSON, zero results, invalid arguments,
  capture validation, review set/clear, and report regression: passed
- Protected-path and symlink tests: passed
- Git diff check: passed before real-Vault acceptance

## Real-Vault acceptance

One anonymous direct-Inbox acceptance note was created and manually marked as
date-reviewed. Its private path is redacted from this public report.

With `as-of` 2026-08-01 and a 14-day window:

- Reminder 2026-08-08: 7 days, `due_soon`
- Deadline 2026-08-15: 14 days, `due_soon`
- Resource Expiry 2026-08-31: 30 days, `upcoming`
- Default acceptance events returned: 2
- With include-upcoming: 3

JSON parsing and output allowlisting passed. Direct candidate logical
H1+Metadata state, lstat state, and acceptance-note hash were unchanged before
and after both due commands. Inbox flatness validation passed.

The evidence script initially stopped after capture and review because its own
process import path was incomplete. The already-created anonymous note was
recovered with the existing bounded metadata-only title search; no Vault-wide
search or second acceptance note was used. The corrected script then completed
the read-only acceptance.

## Safety result

- Protected content or metadata accessed: No
- `.obsidian` accessed: No
- Vault-wide or recursive Inbox scan: No
- Candidate note bodies read by due: No
- Symbolic link followed: No
- Vault files modified by due: No
- Existing permitted note modified: No
- Absolute Vault path exposed by due output: No
- Source URL, Local File, External File Link, Content Hash, or Source Notes
  exposed: No
- Database, index, scheduler, notification, or Calendar event created: No
- Make.com blueprint modified: No

## Backup and rollback

A scoped external evidence folder was created before the real-Vault write. The
backup manifest has zero data rows because no existing permitted target file was
modified. The operation manifest records one new anonymous note and its verified
final hash.

Rollback was not required. The anonymous note is intentionally retained as
acceptance evidence.

## Known limitations

- No natural-language date parsing or timezone inference.
- No background notification, email, mobile alert, or Calendar integration.
- No automatic report population, note movement, archive, or deletion.
- No database, persistent index, semantic search, embedding, RAG, or external AI.
- GitHub-hosted matrix execution remains pending because push and pull-request
  creation are prohibited.
