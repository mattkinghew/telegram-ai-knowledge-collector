# Business Knowledge Capture P1A Acceptance Report

## Acceptance summary

- Acceptance date: 2026-07-26
- Repository branch: private accepted development branch (name redacted)
- Starting commit: `7fbb74c`
- Selected local Python: `/usr/bin/python3` 3.9.6
- Minimum supported Python: 3.9
- CI configuration retained: Python 3.9, 3.10, 3.11, and 3.12
- External AI, API key, network fetch, upload, deployment, publication, merge, and push: None

## Implemented

- Complete SHA-256 equality for comparable text and file captures.
- Conservative HTTP/HTTPS URL normalization and exact equality.
- `unique`, `exact_duplicate_suggested`, and `check_unavailable` metadata.
- Hash, URL, combined, none, and unavailable match types.
- Stable Vault-relative match paths, five-path recording limit, and full match count.
- stderr duplicate and unavailable warnings.
- Optional `Duplicate status reviewed` checkbox and `--mark duplicate`.
- Direct flat Inbox metadata-only scope with a 5,000-candidate limit.
- P0 note review and reporting backward compatibility.

## Validation

```bash
python3 -m compileall -q src tests
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m business_knowledge_capture.cli --help
git diff --check
```

- P0 regression: 33 passed
- P1A tests: 34 passed
- Total local tests: 67 passed
- Isolated Vault E2E: passed with unique text, duplicate text, normalized URL match, conservative URL non-matches, manual review, reporting regression, and flat Inbox validation
- Scoped real-Vault acceptance: passed
- Real acceptance original: `00_Inbox/20260726-190212-BKC-P1A-Acceptance-Original.md` recorded as unique
- Real acceptance duplicate: `00_Inbox/20260726-190213-BKC-P1A-Acceptance-Duplicate.md` recorded as an exact content-hash duplicate
- Duplicate warning, relative match path, count, original anonymous source, and manual checkbox: passed
- GitHub-hosted matrix: configured but not run because no push or pull request was permitted

## Safety result

- Protected content or metadata accessed: No
- `.obsidian` accessed: No
- Vault-wide or recursive scan: No
- Existing note bodies used for duplicate detection: No
- Symbolic link followed: No
- Existing Inbox note modified: No
- Automatic deletion, merge, canonical selection, or movement: No
- External AI, upload, or network fetch: No
- Make.com blueprint modified: No
- Private absolute Vault path committed: No

## Backup and rollback

A scoped external backup record was created before real-Vault writes. No pre-existing permitted file was modified, so the backup manifest contains no data rows. The operation manifest contains the two acceptance-created relative paths and final SHA-256 hashes.

Rollback was not required. Both acceptance notes are intentionally retained as review evidence.

## Known limitations

- Exact matching intentionally misses semantic similarity and reformatted content.
- Conservative URL equality intentionally preserves query order, path case, trailing slash, percent encoding, and HTTP/HTTPS differences.
- Sources without a hash or comparable URL are marked unavailable.
- Files above the existing 20 MB hash limit are not hashed.
- Only current direct flat Inbox metadata participates.
