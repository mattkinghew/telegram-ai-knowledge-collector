# Mobile Device Acceptance v2

## Status

Manual test pack. No case has been executed by Codex.

```text
GATE A USER-ACCEPTED
FULL P1 DEVICE ACCEPTANCE PENDING
```

Gate A is accepted from the user's report. It was not verified by repository
automation, and no individual timings, screenshots, or device identifiers were
supplied.

Use only fictional or public-safe content. Do not record a real Vault
identifier, local path, credential, webhook URL, account detail, or private
screenshot in this repository.

For every case record:

```text
Result: PASS / FAIL / NOT RUN
Capture time:
Unexpected taps:
Format problem:
Sync problem:
Data loss:
Error:
Public-safe evidence reference:
```

A notification or app opening is not proof of note creation or sync. Inspect
the resulting note and approved second destination directly.

## Stage A — Architecture

Purpose:

```text
fixed Markdown → Obsidian URI → direct Inbox note → Remotely Save
```

1. Build the four-action `BKC Mobile Test` from
   `IPHONE_SHORTCUT_BUILD_SPEC_V2.md`.
2. Insert the real Vault identifier only on the device.
3. Run the fixed Markdown test once.
4. Confirm exactly one note appears directly at
   `00_Inbox/BKC-Mobile-Test`.
5. Confirm YAML, Chinese text, headings, and line breaks are intact.
6. Run the approved Remotely Save synchronization.
7. Confirm one readable copy on the intended second device or approved target.
8. Record the result without private identifiers.

Stage A is user-accepted. Build only the P1.0 Action Map for Gate B; do not yet
build the combined V3 Share Sheet or AI branches.

Gate A record:

```text
User reported architecture smoke test completed.
Verified by repository: No
Verified automatically: No
Device evidence: User-reported
Result: Accepted for progression to P1.0
```

## Stage B — Manual Quick Capture

Build the Quick Save-only Shortcut using
`IPHONE_SHORTCUT_P1_0_ACTION_MAP.md`, then run the complete Gate B pack in
`MOBILE_P1_0_DEVICE_ACCEPTANCE.md`:

| Case | Input | Required observation |
|---|---|---|
| B1 | typed text | Raw Content is exact; required Insight and blank optional Context/Action save |
| B2 | voice | Transcript is shown, editable, and must be confirmed |
| B3 | clipboard | Clipboard is read only after explicit selection and preview |

For each case confirm:

- one timestamp note is a direct child of `00_Inbox`;
- no title, category, tags, priority, deadline, or AI is required;
- `## AI 整理建議` is absent;
- cancel creates no note;
- a same-second collision does not overwrite an existing note;
- Remotely Save does not produce an unexplained conflict copy.

## Stage C — Share Sheet

Deferred to P1.1; not implemented in P1.0.

| Case | Input | Expected stored representation |
|---|---|---|
| C1 | URL with query and fragment | original URL in Source; no fetch |
| C2 | selected text | text verbatim as Raw Content |
| C3 | image | `image_reference`, user description, optional safe filename; no OCR |
| C4 | file/PDF | `file_reference`, user description, optional safe filename; no parse/upload |

Also test Chinese, English, emoji, `&`, `#`, `%`, `?`, `=`, `/`, `:`, Markdown
punctuation, and multiline text. Compare the decoded note with the preview.

## Stage D — AI Knowledge Enrichment

Deferred to P1.2; not implemented on device in P1.0.

Use sanitized content only after the Make.com scenario and provider settings
are reviewed and approved.

| Case | Service behavior | Expected user-visible behavior |
|---|---|---|
| D1 | valid success envelope | show bounded suggestions; require acceptance |
| D2 | AI unavailable | show `AI 整理失敗`; offer Quick Save, Retry, Cancel |
| D3 | timeout | preserve all source/user fields and offer Quick Save |
| D4 | invalid JSON | reject suggestions; do not modify confirmed fields |
| D5 | schema mismatch/unknown field | reject suggestions; do not create an AI-confirmed fact |
| D6 | disallowed project | reject response or replace with no suggestion; never auto-confirm |

For every failure, choose `保存原始筆記` and compare the final Source, Raw
Content, Insight, Context, and Action with the preview. Any loss or silent
replacement is a failure.

## Consolidated Acceptance Record

```text
Device model:
iOS version:
Obsidian version:
Shortcut version:
Remotely Save configuration reference:
Make.com scenario reference:
Test date:
Tester:
Stage A result:
Stage B passed / failed cases:
Stage C passed / failed cases:
Stage D passed / failed cases:
Median capture time observed:
Unexpected taps:
Format problems:
Sync problems:
Data loss observed:
Errors:
Approved evidence location:
Decision: ACCEPTED / NOT ACCEPTED
```

## Claim Boundary

Until each stage is directly observed:

```text
GATE A USER-ACCEPTED
FULL P1 DEVICE ACCEPTANCE PENDING
AI_SERVICE_ACCEPTANCE_PENDING
```

Do not claim `mobile feature complete`, `production ready`, `iPhone verified`,
or `Gemini integration complete` from this offline test pack.
