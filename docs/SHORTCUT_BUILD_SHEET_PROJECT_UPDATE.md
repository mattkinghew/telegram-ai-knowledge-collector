# Shortcut Build Sheet — 更新專案進度

Status: `CURRENT` / manual device build required. Target completion time: approximately one minute.

## One-time private variables

- Store only 3–8 short active project display names on device.
- Use `VaultID=EXAMPLE_VAULT_ID` in this repository; replace it only on device.
- This Shortcut has no AI, webhook, file upload, background action, or automatic report claim.

## Literal action sheet

### Step 01

- Action: `List`.
- Input: private active project display names.
- Output variable: `ActiveProjects`.
- Prompt text: none.
- Branch condition: continue.
- Expected result: a short device-local project list is available.
- Failure behavior: if empty, show `請先加入 3–8 個目前專案。` and stop.

### Step 02

- Action: `Choose from List`.
- Input: `ActiveProjects`; Select Multiple off.
- Output variable: `Project`.
- Prompt text: `選擇專案`.
- Branch condition: selected → Step 03; Cancel → Step 12.
- Expected result: one exact project display name is selected.
- Failure behavior: no free-text fallback; update the device list privately if a project is missing.

### Step 03

- Action: `Ask for Input`.
- Input: text.
- Output variable: `Completed`.
- Prompt text: `已完成／目前進度是甚麼？`
- Branch condition: non-blank → Step 04; Cancel → Step 12.
- Expected result: required current progress is recorded in one or two sentences.
- Failure behavior: blank returns to the same prompt.

### Step 04

- Action: `Ask for Input`.
- Input: text.
- Output variable: `InProgress`.
- Prompt text: `仍在進行甚麼？（可留空）`
- Branch condition: any confirmed value → Step 05; Cancel → Step 12.
- Expected result: optional active work is preserved without invention.
- Failure behavior: blank is valid.

### Step 05

- Action: `Ask for Input`.
- Input: text.
- Output variable: `NextAction`.
- Prompt text: `下一個明確行動是甚麼？`
- Branch condition: non-blank → Step 06; Cancel → Step 12.
- Expected result: required next action is recorded.
- Failure behavior: blank returns to the same prompt.

### Step 06

- Action: `Ask for Input`.
- Input: text.
- Output variable: `Blocker`.
- Prompt text: `Blocker／待確認（可留空）`
- Branch condition: any confirmed value → Step 07; Cancel → Step 12.
- Expected result: optional blocker is user-authored or blank.
- Failure behavior: blank is valid; do not infer a blocker.

### Step 07

- Action: `Ask for Input`.
- Input: text or approved link.
- Output variable: `Evidence`.
- Prompt text: `Evidence／連結（可留空；不要貼憑證或客戶資料）`
- Branch condition: any confirmed value → Step 08; Cancel → Step 12.
- Expected result: optional evidence reference is preserved.
- Failure behavior: blank is valid; reject multiline secrets or credential-bearing URLs during review.

### Step 08

- Action: `Current Date`, then `Format Date` × 2.
- Input: device time.
- Output variable: `CapturedAt` ISO-8601 with offset; `Timestamp=yyyy-MM-dd-HHmmss`.
- Prompt text: none.
- Branch condition: continue.
- Expected result: note metadata and flat Inbox filename are deterministic.
- Failure behavior: show `無法建立時間戳；請複製輸入內容。` and stop without saving.

### Step 09

- Action: `Text`.
- Input: Project, Completed, InProgress, NextAction, Blocker, Evidence, CapturedAt.
- Output variable: `MarkdownDraft`.
- Prompt text: none.
- Branch condition: use `templates/mobile-progress-update-v1.md`; continue.
- Expected result: required fields and optional sections are readable and separate.
- Failure behavior: if Project, Completed, or NextAction is blank, return to its prompt.

### Step 10

- Action: `Show Result`.
- Input: `MarkdownDraft`.
- Output variable: none.
- Prompt text: prefix `預覽：尚未保存`.
- Branch condition: continue to Step 11.
- Expected result: the complete update is visible before save.
- Failure behavior: stop and leave entered text visible; do not open Obsidian.

### Step 11

- Action: `Choose from Menu`.
- Input: previewed update.
- Output variable: `SaveChoice`.
- Prompt text: `保存這次更新？`
- Branch condition: `保存` → Step 13; `返回修改` → Step 03; `取消` → Step 12.
- Expected result: explicit save confirmation.
- Failure behavior: menu dismissal cancels.

### Step 12

- Action: `Stop This Shortcut`.
- Input: any Cancel branch.
- Output variable: none.
- Prompt text: optional `已取消，沒有建立更新。`.
- Branch condition: terminal.
- Expected result: no note, URI, network call, or report is created.
- Failure behavior: none.

### Step 13

- Action: `If`.
- Input: `VaultID`.
- Output variable: none.
- Prompt text: failure `請先在裝置填入私人 Vault ID。`
- Branch condition: blank or `EXAMPLE_VAULT_ID` → stop; otherwise → Step 14.
- Expected result: repository placeholder can never be mistaken for a working private value.
- Failure behavior: preserve the preview for manual copy.

### Step 14

- Action: `URL Encode` × 3.
- Input: `VaultID`, `00_Inbox/<Timestamp>-progress`, `MarkdownDraft`.
- Output variable: `EncodedVault`, `EncodedFile`, `EncodedContent`.
- Prompt text: none.
- Branch condition: continue.
- Expected result: each URI component is encoded separately and Inbox stays flat.
- Failure behavior: stop without opening a partial URI.

### Step 15

- Action: `Text`.
- Input: encoded variables.
- Output variable: `ObsidianURI`.
- Prompt text: none.
- Branch condition: build `obsidian://new?vault=[EncodedVault]&file=[EncodedFile]&content=[EncodedContent]`.
- Expected result: no `overwrite` or subfolder is present.
- Failure behavior: if URI is too long, return to preview and shorten only with user approval.

### Step 16

- Action: `Open URLs`.
- Input: `ObsidianURI`.
- Output variable: none.
- Prompt text: none.
- Branch condition: terminal after handoff.
- Expected result: Obsidian receives the create-note request.
- Failure behavior: show `未能交給 Obsidian；請複製預覽內容。`; do not claim the note exists.

### Step 17

- Action: `Show Notification`.
- Input: URI handoff only.
- Output variable: none.
- Prompt text: `已交給 Obsidian；報告會在你明確選取更新後才產生。`
- Branch condition: terminal.
- Expected result: no automatic completion, sync, dashboard, or report claim.
- Failure behavior: sync remains pending until the user observes Remotely Save.

## One-minute acceptance check

- Required: Project, Completed/Current progress, Next Action.
- Optional: In Progress, Blocker, Evidence.
- No title/category/tag/date questionnaire.
- Preview once, save once.
- Complete Scenario 2 in `docs/TRAVEL_E2E_ACCEPTANCE.md` before calling the workflow device-ready.
