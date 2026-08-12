# Mobile P1.0 Device Acceptance — Gate B

## Status

```text
GATE A USER-ACCEPTED
P1.0 OFFLINE CONTRACT VERIFIED
GATE B USER-REPORTED PASS
P1.0 DEVICE ACCEPTED BY USER REPORT
```

The user reports typed, voice, clipboard, blank optional fields, cancel, rapid
double capture, direct save, and Remotely Save all work. Record this as
`USER_REPORTED_GATE_B_COMPLETE`. Codex did not operate an iPhone, build the
Shortcut, access a real Vault, verify Remotely Save, or receive individual
timings/screenshots. The detailed fields below remain a reusable regression
pack rather than repository-verified evidence.

Use fictional or public-safe content. Do not record a Vault identifier, local
path, credential, account detail, or private screenshot in this repository.

For every test record:

```text
Result: PASS / FAIL / NOT RUN
Capture time:
Format:
Sync:
Friction:
Data loss:
Error:
Public-safe evidence reference:
```

## Test 1 — Typed Chinese

Run one short Traditional Chinese capture. Confirm exact Raw Content, Insight
as H1, all four body headings, direct `00_Inbox` placement, and no AI section.

## Test 2 — Typed English

Run one English capture and perform the same format, save, and sync checks.

## Test 3 — Long Input

Run sanitized inputs at approximately 1,000 and 5,000 characters. Compare the
preview and final note for truncation, line-break changes, and URI failure. Do
not jump directly to the theoretical 50,000-character contract boundary.

## Test 4 — Voice

Confirm that dictation completes, the transcript appears in an editable field,
the transcript can be corrected, and the final note uses the corrected text.

## Test 5 — Clipboard

Confirm clipboard text is read only after explicit selection and is preserved
in the final note.

## Test 6 — Empty Optional Questions

Leave Context and Action blank. Confirm the note saves and retains both empty
section headings.

## Test 7 — Cancel

At the final preview choose `取消`. Confirm no Obsidian URI opens and no note is
created.

## Test 8 — Rapid Double Capture

Run two captures in a very short interval. Confirm two different timestamp and
four-digit-suffix filenames, no overwrite, and no unexplained Remotely Save
conflict copy.

## UX Pilot Questions

After all cases, record:

```text
Median approximate capture time:
Q1 useful:
Q2 useful:
Q3 useful:
Most annoying tap:
Most confusing prompt:
Would direct Obsidian typing be faster:
Did the structured questions improve later reuse:
```

The decision question is whether this flow is meaningfully better than opening
Obsidian and typing a note manually, not only whether it technically creates a
file.

## Acceptance Criteria

P1.0 passes only after the user reports all of the following:

```text
typed capture works
voice capture works
clipboard works
Chinese works
no data loss
cancel creates no note
same-second capture does not overwrite
Remotely Save still syncs
normal capture feels acceptable
```

User-reported result:

```text
USER_REPORTED_GATE_B_COMPLETE
P1.0 DEVICE ACCEPTED BY USER REPORT
Repository verification: No
Codex device execution: No
```
