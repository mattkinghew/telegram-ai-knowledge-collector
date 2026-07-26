# P1C Deadline and Resource-expiry Review

## Purpose

`bkc due` produces a bounded, read-only action list from date metadata in direct
flat Inbox notes. It is not a notification or scheduling service.

## Metadata

- Deadline: a commitment or application cutoff.
- Resource Expiry: the last useful or available date for a resource.
- Reminder Date: a user-chosen date to review or act.
- Reminder Note: a single-line instruction associated with the reminder.

Dates must use `YYYY-MM-DD`. Empty values are allowed. Dynamic status is never
saved into the note, so it cannot become stale.

## Status calculation

`days_until` is event date minus `as-of`.

- less than zero: `overdue`;
- zero: `due_today`;
- 1 through `window-days`: `due_soon`;
- later: `upcoming`.

The default window is 14 days and accepts 1 through 365. Tests and acceptance
use explicit `--as-of`; normal use defaults to the local system date.

## Scope and output

The command reuses the P1B direct Inbox scanner and bounded H1/Metadata reader.
It stops above 5,000 candidates and returns at most 200 events. Upcoming events
are excluded unless requested by `--include-upcoming` or explicit upcoming
status.

Repeated event types and statuses use OR. Different filter fields use AND.
Stable tie-breaking is reminder, deadline, resource expiry, then Vault-relative
path. Text displays overdue values as Days Overdue. JSON uses a strict allowlist.

Neither output includes absolute paths, source URLs, local files, external file
links, content hashes, Source Notes, or body content. Diagnostics use stderr.

Each event also includes a stable key built from its type, current date, and
Vault-relative direct Inbox path. P1D accepts only keys the user explicitly
passes to `bkc report`; `bkc due` remains read-only.

## Manual review and search

Capture validates dates before creating a note. Review validates all requested
updates before one atomic write, supports explicit clearing, and can mark Date
and reminder fields reviewed. Relationship anomalies such as a reminder later
than a deadline are non-blocking diagnostics.

P1B search supports inclusive Resource Expiry and Reminder Date ranges and
presence filters. Reminder Note is allowlisted for metadata query.

## Known limitations

- No background notification, email, mobile alert, or scheduler.
- No Calendar integration or Calendar write.
- No natural-language date parsing or timezone guessing.
- No automatic report inclusion, note movement, archive, or deletion. P1D
  validates only explicitly selected events.
- No database, persistent index, semantic search, embedding, RAG, or external AI.
