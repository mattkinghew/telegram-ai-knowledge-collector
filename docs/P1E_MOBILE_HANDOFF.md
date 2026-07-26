# P1E Mobile and Voice Text Handoff

## Decision

P1E is a foreground, manual file handoff:

```text
mobile capture and review
→ one strict JSON file
→ user-approved transfer
→ explicit validate and preview
→ explicit import
→ existing local knowledge workflow
```

No explicit `bkc handoff import` command means no Vault note is created.

## CLI

- `bkc handoff validate --file FILE`: exact-file safety and schema validation;
  no Vault read or write.
- `bkc handoff preview --file FILE`: safe metadata summary; content hidden by
  default.
- `bkc handoff preview --file FILE --show-content`: explicit content display,
  capped at 2,000 characters.
- `bkc handoff import --vault VAULT --file FILE`: one complete validation and
  one atomic direct-Inbox note creation.

Success import prints the generated local note path to stdout. Duplicate
warnings remain on stderr. Invalid handoff data exits 1; file-safety boundary
violations exit 2. User-facing errors do not include a traceback.

## Mapping

All notes receive Handoff Schema Version, Handoff ID, Handoff Source Type,
Handoff Captured At, Transcript Review Status, and the Mobile handoff reviewed
checkbox. Voice-transcript notes also receive:

```text
Processing Status: transcript_registered
Transcript Review Status: pending
Voice transcript checked
```

`bkc review --mark transcript` checks the item and changes the status to
`reviewed`. It is rejected without a partial write for non-voice notes.

Text content and voice transcript text enter Source Notes. URL handoffs preserve
the source URL and optional user note, but never fetch the URL. Handoff file
absolute paths are not stored in notes.

## Safety and atomicity

The complete sequence is exact-file safety → bounded read → strict JSON parse →
all field validation → Vault identity/protection → existing duplicate check →
complete note render → same-directory atomic replacement.

There is no folder scan, watcher, poller, batch, background process, automatic
import, file deletion, file move, file archive, audio transcription, network
service, API, webhook, credential, upload, notification, Calendar integration,
database, semantic search, embedding, RAG, or deployment.

Reimport is allowed only as another explicit user action. Existing exact
duplicate detection warns and preserves both notes.

## Voice privacy

Voice transcription privacy depends on the device, operating-system settings,
keyboard/dictation provider and user configuration. This repository only
receives the resulting text file and does not perform transcription.

P1E does not prove that dictation occurred offline, on-device, privately, or
without transmission to Apple or another provider.
