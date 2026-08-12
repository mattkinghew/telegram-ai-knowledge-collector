# Mobile P1.1 Device Acceptance — Gate C

## Status

```text
GATE A USER-REPORTED PASS
GATE B USER-REPORTED PASS
P1.0 DEVICE ACCEPTED BY USER REPORT
P1.1 OFFLINE IMPLEMENTATION COMPLETE
GATE C NOT RUN
```

Codex did not operate an iPhone, edit or run the real Shortcut, access a real
Vault, or verify Remotely Save. Gate A and Gate B are user-reported results,
not repository verification. Use only fictional or public-safe content.

For every case record:

```text
Result: PASS / FAIL / NOT RUN
Capture time:
Unnecessary taps:
Wrong input detection:
Formatting:
Sync:
Data loss:
User friction:
Error:
Public-safe evidence reference:
```

A success notification or Obsidian opening is not enough. Inspect the created
note directly and, when applicable, inspect the approved sync destination.

## Test 1 — Safari URL

Share one public HTTP/HTTPS URL containing no private query values.

Expected:

- exactly one URL is detected;
- original URL, query, fragment, and percent encoding are preserved;
- no manual URL re-entry and no webpage fetch occur;
- one direct `00_Inbox` note is created;
- frontmatter `source` contains the original URL;
- Raw Content contains available safe shared title/text or the URL.

## Test 2 — Selected Web Text

Share selected public-safe web text containing line breaks and punctuation.

Expected:

- `source_type: shared_text` and blank `source`;
- selected text is preserved exactly in Raw Content;
- no URL re-entry or invented page summary;
- one note only.

## Test 3 — Chinese Shared Text

Share Traditional Chinese text with emoji and Markdown characters.

Expected:

- Unicode, emoji, line breaks, Markdown characters, and internal whitespace
  remain intact in preview and final note;
- no character corruption occurs after URI encoding.

## Test 4 — Screenshot

Share one sanitized screenshot and answer `這張圖片主要記錄甚麼？`.

Expected:

- `source_type: image_reference`;
- no OCR, pixel analysis, upload, or base64 conversion;
- user description becomes Raw Content;
- optional safe filename is preserved when natively available;
- capture continues through the same three reflection questions.

## Test 5 — PDF

Share one fictional or public-safe PDF and answer the document description
question.

Expected:

- `source_type: file_reference`;
- optional safe filename is preserved when available;
- user description becomes Raw Content;
- no file open, extraction, parsing, attachment copy, or upload occurs.

## Test 6 — Generic File

Share one fictional or public-safe non-PDF file.

Expected:

- the same controlled `file_reference` behavior as Test 5;
- no opaque path, account detail, or binary content appears in Markdown;
- unsupported or ambiguous types stop rather than being guessed.

## Test 7 — Existing No-input Flow

Launch the Shortcut without Share Sheet input and test typed, voice, and
clipboard capture.

Expected:

- the original four-item P1.0 menu appears unchanged;
- typed, editable voice transcript, and clipboard branches still work;
- Insight remains required; Context and Action remain optional;
- preview, filename, Quick Save, direct Inbox placement, and no-AI behavior
  remain unchanged.

## Test 8 — Cancel

Cancel once during source-specific input and once at the final preview.

Expected:

- no Obsidian URI opens after cancellation;
- no note, upload, network request, or partial attachment copy occurs.

## Cross-case Checks

Run URL cases with HTTP, HTTPS, query, fragment, and percent-encoded values.
Run shared text with Chinese, English, multiline text, emoji, and Markdown.
Also confirm:

- one incoming item per run;
- multiple or unsupported items show a clear error;
- blank image/file descriptions create no note;
- the flow never asks URL/text users to re-enter supplied content;
- image/file source-specific description is the only extra question before the
  three common reflections;
- two rapid captures do not overwrite one another;
- Remotely Save produces no unexplained duplicate or conflict copy.

## Gate C Decision Record

Complete manually without secrets or private identifiers:

```text
Device:
iOS version:
Obsidian version:
Shortcut version:
Test date:
Tester:
Passed cases:
Failed cases:
Median approximate capture time:
Most unnecessary tap:
Most frequent wrong detection:
Formatting problems:
Sync problems:
Data loss observed:
User friction:
Approved evidence location:
Decision: ACCEPTED / NOT ACCEPTED
```

Until all eight cases pass:

```text
GATE C SHARE SHEET DEVICE ACCEPTANCE PENDING
```
