# Mobile Handoff Schema Version 1

## Purpose

Schema version 1 carries one user-reviewed text, URL, or device-produced voice
transcript from a mobile device into an explicit local CLI import. It is not an
API, batch format, attachment container, audio format, or automatic transport.

Schema version 1 is intentionally small and strict. Future fields require a new
documented schema version or an explicit backward-compatible policy.

## Exact object

Every field is required. Empty optional values remain empty strings.

```json
{
  "schema_version": 1,
  "handoff_id": "20260726T210000Z-iphone-001",
  "source_type": "voice_transcript",
  "title": "Meeting follow-up idea",
  "content": "Review the onboarding workflow and prepare the next action list.",
  "source_url": "",
  "captured_at": "2026-07-26T21:00:00+02:00",
  "action_required": "Review and classify this transcript.",
  "deadline": "",
  "resource_expiry": "",
  "reminder_date": "",
  "reminder_note": "",
  "related_project": "14_New_Role_90_Day",
  "related_area": "New Role"
}
```

Unknown fields, missing fields, duplicate keys, top-level arrays, nested values,
`null`, non-finite numbers, trailing JSON, and unsupported versions are
rejected. `schema_version` is the integer `1`; every other field is a string.

## Limits

| Field | Length |
|---|---:|
| `handoff_id` | 1–128 |
| `source_type` | 1–32 |
| `title` | 1–200 |
| `content` | 0–50,000 |
| `source_url` | 0–2,048 |
| `captured_at` | 1–64 |
| `action_required` | 0–500 |
| `deadline`, `resource_expiry`, `reminder_date` | 0 or 10 |
| `reminder_note` | 0–500 |
| `related_project`, `related_area` | 0–200 |

All fields except `content` are single-line and reject newline or control
characters. `handoff_id` accepts only ASCII letters, digits, `-`, `_`, `.`, and
`:`.

## Source-type rules

- `text`: non-empty `content`; empty `source_url`.
- `url`: valid HTTP/HTTPS `source_url`; optional `content` as a user note.
- `voice_transcript`: non-empty transcript text in `content`; empty
  `source_url`.

URLs with embedded username/password or non-HTTP schemes are rejected. URL
validation is syntactic: it never fetches, resolves DNS, or follows redirects.

There are no attachments, audio bytes, MP3/M4A/WAV inputs, OCR, video, arrays,
or batch payloads.

## Dates and timestamps

`deadline`, `resource_expiry`, and `reminder_date` are empty or strict
`YYYY-MM-DD`. `captured_at` is an ISO-8601/RFC3339 datetime with `Z` or an
explicit timezone offset. Import time remains the note `Created` value.

## File and import boundary

The CLI accepts one exact existing regular UTF-8 `.json` file of at most
256 KB. Symlink files, symlink ancestors, directories, special files, and
recursive folder input are rejected.

Validation and preview do not access the Vault. Import validates the complete
file, then uses the existing capture, exact duplicate, date, metadata
sanitization, protected-path, and atomic-write pipeline. Failure creates no
partial note. Reimport remains an explicit user action and may create a new
note with an exact-duplicate suggestion; there is no import registry.

The CLI never deletes, moves, archives, watches, uploads, or modifies the
handoff file.
