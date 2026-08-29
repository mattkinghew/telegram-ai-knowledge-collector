# Shortcut Build Sheet — 語音閃念 V2

Status: `CURRENT` / manual device build required. Device, Siri, dictation,
Obsidian, Make/Gemini, and Remotely Save behavior remains unverified.

## One-time private values

- `VaultID`: replace `EXAMPLE_VAULT_ID` only on the device.
- `AllowedProjects`: zero to 20 device-local names; never show a selector.
- `VoiceAIEnabled`: default `false`.
- `MakeWebhookURL`: blank or device-local only; never commit it.
- `PreviewBeforeSave`: default `false`; enable only if a full preview is useful.

No title, classification, project, tag, Insight, Context, Action, deadline, or
output-type prompt is allowed.

## Literal action sheet

### Step 01 — Dictate once

- Action: `Dictate Text`.
- Output: `DictatedTranscript`.
- Prompt: `自由講一次；工作、新知識、想法可以混合。`
- Branch: non-blank → Step 02; blank/Cancel → Step 13.
- Failure: show `未收到轉錄，沒有保存。`; do not invent content.

### Step 02 — Optional correction

- Action: `Ask for Input`, Text, Default Answer = `DictatedTranscript`.
- Output: `ConfirmedTranscript`.
- Prompt: `可直接完成；只在需要時修正轉錄。`
- Branch: non-blank → Step 03; Cancel → Step 13.
- Failure: a blank value stays on this editor; ask no other questions.

### Step 03 — Timestamp

- Action: `Current Date`, then `Format Date` twice.
- Output: timezone-aware ISO-8601 `CapturedAt`; `Timestamp=yyyy-MM-dd-HHmmss`.
- Branch: success → Step 04.
- Failure: display `ConfirmedTranscript` for manual copy and stop.

### Step 04 — Exact Voice V1 request

- Action: `Dictionary`.
- Keys: `schema_version=1`, `captured_at=CapturedAt`,
  `source_type=voice_transcript`, `raw_transcript=ConfirmedTranscript`,
  `allowed_projects=AllowedProjects`.
- Output: `VoiceRequest`.
- Branch: exact five keys → Step 05; otherwise → Step 08.

### Step 05 — Optional AI gate

- Action: `If`.
- Branch: `VoiceAIEnabled=true` and non-placeholder `MakeWebhookURL` → Step 06;
  otherwise → Step 08.
- Failure: never request credentials during capture.

### Step 06 — Structured processing

- Action: `Get Contents of URL`, POST JSON `VoiceRequest` to the private URL.
- Output: `VoiceResponse`.
- Branch: bounded JSON response → Step 07; timeout/network/provider error →
  Step 08.
- Failure: no automatic retry; keep `ConfirmedTranscript` unchanged.

### Step 07 — Validate and render suggestion

- Action: `Get Dictionary from Input`, then validate all Voice V1 fields,
  enums, list bounds, unknown fields, and project allowlist.
- Output: `MarkdownDraft`, `AIStatus=suggested`.
- Required rendering: omit empty sections; always append exact
  `## 原始語音轉錄` last.
- Branch: valid → Step 09; invalid JSON/schema/project → Step 08.
- Failure: do not repair prose or infer missing fields.

### Step 08 — Pending fallback

- Action: `Text`.
- Output: `MarkdownDraft`, `AIStatus=pending`.
- Required metadata: `type: voice_capture`, `created`,
  `source_type: voice_transcript`, `ai_status: pending`,
  `review_status: unreviewed`.
- Required body: exact `ConfirmedTranscript` under `## 原始語音轉錄`.
- Branch: Step 09.

### Step 09 — Optional preview

- Action: `If PreviewBeforeSave`; when true use `Show Result`.
- Input: `MarkdownDraft`.
- Branch: continue to Step 10; preview dismissal → Step 13.
- Default: false, so daily capture does not require a long preview.

### Step 10 — One final decision

- Action: `Choose from Menu`.
- Prompt: `保存這次語音閃念？`
- Options only: `保存`, `取消`.
- Branch: Save → Step 11; Cancel/dismissal → Step 13.

### Step 11 — Build Obsidian URI

- Action: validate `VaultID`, then `URL Encode` Vault, file, and content
  separately.
- File: `00_Inbox/<Timestamp>-voice-flash`.
- URI: `obsidian://new?vault=[Vault]&file=[File]&content=[Content]`.
- Branch: complete URI → Step 12.
- Failure: placeholder/blank Vault or encoding error preserves the draft for
  manual copy; do not add `overwrite`.

### Step 12 — Handoff and bounded notification

- Action: `Open URLs`, then `Show Notification`.
- If `AIStatus=suggested`: `✓ 已整理並保存`.
- If `AIStatus=pending`: `✓ 已保存，待稍後整理`.
- Meaning: the URI was handed to Obsidian; the user must still observe the note
  and any sync result. Do not display `已同步`.

### Step 13 — Safe stop

- Action: `Stop This Shortcut`.
- Optional message: `已取消，沒有建立筆記。`
- Result: no URI or network call begins after cancellation.

## Regression boundary

The request, validator, prompt, output structure, and fallback reuse P1.3 Voice
Contract V1. `語音快速記錄` may remain installed as a fallback; do not delete
or silently modify it during the P1.4 build.
