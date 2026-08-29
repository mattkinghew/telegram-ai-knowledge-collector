# Shortcut Build Sheet — 收集內容 V2

Status: `CURRENT` / manual device build required. This sheet specifies one-share
capture; it does not prove iPhone, Obsidian, AI, or sync behavior.

## One-time private values

- `VaultID`: replace `EXAMPLE_VAULT_ID` only on the device.
- `ContentAIEnabled`: default `false`.
- `MakeWebhookURL`: blank or device-local only.
- `PreviewBeforeSave`: default `false`.
- Share Sheet types: URLs, Text, Images, Files, and PDFs.

Never add URL fetch, OCR, parsing, attachment upload, video download,
transcription, autonomous retry, provider/model selector, or `overwrite`.

## Literal action sheet

### Step 01 — Receive one input

- Action: `Receive Shortcut Input`.
- Output: `ShortcutInput`.
- Branch: has value → Step 03; no value → Step 02.
- Failure: multiple mixed objects or unsupported types show a short explanation
  and stop; do not merge them by guessing.

### Step 02 — Clipboard fallback

- Action: `Get Clipboard` only after direct launch.
- Output: `RawContent`; set `InputKind=clipboard`, `Source` blank.
- Branch: non-blank text → Step 08; blank/non-text → Step 16.
- Failure message: `剪貼簿沒有可保存文字。`

### Step 03 — Detect system type

- Action: `Get Type`.
- Branch: URL → Step 04; Text → Step 05; Image → Step 06; File/PDF →
  Step 07; otherwise → Step 16.
- Failure message: `不支援此分享格式；請改用文字、連結或檔案參考。`

### Step 04 — Classify URL without a question

- Action: `Get URLs from Input`, `Get Component of URL=Host`, lowercase host,
  then `If` checks.
- Preserve the exact original URL in `Source`; set `RawContent` to any separate
  shared text/takeaway only, otherwise blank.
- Host ending in `youtube.com`, `youtu.be`, `vimeo.com`, `tiktok.com`, or
  `twitch.tv` → `SourceType=video_url`.
- Host ending in `x.com`, `twitter.com`, `threads.net`, `instagram.com`,
  `facebook.com`, `linkedin.com`, or `reddit.com` → `SourceType=social_post`.
- Otherwise → `SourceType=article_url`.
- Branch: valid HTTP/HTTPS URL without embedded credentials/whitespace → Step
  08; invalid → Step 16.
- Boundary: classification is only a local routing hint. It does not prove that
  any page or transcript content is available.

### Step 05 — Shared or selected text

- Action: `Get Text from Input`.
- Set: `InputKind=selected_text`, `SourceType=selected_text`, `Source` blank,
  `RawContent` exact input.
- Branch: non-blank → Step 08; blank → Step 16.
- Preserve line breaks, Unicode, emoji, and Markdown exactly.

### Step 06 — Image reference

- Action: `Get Name` only.
- Set: `InputKind=image`, `SourceType=image_reference`,
  `Source=safe filename`, `RawContent` blank.
- Branch: filename contains no `/` or `\` and is not `.`/`..` → Step 08;
  otherwise → Step 16.
- Do not read bytes, OCR, base64-encode, upload, or infer image content.

### Step 07 — File/PDF reference

- Action: `Get Name` only.
- Set: `InputKind=file`, `SourceType=file_reference`,
  `Source=safe filename`, `RawContent` blank.
- Branch: same filename checks as Step 06 → Step 08; otherwise → Step 16.
- Do not read, parse, copy, upload, or preserve an absolute path.

### Step 08 — Primary menu

- Action: `Choose from Menu`.
- Prompt: `如何保存？`
- Options: `整理`, `只收藏`, `取消`.
- Branch: `只收藏` → set `RequestedProcessing=raw_save`, `AIStatus=none`,
  then Step 12; `整理` → Step 09; Cancel/dismissal → Step 16.

### Step 09 — Small processing menu

- Action: `Choose from Menu`.
- Prompt: `整理方式`.
- Map: `一般整理=summary`, `轉短文章=short_article`,
  `深入建議=recommendation`.
- Branch: selected → Step 10; Cancel → Step 16.
- Do not show task, decision, learning note, provider, or model choices.
  `project_knowledge` remains an internal/configured contract mode.

### Step 10 — Evidence and AI gate

- Action: `If`.
- If `RawContent` is blank: set `AIStatus=pending`; Step 12. This includes a
  URL-only, image-only, or file-only capture.
- If AI is disabled, webhook blank/placeholder, or sharing not approved: set
  `AIStatus=pending`; Step 12.
- Otherwise → Step 11.
- Never summarize a URL or reference when its content was not supplied.

### Step 11 — Optional structured processing

- Action: build the exact private request, then `Get Contents of URL` POST JSON.
- Validate the complete response before rendering: mode must match the request;
  summary/title/why fields bounded; maximum 3 core points, 3 immediate uses,
  3 convertible items, and 5 verification items; mode-specific draft or
  recommendation only; unknown fields rejected.
- Valid → set `AIStatus=suggested`; Step 12.
- Timeout/network/provider/invalid JSON/schema → set `AIStatus=pending`; Step
  12. Do not retry automatically and do not change Source/RawContent.

### Step 12 — Build lossless Markdown

- Action: `Text`.
- Required metadata: `type: content_capture`, `created`, `source_type`, exact
  `source`, `requested_processing`, `ai_status`, `review_status: unreviewed`.
- Suggested mode: label it `以下內容是未確認建議`, then render `30 秒摘要`,
  up to 3 points, why worth saving, immediate uses, convertible material, facts
  to verify, optional mode-specific section, then exact `原始內容` and `Source`.
- Pending/raw mode: render only available exact `原始內容` and `Source`.
- Branch: Step 13.

### Step 13 — Optional preview

- Action: `If PreviewBeforeSave`; when true, `Show Result`.
- Default: false. Continue to Step 14; preview dismissal → Step 16.

### Step 14 — One final decision and URI

- Action: `Choose from Menu`, options only `保存`, `取消`.
- Save: validate `VaultID`, create timestamp, URL-encode Vault/file/content
  separately, and build one `obsidian://new` URI targeting
  `00_Inbox/<Timestamp>-content`.
- Cancel/dismissal: Step 16.
- Failure: keep Markdown visible for manual copy; no partial URI or overwrite.

### Step 15 — Handoff and bounded notification

- Action: `Open URLs`, then `Show Notification`.
- `AIStatus=none`: `✓ 已保存`.
- `AIStatus=suggested`: `✓ 已整理並保存`.
- `AIStatus=pending`: `✓ 已保存，待稍後整理`.
- These messages mean URI handoff only. Confirm note creation and Remotely Save
  separately.

### Step 16 — Safe stop

- Action: show the relevant short error/cancel message, then
  `Stop This Shortcut`.
- Result: no capture, network request, or URI is created after cancellation.

## Remote Save boundary

Intended flow:

```text
Shortcut → Obsidian URI → local note → Sync on Save / normal Remotely Save
```

The Shortcut does not call or control Remotely Save. Device acceptance must
observe Obsidian opening, the note locally appearing, and the remote sync
result as separate facts.
