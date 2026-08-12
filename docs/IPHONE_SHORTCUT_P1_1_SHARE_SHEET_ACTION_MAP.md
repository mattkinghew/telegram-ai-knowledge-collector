# iPhone Shortcut P1.1 Share Sheet Action Map

## Status and Boundary

Edit the one existing Shortcut:

```text
收集靈感到 Obsidian
```

Do not create a second production Shortcut. This document adds P1.1 Share
Sheet routing to the accepted P1.0 Quick Save flow. It does not add AI,
Make.com, OCR, file parsing, attachment upload, or network access.

Gate A and Gate B are user-reported passes. Codex did not operate the device.
Gate C remains pending.

Shortcuts action labels can vary by iOS language and release. If a label below
differs, use the native equivalent with the same local behavior. Do not add a
third-party action or external service to compensate.

## Shortcut Configuration

In the existing Shortcut details:

1. Enable **Show in Share Sheet**.
2. Limit accepted inputs to URLs, text, images, PDFs, and files when the local
   Shortcuts version exposes those filters.
3. Keep the real Vault identifier only in the local Shortcut. Repository
   examples use `EXAMPLE_VAULT_ID`.
4. Do not add a webhook URL, credential, or attachment-storage action.

## Stable Variables

Retain all P1.0 variables and add only these routing values:

```text
ShortcutInput
InputCount
DetectedType
Source
ReferenceName
```

The complete state remains:

```text
RawContent
SourceType
Source
Insight
Context
Action
CreatedAt
FilenameTimestamp
UniqueSuffix
NoteFile
Markdown
EncodedVault
EncodedFile
EncodedContent
ObsidianURI
```

Never replace one variable with another. Validation may inspect a copy, but
must not trim, rewrite, summarize, or normalize saved source/user text.

## Phase A — Shortcut Input Branch

At the beginning, add **If** using the native `Shortcut Input has any value`
condition.

### No incoming value

Run the existing P1.0 menu unchanged:

```text
輸入文字
語音輸入
使用剪貼簿
取消
```

Reuse the branches in `IPHONE_SHORTCUT_P1_0_ACTION_MAP.md`. Do not duplicate
their later reflection, Markdown, preview, or URI actions.

### Incoming value exists

1. Store the incoming value as `ShortcutInput`.
2. Use the native count action. P1.1 accepts exactly one item.
3. If the count is not one, show `一次只可保存一項分享內容。` and **Stop This
   Shortcut**.
4. Determine the native input type without reading attachment contents.
5. Route in this order:

```text
URL
Image
PDF or File
Text
Unsupported
```

The order matters because a URL must not be degraded into generic text, and a
PDF must remain a controlled file reference. Do not use `Get Contents of URL`,
`Get Contents of File`, OCR, base64, or any network action.

If the installed Shortcuts version cannot reliably distinguish an incoming
type, show `暫不支援這種分享內容。` and stop. Do not guess.

## Phase B — Source-specific Handling

### URL branch

1. Convert the single URL object to its original text representation without
   opening it.
2. Validate a copy with **Match Text** using a full-string HTTP/HTTPS rule.
   Reject blank, whitespace-containing, credential-bearing, or non-HTTP(S)
   values. If native matching cannot establish one valid URL, show
   `只支援一個有效的 HTTP 或 HTTPS 網址。` and stop.
3. Set:

```text
SourceType = url
Source = exact URL text
```

4. If the Share Sheet provides a safe title or selected text natively, set
   `RawContent` to that value followed by the URL when useful. Do not fetch a
   page title.
5. If no safe shared text/title exists, set `RawContent = Source`.
6. Do not ask the user to re-enter the URL.

Query strings, fragments, and existing percent escapes must remain unchanged.

### Shared text branch

1. Convert only the incoming plain/shared text to text.
2. Set:

```text
SourceType = shared_text
Source = blank
RawContent = incoming text verbatim
```

3. Use **Match Text** with `\S` against a copy. If there is no match, show
   `分享文字沒有可保存的內容。` and stop.
4. Preserve Chinese, English, multiline text, emoji, Markdown characters, and
   internal whitespace. Do not trim the stored variable.

### Image reference branch

1. Set `SourceType = image_reference`.
2. Do not run OCR, inspect pixels, encode, copy, upload, or save the image.
3. If the native item exposes a non-sensitive filename, obtain only its name.
   Store it as `ReferenceName` only when it is a basename with no `/`, `\`,
   absolute path, or account/location detail. Otherwise leave it blank.
4. Set `Source = ReferenceName` or blank.
5. Add **Ask for Input** with input type Text:

```text
這張圖片主要記錄甚麼？
```

6. Store the exact answer as `RawContent`.
7. Validate a copy with `\S`. If blank, show `請先描述這張圖片。` and stop.

### PDF or general file reference branch

1. Set `SourceType = file_reference`.
2. Do not open, parse, extract, encode, copy, upload, or save the file.
3. Obtain only an optional native filename and apply the same safe-basename
   rule as the image branch.
4. Set `Source = ReferenceName` or blank.
5. Ask:

```text
這份文件最值得記錄的內容是甚麼？
```

6. Store the exact answer as `RawContent`.
7. Validate a copy with `\S`. If blank, show `請先描述這份文件。` and stop.

### Unsupported branch

Show `暫不支援這種分享內容。` and **Stop This Shortcut**. Do not fall back to
stringifying unknown objects because that can leak paths or opaque metadata.

## Phase C — Shared Reflection Flow

After any valid source branch, join the accepted P1.0 flow once. Do not create
four separate copies of these questions.

1. Ask `這裡最值得記住甚麼？` and store the exact answer as `Insight`.
2. Validate a copy with `\S`. If blank, show
   `請寫下一句最值得記住的內容。` and stop.
3. Reject a multiline Insight so the Markdown keeps one H1. Ask the user to
   replace it with one line.
4. Ask `它可以幫我處理甚麼？（可留空）` and store as `Context`.
5. Ask `如果要用到它，我下一步可以做甚麼？（可留空）` and store as
   `Action`.

Set without asking:

```text
project = blank
output_goal = collect
ai_status = none
```

Do not add title, category, tags, project, output type, priority, deadline, or
AI prompts.

## Phase D — Filename and Markdown

Reuse the accepted P1.0 timestamp and four-digit random suffix actions:

```text
00_Inbox/YYYY-MM-DD-HHmmss-NNNN
```

Use the same Markdown structure:

```markdown
---
status: inbox
created: [CreatedAt]
source_type: [SourceType]
source: [Source]
project:
output_goal: collect
ai_status: none
---

# [Insight]

## 原始內容

[RawContent]

## 最值得記住

[Insight]

## 可以幫我處理

[Context]

## 下一步

[Action]
```

For a URL, `source:` must contain the exact original URL. Use a safe YAML
scalar representation available locally. If the Shortcut cannot safely escape
an optional image/file filename, leave that optional Source blank rather than
writing malformed frontmatter. Do not omit the URL Source.

Keep both optional headings when Context or Action is blank. Do not add an AI
section or attachment link.

## Phase E — Preview, Save, and URI

Reuse the accepted P1.0 preview and final menu exactly:

```text
保存
取消
```

`取消` stops before URI construction and creates no note. In `保存`:

1. URL Encode `VaultID`, `NoteFile`, and `Markdown` separately.
2. Construct exactly one:

```text
obsidian://new?vault=[EncodedVault]&file=[EncodedFile]&content=[EncodedContent]
```

3. Open the URI.

Do not add `overwrite`, `append`, local file writes, network calls, retries, or
a duplicate Shortcut. Success means only that the URI was handed to Obsidian;
Gate C must inspect the note and sync result directly.

## Build and Evidence Boundary

Build by editing the existing Shortcut directly on iPhone or in the Mac
Shortcuts app with user-managed sync. Do not generate or commit an unsigned
`.shortcut` package and do not reverse-engineer Apple's file format.

Use only public-safe test content. Keep real Vault identifiers, account data,
local paths, private screenshots, and Remotely Save details out of the
repository.
