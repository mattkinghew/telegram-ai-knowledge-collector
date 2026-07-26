# Business Knowledge Capture P1D Acceptance Report

## Acceptance summary

- Acceptance date: 2026-07-26
- Repository branch: private accepted development branch (name redacted)
- Starting commit: `fab9238`
- Local Python: 3.9.6
- Minimum supported Python: 3.9
- CI matrix retained: Python 3.9, 3.10, 3.11, and 3.12
- External AI, API key, network, upload, notification, Calendar write,
  deployment, publication, merge, and push: None

## Implemented

- Stable readable keys for all three date-event types.
- Explicit repeatable `bkc report --due-selection`.
- Direct-Inbox path, Protected Paths, regular-file, and symlink validation.
- Exact current-date validation and stale/cleared/missing-event rejection.
- Stable duplicate handling and a 50-selection maximum.
- Dynamic status recalculation and deterministic report ordering.
- Optional Date Review with Vault-relative source traceability.
- Metadata-only selected-note reads and atomic report creation.
- Existing daily and weekly compatibility with no automatic event inclusion.

## Validation

- Compile: passed
- P0/P1A/P1B/P1C regression: 147/147 passed
- P1D focused tests: 61 passed
- Total unit tests: 208/208 passed
- Main, due, and report CLI help: passed
- Isolated E2E: passed with eight direct notes, one rejected nested fixture,
  eight date events, and five valid reports
- Invalid, stale, missing, nested, duplicate, overdue, and 51-selection flows:
  passed
- Direct-note read-only hashes and no-selection daily/weekly compatibility:
  passed
- Scoped real-Vault acceptance: passed
- Git diff check: passed before scoped acceptance
- GitHub-hosted matrix: pending because push and pull-request creation are
  prohibited

The first isolated evidence run stopped because its fixture assertion expected
nine date events from nine notes. Two notes intentionally had no dates, so the
correct result was eight events. The test-script assertion was corrected and
the complete isolated E2E then passed; no product CLI defect was involved.

## Real-Vault acceptance

The acceptance is designed to use one existing anonymous P1C direct-Inbox note
identified by bounded Metadata-only title search. Its private path is redacted.

Only reminder, deadline, and resource expiry keys explicitly selected from that
note entered the acceptance report. The private report path is redacted.

With `as-of` 2026-08-01 and a 14-day window:

- Reminder 2026-08-08: 7 days, `due_soon`
- Deadline 2026-08-15: 14 days, `due_soon`
- Resource Expiry 2026-08-31: 30 days, `upcoming`

The Date Review contained exactly three items in that order. The direct Inbox
candidate count remained five. Logical H1+Metadata state, direct-file `lstat`
state, and the selected note hash were unchanged. One new non-conflicting
report was created and no existing permitted file was overwritten.

## Safety result

- Protected content or metadata accessed: No
- `.obsidian` accessed: No
- Vault-wide or recursive Inbox scan: No
- Selected-note body read by due handoff: No
- Symbolic link followed: No
- Selected note modified: No
- Absolute Vault path exposed in public output: No
- Database, index, scheduler, notification, Calendar event, or external AI: No
- Make.com blueprint modified: No

## Evidence and rollback

Evidence is stored outside the Vault in the scoped P1D evidence folder. It
contains a zero-row backup manifest, backup/readme records, a one-row verified
operation manifest, redacted selection summary, report validation, command
summary, and read-only validation.

Rollback was not required. The anonymous acceptance report is intentionally
retained as evidence.

## Known limitations

- A date or path change intentionally invalidates an old key.
- No automatic event selection, notification, Calendar integration, scheduler,
  database, persistent index, semantic search, embedding, RAG, or external AI.
- GitHub-hosted matrix remains pending until a future permitted push or pull
  request.
