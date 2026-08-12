# Mobile-first P1.1 Product Scope

## Status

```text
GATE A USER-REPORTED PASS
GATE B USER-REPORTED PASS
P1.0 DEVICE ACCEPTED BY USER REPORT
P1.1 OFFLINE IMPLEMENTATION COMPLETE
GATE C SHARE SHEET DEVICE ACCEPTANCE PENDING
AI NOT IMPLEMENTED ON DEVICE
```

Gate A and Gate B are accepted from the user's report. Codex and repository
automation did not operate the device, inspect a real Vault, verify note
creation, or verify Remotely Save. No timing, screenshot, device identifier, or
private evidence is stored in this repository.

## Objective

P1.1 extends the existing Shortcut named `收集靈感到 Obsidian`. It does not
create a second production Shortcut.

```text
Share
→ detect supported input
→ preserve source material
→ Insight
→ optional Context
→ optional Action
→ preview
→ Quick Save
→ Obsidian 00_Inbox
```

When the Shortcut has no incoming Share Sheet input, the accepted P1.0 menu
remains unchanged:

```text
輸入文字
語音輸入
使用剪貼簿
取消
```

## Supported Share Sheet Inputs

| Incoming value | `source_type` | `source` | `raw_content` |
|---|---|---|---|
| HTTP/HTTPS URL | `url` | exact shared URL | shared title/text when safely available, otherwise URL |
| plain or selected text | `shared_text` | blank | incoming text verbatim |
| image | `image_reference` | optional public-safe filename | required user description |
| PDF or general file | `file_reference` | optional public-safe filename | required user description |

P1.1 accepts one supported incoming item per run. Empty, multiple, malformed,
or unsupported values stop with a clear message and create no note.

### URL

- Preserve the original HTTP/HTTPS string, including query, fragment, and
  existing percent encoding.
- Do not ask the user to enter the URL again.
- Do not fetch the page or infer its contents.
- When no safe shared title or text is available, use the URL as Raw Content.

### Shared text

- Preserve Unicode, multiline text, emoji, Markdown characters, and internal
  whitespace.
- Keep `source` blank.
- Do not summarize, correct, or classify the incoming text.

### Image reference

Ask one source-specific question before the common reflection flow:

```text
這張圖片主要記錄甚麼？
```

The answer becomes Raw Content. The image bytes are not opened, encoded,
copied, uploaded, or sent to OCR. A native filename may be retained only when
it is a basename without a path and is safe to store; otherwise leave Source
blank.

### File or PDF reference

Ask:

```text
這份文件最值得記錄的內容是甚麼？
```

The answer becomes Raw Content. P1.1 does not read, parse, extract, upload, or
embed the file. A native filename follows the same optional safe-basename rule.

## Common Reflection Flow

After source routing, use the accepted P1.0 questions:

1. Required Insight: `這裡最值得記住甚麼？`
2. Optional Context: `它可以幫我處理甚麼？（可留空）`
3. Optional Action: `如果要用到它，我下一步可以做甚麼？（可留空）`

Insight remains the Markdown H1. Context and Action may be blank and keep their
headings. Do not add title, tags, category, priority, deadline, project picker,
output-goal menu, or AI option.

## Fixed Defaults and Output

```text
project = blank
output_goal = collect
ai_status = none
filename = 00_Inbox/YYYY-MM-DD-HHmmss-NNNN
```

The P1.0 Markdown structure and independent URI encoding are unchanged. For a
URL capture, frontmatter `source` contains the exact shared URL. All Quick Save
notes omit `## AI 整理建議`.

## Security and Privacy Boundary

- Share Sheet input is untrusted data and must be validated before rendering.
- No network, webpage fetch, Make.com, Gemini, OCR, PDF parsing, file reading,
  attachment upload, base64 conversion, or real Vault access is part of P1.1.
- Never store an absolute path, Vault identifier, credential, account detail,
  or private evidence in repository material.
- Use fictional or public-safe data for Gate C.
- The Shortcut may receive a reference object to determine its native type and
  optional name; it must not request or transform attachment bytes.

## Success Boundary

Offline tests prove the reference contract, Markdown rendering, validation,
and P1.0 regressions. They do not prove iOS routing, app-specific Share Sheet
behavior, Obsidian note creation, or sync.

P1.1 becomes device accepted only after the user completes Gate C in
`MOBILE_P1_1_DEVICE_ACCEPTANCE.md`.
