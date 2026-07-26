# P1D Explicit Due-to-report Handoff

## Purpose

P1D connects read-only date review to progress reports without automatic
selection. The user reviews `bkc due`, copies stable keys, and passes only those
keys to `bkc report`.

No explicit selection means no date event enters the report.

## Selection key

```text
<event_type>::<event_date>::<vault_relative_path>
```

Supported types are `reminder`, `deadline`, and `resource_expiry`. The date must
use `YYYY-MM-DD`. The path must identify one existing regular direct
`00_Inbox/*.md` note. The parser splits twice, so additional `::` text inside
the filename stays in the relative path.

Keys are readable audit references, not database or hash identifiers.

## Validation

Before rendering, every supplied key must pass:

- format, event-type, and ISO-date validation;
- Vault-relative, traversal-free, direct flat Inbox Markdown scope;
- Protected Paths and symlink checks before selected-note content is opened;
- existing regular-file validation;
- bounded H1 and Metadata read;
- current event-field existence and exact equality with the key date.

A changed or cleared date, missing note, or unsafe path stops the whole
operation. The command does not search for a replacement or silently use a new
date.

At most 50 keys may be supplied. Identical keys are stably deduplicated and
reported on stderr. Different event types from one note remain separate.

## Report behavior

`--as-of` defaults to the local date. `--window-days` defaults to 14 and accepts
1 through 365. These values recalculate current status but never decide whether
an explicit valid event is included. An explicitly selected upcoming event
therefore remains in the report.

Selected events sort by:

1. event date ascending;
2. reminder, deadline, resource expiry;
3. Unicode case-folded title ascending;
4. Vault-relative path ascending.

When at least one event exists, `## Date Review` appears after In Progress and
before Evidence. Each item includes status, non-negative days wording,
allowlisted action and relationship Metadata when present, and a Vault-relative
Source Note. Reminder Note appears only for reminder events.

Without selections, no empty Date Review section is rendered and the existing
daily/weekly workflow remains available.

## Atomicity and privacy

All keys are parsed and validated before report rendering or file creation. The
complete report is rendered in memory and created with one same-directory
atomic replacement. Existing report filenames are not intentionally reused.
Selected notes are not changed.

The selected-event reader does not read One-line Summary, Key Points,
Relevance, Suggested Actions, Source Notes, Manual Review, or other body
sections. Report output excludes absolute Vault paths, source URLs, local file
paths, external links, content hashes, credentials, and body content.

P1D uses Python 3.9+ and no API key. It adds no automatic report population,
notification, Calendar integration, background report, scheduler, database,
persistent index, external AI, upload, note movement, archive, or date update.

## Known limitations

- A date or path change intentionally invalidates an old key; run `bkc due`
  again.
- Date parsing remains strict ISO only, with no natural-language or timezone
  inference.
- Completed and In Progress retain their pre-P1D P0 note-reading behavior; the
  new due-selection path alone is Metadata-only.
