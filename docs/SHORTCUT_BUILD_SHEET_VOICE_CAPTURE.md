# Shortcut Build Sheet — 語音快速記錄

Status: `CURRENT` / manual device build required. Recommended invocation name:
`語音快速記錄`. Siri invocation is supported as a design target but is
**未經裝置驗證**; wording, permissions, and dictation behavior may vary by OS.

## One-time private variables

- `VaultID`: keep `EXAMPLE_VAULT_ID` in repository examples; replace on device.
- `AllowedProjects`: device-local names only; the Shortcut never asks the user
  to choose one.
- `VoiceAIEnabled`: default `false`.
- `MakeWebhookURL`: keep blank or on-device only; never commit it.

No title, classification, project, tag, Insight, Context, or Action prompt is
part of this Shortcut.

Basic flow: `語音快速記錄` → `Dictate Text` → editable transcript
confirmation → structured processing when AI is available, otherwise pending
Quick Save → preview → Obsidian.

## Literal action sheet

### Step 01

- Action: `Dictate Text`.
- Input: one free-form utterance; stop listening after pause.
- Output variable: `DictatedTranscript`.
- Prompt text: `自由講一次；工作、新知識、想法可以混合。`
- Branch condition: non-blank → Step 02; blank/Cancel → Step 17.
- Expected result: one device-produced transcript exists.
- Failure behavior: show `未收到轉錄，沒有保存。`; never invent content.

### Step 02

- Action: `Ask for Input` with Default Answer = `DictatedTranscript`.
- Input: text.
- Output variable: `ConfirmedTranscript`.
- Prompt text: `確認轉錄（可直接完成，修改文字屬可選）`.
- Branch condition: non-blank → Step 03; Cancel → Step 17.
- Expected result: user reviews once and may correct transcription errors.
- Failure behavior: blank returns to this confirmation; no other questions.

### Step 03

- Action: `Current Date`, then `Format Date` twice.
- Input: device time.
- Output variable: `CapturedAt` as ISO-8601 with offset;
  `Timestamp=yyyy-MM-dd-HHmmss`.
- Prompt text: none.
- Branch condition: success → Step 04.
- Expected result: request timestamp and flat note filename are available.
- Failure behavior: show transcript for manual copy and stop without saving.

### Step 04

- Action: `List`.
- Input: zero to 20 private active project display names.
- Output variable: `AllowedProjects`.
- Prompt text: none.
- Branch condition: continue without showing a project selector.
- Expected result: allowlist is supplied as background context only.
- Failure behavior: invalid or duplicate list becomes an empty list.

### Step 05

- Action: `Dictionary`, then `Get Dictionary from Input` for validation.
- Input: version `1`, `CapturedAt`, `voice_transcript`,
  `ConfirmedTranscript`, and `AllowedProjects`.
- Output variable: `VoiceRequest`.
- Prompt text: none.
- Branch condition: all five keys present → Step 06.
- Expected result: exact `VOICE_CAPTURE_CONTRACT_V1` request.
- Failure behavior: skip AI and go to Step 10 with the transcript.

### Step 06

- Action: `If`.
- Input: `VoiceAIEnabled` and non-blank `MakeWebhookURL`.
- Output variable: none.
- Prompt text: none.
- Branch condition: both valid → Step 07; otherwise → Step 10.
- Expected result: live AI is optional and off by default.
- Failure behavior: never ask for a webhook or credential during capture.

### Step 07

- Action: `Get Contents of URL` using `POST`, JSON request body.
- Input: private on-device `MakeWebhookURL`; `VoiceRequest`.
- Output variable: `VoiceResponse`.
- Prompt text: none.
- Branch condition: bounded success response → Step 08; network/provider/
  timeout error → Step 10.
- Expected result: Make returns strict structured JSON, not prose.
- Failure behavior: discard the AI layer only; preserve transcript locally.

### Step 08

- Action: `Get Dictionary from Input`, then `Get Dictionary Value` for every
  required response field.
- Input: `VoiceResponse`.
- Output variable: `StructuredFields`.
- Prompt text: none.
- Branch condition: exact keys/types, allowed enums, bounds, and no unknown
  project → Step 09; otherwise → Step 10.
- Expected result: untrusted model output is schema-compatible.
- Failure behavior: invalid JSON/schema/project uses pending fallback; never
  repair provider prose by guessing.

### Step 09

- Action: `Text` plus one `If` per optional list.
- Input: `StructuredFields` and exact `ConfirmedTranscript`.
- Output variable: `MarkdownDraft`.
- Prompt text: none.
- Branch condition: append a heading only when its field is non-empty; always
  append `## 原始語音轉錄` last; continue to Step 11.
- Expected result: `ai_status: suggested`, concise structure, exact transcript.
- Failure behavior: any assembly problem → Step 10.

### Step 10

- Action: `Text`.
- Input: `CapturedAt` and exact `ConfirmedTranscript`.
- Output variable: `MarkdownDraft`.
- Prompt text: none.
- Branch condition: continue to Step 11.
- Expected result: `# Voice Capture`, `ai_status: pending`, and full original
  transcript; no other content is required.
- Failure behavior: if text assembly fails, show transcript for manual copy.

### Step 11

- Action: `Show Result`.
- Input: `MarkdownDraft`.
- Output variable: none.
- Prompt text: prefix `預覽：尚未保存`.
- Branch condition: continue to Step 12.
- Expected result: user reviews once before save.
- Failure behavior: do not open Obsidian; leave transcript visible.

### Step 12

- Action: `Choose from Menu`.
- Input: previewed note.
- Output variable: `SaveChoice`.
- Prompt text: `保存這次語音記錄？`
- Branch condition: `保存` → Step 13; `修改轉錄` → Step 02; `取消` → Step 17.
- Expected result: one explicit save decision.
- Failure behavior: menu dismissal cancels.

### Step 13

- Action: `If`.
- Input: `VaultID`.
- Output variable: none.
- Prompt text: `請先在裝置填入私人 Vault ID。`
- Branch condition: blank or `EXAMPLE_VAULT_ID` → stop with copy option;
  otherwise → Step 14.
- Expected result: repository placeholder is never treated as private config.
- Failure behavior: preserve the preview for manual copy.

### Step 14

- Action: `URL Encode` three times.
- Input: `VaultID`, `00_Inbox/<Timestamp>-voice`, `MarkdownDraft`.
- Output variable: `EncodedVault`, `EncodedFile`, `EncodedContent`.
- Prompt text: none.
- Branch condition: all encoded → Step 15.
- Expected result: each Obsidian URI component is encoded separately.
- Failure behavior: stop without opening a partial URI.

### Step 15

- Action: `Text`.
- Input: encoded variables.
- Output variable: `ObsidianURI`.
- Prompt text: none.
- Branch condition: build
  `obsidian://new?vault=[EncodedVault]&file=[EncodedFile]&content=[EncodedContent]`.
- Expected result: note target stays flat in `00_Inbox`; no overwrite flag.
- Failure behavior: if URI is too long, preserve preview for manual copy.

### Step 16

- Action: `Open URLs`, then `Show Notification`.
- Input: `ObsidianURI`.
- Output variable: none.
- Prompt text: `已交給 Obsidian；請確認筆記及同步。`
- Branch condition: terminal.
- Expected result: URI handoff occurs; existence or sync is not automatically
  claimed.
- Failure behavior: show `未能交給 Obsidian；請複製預覽內容。`.

### Step 17

- Action: `Stop This Shortcut`.
- Input: any Cancel or blank branch.
- Output variable: none.
- Prompt text: optional `已取消，沒有建立筆記。`.
- Branch condition: terminal.
- Expected result: no note, network call, or URI is created.
- Failure behavior: none.

## Deferred AI boundary

`ai_status: pending` permits later explicit processing after review. Do not add
an autonomous background retry. The existing `收集靈感到 Obsidian` and
`更新專案進度` Shortcuts remain in service; this is a universal fast
alternative for walking, commuting, or hands-busy situations.
