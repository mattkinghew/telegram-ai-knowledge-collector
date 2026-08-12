# iPhone Shortcut Build Specification v3

## Status

Future combined specification. P1.0 is user-reported device accepted; P1.1
Share Sheet Gate C and P1.2 AI device acceptance are pending.

For P1.0, use `IPHONE_SHORTCUT_P1_0_ACTION_MAP.md`. For the current P1.1 Share
Sheet build, use `IPHONE_SHORTCUT_P1_1_SHARE_SHEET_ACTION_MAP.md`; it supersedes
the Share Sheet steps below. AI parts remain deferred to P1.2.

No Shortcut was created or run by Codex during this offline stage. Gate A and
Gate B were accepted from the user's report, not repository or automatic
verification.

Build exactly one primary Shortcut named:

```text
收集靈感到 Obsidian
```

## Product Boundary

```text
Start
├── Shortcut Input exists?
│   ├── URL
│   ├── selected text
│   ├── image
│   └── file
└── No input
    ├── 輸入文字
    ├── 語音輸入
    ├── 使用剪貼簿
    └── 取消
        ↓
Raw Content / Source
        ↓
Insight → Context → optional Action
        ↓
optional Output Goal
        ↓
Quick Save / AI 整理 / Cancel
        ↓
Preview and one explicit Save
        ↓
Obsidian URI → direct 00_Inbox note
```

Quick Save is the reliability path and must not require Make.com, Gemini, a
Mac, Terminal, or a JSON handoff. AI is optional Knowledge Enrichment, not the
capture system.

## Configuration Kept Only on Device

| Variable | Repository example | Rule |
|---|---|---|
| `VaultID` | `EXAMPLE_VAULT_ID` | Enter the real identifier only on device |
| `InboxPath` | `00_Inbox` | Never add a subfolder |
| `WebhookURL` | `[MAKE_WEBHOOK_URL]` | Optional; never commit the value |
| `AllowedProjects` | public-safe test list | Do not expose private names |

Do not store a credential in the Shortcut. Configure authentication only in an
approved Make.com connection. Do not put a Vault path, attachment bytes, or
private identifier in a request.

## Canonical Variables

Use the exact concepts in `MOBILE_CAPTURE_CONTRACT_V1.md`:

```text
CapturedAt
SourceType
Source
RawContent
Insight
Context
Action
OutputGoal
Project
```

Keep these variables separate throughout the Shortcut. Never replace
`RawContent`, `Insight`, `Context`, or `Action` with AI output.

## Build Sequence

### 1. Receive and route input

Use **If Shortcut Input has any value**. When input exists, branch by the
first supported type. Do not send data to the network in this stage.

When no input exists, use one **Choose from Menu**:

```text
輸入文字
語音輸入
使用剪貼簿
取消
```

`取消` uses **Stop This Shortcut** before any URI or network action.

### 2. Produce Raw Content and Source

#### Shared URL

```text
SourceType = url
Source = original shared URL
RawContent = URL or available shared title/text
```

P0 must not fetch the webpage. Preserve query parameters, fragments, and
existing percent escapes as source data.

#### Selected text

```text
SourceType = shared_text
Source = blank
RawContent = selected text verbatim
```

Do not summarize, trim internal whitespace, or require a title.

#### Typed text

Use **Ask for Input** once:

```text
你想保存甚麼？
```

Set `SourceType = personal`, `Source = blank`, and the answer as `RawContent`.

#### Voice

Use **Dictate Text**, then show the transcript in an editable **Ask for Input**
field. The user must edit or confirm before continuing.

```text
SourceType = voice_transcript
Source = blank
RawContent = confirmed transcript
```

Do not claim dictation is offline, private, on-device, or encrypted. Those
properties depend on the user's device, settings, language, and provider and
must be verified manually.

#### Clipboard

Run **Get Clipboard** only after the user taps `使用剪貼簿`. Show the text for
review before continuing.

```text
SourceType = clipboard
Source = blank
RawContent = confirmed clipboard text
```

#### Screenshot or image

Do not run OCR and do not require attachment handling. Ask the user for a
description of the image.

```text
SourceType = image_reference
Source = optional public-safe filename
RawContent = user description
```

Do not infer unseen content. A filename is not evidence of image contents.

#### PDF or general file

Do not parse, upload, or embed the file. Ask for a description.

```text
SourceType = file_reference
Source = optional public-safe filename
RawContent = user description
```

Never store an absolute local path or binary data.

### 3. Ask the three reflection questions

Required Q1:

```text
這裡最值得記住甚麼？
```

Store the answer as `Insight`. If blank, explain that a short answer is needed
and return to the same field.

Required Q2:

```text
它可以幫我處理甚麼？
```

Store the free-text answer as `Context`. Do not force a project or category.

Optional Q3:

```text
如果要用到它，我下一步可以做甚麼？
```

Use an editable text field that accepts blank. The user may leave it empty for
later review; do not add another `稍後處理` menu.

### 4. Keep Output Goal optional

Default `OutputGoal` to `collect`. The main path does not require another tap.
Only when the user chooses `更改輸出目標` show this compact menu:

```text
collect — 只收藏
task — 任務
content — 內容素材
project_knowledge — 專案知識
progress — 工作進度
decision — 決策記錄
```

Project is optional. A blank Project is valid. If the user explicitly chooses
a Project, select only from the configured public-safe `AllowedProjects` list.

### 5. Build a deterministic draft

1. Use **Current Date**.
2. Use **Format Date** with `yyyy-MM-dd-HHmmss` for the filename.
3. Use ISO-8601 with a UTC offset for `created`.
4. Set `Filename` to `00_Inbox/<timestamp>`.
5. If another capture is intentionally created in the same second, add `-2`,
   `-3`, and so on before opening Obsidian.
6. Build the Markdown structure in `mobile-insight-note-v1.md`.
7. Put multiline data in body sections, not YAML scalar fields.

Do not ask for a title. Use `# Quick Capture`; a later review may rename the
file or improve the H1.

### 6. Preview and choose the save path

Show one preview containing Source, Raw Content, Insight, Context, optional
Action, Output Goal, optional Project, and AI status. Then offer:

```text
快速保存
使用 AI 整理
更改輸出目標
返回修改
取消
```

The normal Quick Save tap path is:

```text
1 launch
1 raw input
2 required reflection answers
1 optional Action answer
1 Save
```

No normal capture asks for a manual title, category, tags, priority, deadline,
classification confidence, duplicate status, AI model, project ID, or folder.

### 7. Quick Save

1. Set `ai_status = not-requested`.
2. Omit the entire `## AI 整理建議` section.
3. Keep the previewed source and user layers unchanged.
4. Continue to URI construction.

### 8. Optional Knowledge Enrichment

Only after the user selects `使用 AI 整理`:

1. Show a network-use confirmation.
2. Map confirmed fields to
   `schemas/mobile-insight-request-v2.schema.json`.
3. POST JSON to the locally configured `[MAKE_WEBHOOK_URL]`.
4. Treat the response as untrusted.
5. Require `ok = true`, `schema_version = "2"`, no unknown fields, bounded
   arrays, valid confidence, and an allowlisted or null project.
6. Show all AI Suggestions as unconfirmed.
7. Only explicit user acceptance adds the AI section.

Do not send credentials, absolute paths, attachment bytes, unconfirmed
clipboard content, or content the user is not permitted to share.

### 9. AI failure behavior

For network failure, timeout, non-2xx response, invalid JSON, schema mismatch,
or unknown fields, show:

```text
AI 整理失敗

保存原始筆記
重試
取消
```

`保存原始筆記` runs Quick Save with all original Source, Raw Content,
Insight, Context, and Action values intact. `重試` must not recreate or mutate
those variables. No AI failure may erase the capture.

### 10. Build but do not pre-claim the Obsidian URI

Apply **URL Encode** separately to `VaultID`, `Filename`, and the complete
Markdown. Build exactly:

```text
obsidian://new?vault=[EncodedVault]&file=[EncodedFile]&content=[EncodedContent]
```

Use **Open URLs** once. Do not add `overwrite`. Do not add `silent=true` until
device acceptance proves that failure feedback remains adequate.

The Shortcut may report that the URI was handed to Obsidian. It must not claim
the note exists or synchronized until those outcomes are observed directly.

## Explicit Non-goals for This Stage

- No webpage fetch.
- No OCR.
- No PDF or DOCX parsing.
- No attachment upload.
- No background watcher.
- No automatic tag or category generation.
- No automatic note move, overwrite, deletion, publication, or archive.
- No Mac dependency for primary capture.
- No removal or change to the desktop CLI or version-1 JSON fallback.

## Acceptance Boundary

This combined specification is not the P1.0 build guide. Complete the P1.0
Gate B pack before beginning its P1.1 or P1.2 sections. Until those later test
packs are run:

```text
DEVICE_ACCEPTANCE_PENDING
AI_SERVICE_ACCEPTANCE_PENDING
```
