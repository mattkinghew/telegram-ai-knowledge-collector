# iPhone Shortcut Build Specification v2

## Status and Scope

Proposed and specified. Not yet built or device-accepted.

Build exactly one primary Shortcut named:

```text
收集靈感到 Obsidian
```

It supports Share Sheet, Home Screen widget, Siri, Back Tap, and direct launch
from the Shortcuts app. Quick Save is the P0 path. Optional AI enrichment is
the P1 path. Normal capture must not require a Mac, Terminal, or JSON handoff.

## Configuration

Create these Shortcut text variables. Do not commit their real values:

| Variable | Design value | Purpose |
|---|---|---|
| `VaultID` | `EXAMPLE_VAULT_ID` | User-configured Vault identifier or approved public-safe name |
| `InboxPath` | `00_Inbox` | Direct destination; do not add subfolders |
| `WebhookURL` | `[MAKE_WEBHOOK_URL]` | Optional P1 endpoint |
| `AllowedProjects` | sanitized list below | Choices supplied to the user and AI |

Sanitized configurable project examples:

```text
New Role AI System
Digital Transformation Consulting
Cyber Kuma
AI PM Radar
Culture × Scent
AWS AIF-C01
Google AI Leader
Content Creation
Other
Not sure yet
```

Do not hard-code a private employer, client, personal Vault path, API key, or
credential.

## Shortcut Input Settings

Enable Share Sheet input for:

- URLs;
- plain text;
- rich text;
- images;
- files.

When launched without Shortcut Input, show:

```text
輸入文字
語音輸入
使用剪貼簿
取消
```

`取消` stops without opening Obsidian or making a network request.

## Stage 1 — Normalize the Input

Keep separate variables for `SourceType`, `Source`, `RawContent`, and
`SourceDescription`. Never replace `RawContent` with an AI result.

### Shared URL

1. Detect a URL from Shortcut Input.
2. Set `SourceType` to `url`.
3. Store the exact shared URL in `Source`.
4. Use the shared title when it is available; otherwise derive only a short
   filename title from user input.
5. Do not fetch or summarize the webpage in P0.

### Shared plain or rich text

1. Convert rich text to plain text without changing the source object.
2. Set `SourceType` to `text` or `rich_text`.
3. Store selected/shared text in `RawContent`.

### No-input typed text

1. Use **Ask for Input** with type Text.
2. Set `SourceType` to `text`.
3. Store the answer in `RawContent`.

### No-input voice

1. Run **Dictate Text**.
2. Set `SourceType` to `voice_transcript`.
3. Show the transcript using **Show Result** or **Choose from Menu**.
4. Offer `編輯`, `確認`, and `取消`.
5. For `編輯`, use **Ask for Input** prefilled with the transcript.
6. Continue only after the user confirms the edited or original transcript.

The user must verify the actual dictation provider and privacy settings.

### Clipboard

1. Use **Get Clipboard** only after the user selects `使用剪貼簿`.
2. Set `SourceType` to `clipboard`.
3. Show a preview before continuing.
4. Stop if the user cancels.

### Shared image or file

1. Set `SourceType` to `image` or `file`.
2. Use **Get Details of Files** to obtain a filename when available.
3. Put only the filename in `Source`; never put an absolute local path there.
4. Ask for a manual description and store it in `RawContent`.
5. Do not run OCR, parse documents, embed bytes, or silently discard the input.

The P0 note records the source type, safe filename, and description. It does
not claim that the original binary was copied into Obsidian.

## Stage 2 — Ask the Core Questions

The default path asks no more than three questions.

### Required question 1

```text
這項資料最值得保留的觀點是甚麼？
```

Store as `WhyKeep`. Permit a blank answer only when user-created
`RawContent` already states the insight. Otherwise, show a validation message
and ask again.

### Required question 2

```text
可以立即應用在哪裡？
```

Use **Choose from Menu** with the configured sanitized examples. `Other` asks
for one short custom value. `Not sure yet` is stored as an explicit uncertain
choice, not inferred into a project.

### Optional question 3

```text
下一個可執行行動是甚麼？
```

Use **Ask for Input** and permit blank.

### Conditional output question

Ask only when the intended output cannot be inferred from an explicit user
choice:

```text
希望這項資料變成甚麼？
```

Options:

```text
只收藏
任務
內容素材
專案知識
工作進度
決策記錄
```

Only one additional context question may follow, and only when necessary to
make the selected output usable. The preview must identify it as optional
context.

## Stage 3 — Build a Safe Draft

1. Create a timestamp with **Current Date** and **Format Date** using custom
   format `yyyy-MM-dd-HHmmss`.
2. Create `ShortTitle` from a user-reviewed title, limited to a short filename
   component. Replace `/`, `:`, and line breaks with `-`.
3. Set `Filename` to:

   ```text
   00_Inbox/<timestamp>-<short-title>.md
   ```

4. The seconds-level timestamp is the primary duplicate-name guard. If the
   Shortcut is rerun within the same second, regenerate the timestamp or add a
   short random suffix before continuing.
5. Build frontmatter using the mobile template. Use an ISO-8601 created time.
6. Build body sections from separate variables.
7. Escape or safely quote frontmatter values containing `:`, `#`, quotes, or
   line breaks. Multiline user content belongs in body sections, never inline
   frontmatter.

For Quick Save, omit the entire `## AI 整理建議` heading and body. For AI Save,
render reviewed AI suggestions under that heading and label them as
unconfirmed suggestions. Never overwrite `## 原始內容` or merge AI text into
the user's answers.

## Stage 4 — Preview and Save Choice

Show title, source type, safe source, raw content, three answers, output goal,
and whether AI will be used. Then show:

```text
快速保存
使用 AI 整理
返回修改
取消
```

- `快速保存`: build Markdown locally and continue to the Obsidian URI.
- `使用 AI 整理`: execute the reviewed P1 request below.
- `返回修改`: return to the editable answers without discarding raw content.
- `取消`: stop with no write or network call.

## Quick Save

Quick Save must work without Gemini, Make.com, a Mac, or JSON handoff:

1. Set `ai_status` to `not-requested`.
2. Build Markdown locally.
3. Omit the AI section.
4. Show a final note preview.
5. Require `儲存` confirmation.
6. Open exactly one `obsidian://new` URI.

## Optional AI Save

1. Confirm the final request preview before network use.
2. Build the object defined by
   `schemas/mobile-insight-request-v1.schema.json`.
3. Use **Get Contents of URL**:
   - URL: configured `WebhookURL`;
   - Method: `POST`;
   - Request Body: JSON;
   - headers: `Content-Type: application/json`;
   - body: reviewed fields only.
4. Do not include credentials, absolute paths, attachment bytes, or unreviewed
   clipboard content.
5. Validate that the response contains only the response-schema fields, at
   most three key points, a valid confidence, and an allowed related project or
   `null`.
6. Show every returned suggestion and offer `接受`, `返回修改`, and
   `改用快速保存`.
7. Only `接受` places the suggestions in the AI section.

On timeout, network error, non-2xx response, failure object, invalid JSON,
unknown field, schema mismatch, or disallowed project:

1. show a concise error;
2. preserve all original variables;
3. set `ai_status` to `fallback`;
4. offer Quick Save immediately.

Capture must never fail solely because AI is unavailable.

## Obsidian URI Construction

Use this parameter shape:

```text
obsidian://new?vault=<encoded-vault>&file=<encoded-file>&content=<encoded-markdown>
```

Shortcut actions must be applied in this order:

1. **URL Encode** `VaultID`; store as `EncodedVault`.
2. **URL Encode** the complete unique `Filename`; store as `EncodedFile`.
3. **URL Encode** the complete reviewed Markdown; store as `EncodedContent`.
4. Use a **Text** action to concatenate:

   ```text
   obsidian://new?vault=[EncodedVault]&file=[EncodedFile]&content=[EncodedContent]
   ```

5. Pass that Text into a **URL** action.
6. Use **Open URLs**.

Optionally add `&silent=true` only after real-device testing confirms the user
still receives sufficient success/failure feedback.

Requirements:

- URI-encode the Vault value, complete file path, and complete Markdown
  separately.
- Keep `00_Inbox` direct and do not create an Inbox subfolder.
- Do not use `overwrite`.
- Do not append to an unknown existing note.
- Use `EXAMPLE_VAULT_ID` only in documentation.
- Preserve non-ASCII Chinese and reserved characters through URL Encode.

## Completion Feedback

After Obsidian opens, the Shortcut may show `已交給 Obsidian 建立筆記`.
This is not proof that a note exists or has synchronized. Real-device
acceptance must separately confirm direct-Inbox creation and Remotely Save
sync.

## Explicit Non-goals

- No webpage fetch in P0 or P1.
- No OCR or document parsing in P0.
- No attachment upload in P1.
- No background capture or permanent service storage by default.
- No automatic publication, movement, deletion, overwrite, or archive.
- No change to the existing desktop CLI or JSON fallback.
