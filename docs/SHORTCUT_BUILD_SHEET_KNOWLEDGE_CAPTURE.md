# Shortcut Build Sheet — 收集靈感到 Obsidian

Status: `CURRENT` / manual device build required. This is a literal build sheet, not proof that a Shortcut or Vault works.

## One-time private variables

- `VaultID`: replace `EXAMPLE_VAULT_ID` only on the device.
- `AllowedProjects`: copy only 3–8 current short project names to the device.
- `WebhookURL`: leave blank unless optional Make/Gemini is configured; never put it in Git.
- Shortcut Share Sheet types: URLs, Text, Images, Files, PDFs.
- Never add `overwrite`, file upload, OCR, scraping, transcription, or automatic publication.

## Literal action sheet

### Step 01

- Action: `Receive Shortcut Input`.
- Input: Share Sheet item or no input when launched directly.
- Output variable: `Shortcut Input`.
- Prompt text: none.
- Branch condition: continue to Step 02.
- Expected result: the original shared object remains available.
- Failure behavior: if iOS supplies an unsupported type, show `不支援此分享格式；請改用文字或連結。` and stop without saving.

### Step 02

- Action: `If`.
- Input: `Shortcut Input`.
- Output variable: none.
- Prompt text: none.
- Branch condition: `Shortcut Input has any value` → Step 03; otherwise → Step 11.
- Expected result: shared and manual entry paths are separated.
- Failure behavior: treat a missing or empty value as the manual path; do not infer content.

### Step 03

- Action: `Get Type`.
- Input: `Shortcut Input`.
- Output variable: `SharedType`.
- Prompt text: none.
- Branch condition: URL → Step 04; Text → Step 06; Image → Step 07; File/PDF → Step 09; otherwise stop.
- Expected result: one supported source branch is selected.
- Failure behavior: show the unsupported-format message and stop before any URI or network action.

### Step 04

- Action: `Choose from Menu`.
- Input: shared URL.
- Output variable: `URLKind`.
- Prompt text: `這是甚麼連結？`
- Branch condition: `一般 URL` or `影片 URL`; Cancel → Step 16.
- Expected result: the user, not hostname guessing, determines the URL type.
- Failure behavior: Cancel writes nothing; a blank URL stops with `未收到有效連結。`.

### Step 05

- Action: `Set Variable` × 3.
- Input: shared URL and `URLKind`.
- Output variable: `SourceType`, `Source`, `RawContent`.
- Prompt text: none.
- Branch condition: `一般 URL` → `SourceType=url`; `影片 URL` → `SourceType=video_url`.
- Expected result: `Source` and `RawContent` both preserve the exact URL; no fetch occurs.
- Failure behavior: if the value does not start with `http://` or `https://`, show `只接受 HTTP/HTTPS 連結。` and stop.

### Step 06

- Action: `Set Variable` × 3.
- Input: shared text.
- Output variable: `SourceType=shared_text`, `Source` blank, `RawContent` exact shared text.
- Prompt text: none.
- Branch condition: then Step 17.
- Expected result: line breaks and Chinese text are preserved.
- Failure behavior: blank text goes to Step 15 validation; never replace it with a summary.

### Step 07

- Action: `Get Name`.
- Input: shared image.
- Output variable: `ReferenceName`.
- Prompt text: none.
- Branch condition: then Step 08.
- Expected result: only a filename/reference is retained; no local path or image bytes enter Markdown.
- Failure behavior: if no public-safe filename is available, set `ReferenceName` blank.

### Step 08

- Action: `Ask for Input`.
- Input: shared image reference.
- Output variable: `RawContent`; also set `SourceType=image_reference`, `Source=ReferenceName`.
- Prompt text: `請用文字描述這張圖片最重要的內容（不會執行 OCR）。`
- Branch condition: non-blank → Step 17; Cancel → Step 16.
- Expected result: the user's description becomes content and the filename remains only a reference.
- Failure behavior: blank answer returns to the same prompt; never infer unseen image details.

### Step 09

- Action: `Get Name`.
- Input: shared File/PDF.
- Output variable: `ReferenceName`.
- Prompt text: none.
- Branch condition: then Step 10.
- Expected result: filename only; no absolute path, binary, upload, or parsing.
- Failure behavior: if the name contains `/` or `\\`, set it blank and continue to ask for a description.

### Step 10

- Action: `Ask for Input`.
- Input: shared file reference.
- Output variable: `RawContent`; also set `SourceType=file_reference`, `Source=ReferenceName`.
- Prompt text: `請描述這個檔案值得保留的內容（不會讀取或上傳檔案）。`
- Branch condition: non-blank → Step 17; Cancel → Step 16.
- Expected result: only reviewed user text and an optional filename are captured.
- Failure behavior: blank answer returns to this prompt.

### Step 11

- Action: `Choose from Menu`.
- Input: none.
- Output variable: `InputMode`.
- Prompt text: `選擇輸入方式`.
- Branch condition: `輸入文字` → Step 12; `語音輸入` → Step 13; `使用剪貼簿` → Step 14; `取消` → Step 16.
- Expected result: exactly one manual input mode is selected.
- Failure behavior: menu dismissal follows Cancel and writes nothing.

### Step 12

- Action: `Ask for Input`.
- Input: typed text.
- Output variable: `RawContent`; set `SourceType=personal`, `Source` blank.
- Prompt text: `你想保存甚麼？`
- Branch condition: non-blank → Step 17; Cancel → Step 16.
- Expected result: typed text is preserved exactly.
- Failure behavior: blank answer returns to the prompt.

### Step 13

- Action: `Dictate Text`, then `Ask for Input` with dictated text as default.
- Input: device-produced transcript.
- Output variable: edited `RawContent`; set `SourceType=voice_transcript`, `Source` blank.
- Prompt text: `請檢查並修正語音文字。`
- Branch condition: confirmed non-blank → Step 17; Cancel → Step 16.
- Expected result: only user-reviewed transcript text continues.
- Failure behavior: dictation unavailable → offer typed input or Cancel; make no offline/privacy claim about dictation.

### Step 14

- Action: `Get Clipboard`, then `Ask for Input` with clipboard text as default.
- Input: clipboard, only after the user selected this mode.
- Output variable: edited `RawContent`; set `SourceType=clipboard`, `Source` blank.
- Prompt text: `請確認要保存的剪貼簿文字。`
- Branch condition: confirmed non-blank → Step 17; Cancel → Step 16.
- Expected result: only reviewed clipboard text continues.
- Failure behavior: blank/non-text clipboard returns to the editor or Cancel; do not inspect clipboard earlier.

### Step 15

- Action: `If`.
- Input: `RawContent`.
- Output variable: none.
- Prompt text: failure message `內容不能留空。`.
- Branch condition: trimmed text is non-blank → Step 17; otherwise return to the originating input step.
- Expected result: no blank capture reaches preview.
- Failure behavior: never fabricate fallback content.

### Step 16

- Action: `Stop This Shortcut`.
- Input: any Cancel branch.
- Output variable: none.
- Prompt text: optional `已取消，沒有建立筆記。`.
- Branch condition: terminal.
- Expected result: no URI, webhook, or file action runs.
- Failure behavior: none; this is the safe terminal path.

### Step 17

- Action: `Ask for Input`.
- Input: user reflection.
- Output variable: `Insight`.
- Prompt text: `這裡最值得記住甚麼？`
- Branch condition: non-blank → Step 18; Cancel → Step 16.
- Expected result: one explicit user insight is captured.
- Failure behavior: blank answer returns to this prompt.

### Step 18

- Action: `Choose from Menu`.
- Input: `Insight`.
- Output variable: `CaptureDepth`.
- Prompt text: `選擇整理深度`.
- Branch condition: `快速保存` → Step 19; `深度整理` → Step 20; `取消` → Step 16.
- Expected result: Fast capture avoids optional questions; Deep capture gathers context.
- Failure behavior: menu dismissal cancels without saving.

### Step 19

- Action: `Set Variable` × 4.
- Input: Fast capture branch.
- Output variable: `Context` blank, `Action` blank, `OutputGoal=collect`, `RequestedOutput=summary`.
- Prompt text: none.
- Branch condition: continue to Step 25.
- Expected result: Quick Save remains independent of AI, Mac, Terminal, and network.
- Failure behavior: none; do not invoke WebhookURL.

### Step 20

- Action: `Ask for Input`.
- Input: user context.
- Output variable: `Context`.
- Prompt text: `它可以幫我處理甚麼？`
- Branch condition: non-blank → Step 21; Cancel → Step 16.
- Expected result: Deep capture has explicit use context.
- Failure behavior: blank returns to this prompt.

### Step 21

- Action: `Ask for Input`.
- Input: optional next action.
- Output variable: `Action`.
- Prompt text: `如果要用到它，我下一步可以做甚麼？（可留空）`
- Branch condition: any confirmed value → Step 22; Cancel → Step 16.
- Expected result: action is user-authored or blank.
- Failure behavior: do not auto-generate an action.

### Step 22

- Action: `Choose from Menu`.
- Input: Deep capture.
- Output variable: `OutputGoal`.
- Prompt text: `用途`.
- Branch condition: `collect`, `task`, `content`, `project_knowledge`, `progress`, or `decision`; Cancel → Step 16.
- Expected result: one exact contract value is selected.
- Failure behavior: unsupported value stops before AI or URI construction.

### Step 23

- Action: `Choose from Menu`.
- Input: desired AI output.
- Output variable: `RequestedOutput`.
- Prompt text: `如果使用 AI，希望得到甚麼？`
- Branch condition: `summary`, `recommendation`, `short_article`, `project_knowledge`, `task`, `decision`, or `learning_note`.
- Expected result: one V3 requested output is stored even if AI is skipped.
- Failure behavior: Cancel → Step 16; never default to a long free-form response.

### Step 24

- Action: `Choose from List` with `Select Multiple` off and an added `不連結專案` item.
- Input: on-device `AllowedProjects`.
- Output variable: `Project`.
- Prompt text: `連結到哪個專案？`
- Branch condition: project item → exact short name; `不連結專案` → blank.
- Expected result: Project is blank or allowlisted.
- Failure behavior: if the list is unavailable, set Project blank; never type or infer a private project name in shared output.

### Step 25

- Action: `Current Date`, then `Format Date` × 2.
- Input: device time.
- Output variable: `CapturedAt` as ISO-8601 with offset; `Timestamp` as `yyyy-MM-dd-HHmmss`.
- Prompt text: none.
- Branch condition: continue.
- Expected result: deterministic metadata and filename time are available.
- Failure behavior: if formatting fails, show `無法建立時間戳；內容仍在畫面上。` and stop without opening Obsidian.

### Step 26

- Action: `Text`.
- Input: Source/User variables, `ai_status=not-requested`.
- Output variable: `MarkdownDraft`.
- Prompt text: none.
- Branch condition: use body sections for multiline content; continue to Step 27.
- Expected result: Source, Raw Content, Insight, Context, Action, Output Goal, and Project stay separate.
- Failure behavior: if draft is empty, show variables for recovery and stop.

### Step 27

- Action: `Show Result`.
- Input: `MarkdownDraft`.
- Output variable: none.
- Prompt text: prefix `預覽：尚未保存`.
- Branch condition: after review → Step 28.
- Expected result: user can verify exact source and content before any save/network action.
- Failure behavior: preview failure stops while preserving entered variables in the running Shortcut.

### Step 28

- Action: `Choose from Menu`.
- Input: previewed draft.
- Output variable: `SaveChoice`.
- Prompt text: `下一步`.
- Branch condition: `快速保存` → Step 35; `使用 AI 整理` → Step 29; `返回修改` → Step 17; `取消` → Step 16.
- Expected result: one explicit save path is chosen.
- Failure behavior: dismissal cancels; no default network call.

### Step 29

- Action: `If`, then `Choose from Menu`.
- Input: `WebhookURL`, `ai_enabled`, and privacy decision.
- Output variable: `AIConsent`.
- Prompt text: `內容將傳送至已設定的 Make/Gemini。只可傳送獲准資料。繼續？`
- Branch condition: configured + `繼續` → Step 30; otherwise → Step 34.
- Expected result: live AI is opt-in and private/employer/client data defaults to Quick Save.
- Failure behavior: missing webhook or declined consent goes to Quick Save fallback without losing text.

### Step 30

- Action: `Dictionary`.
- Input: confirmed fields.
- Output variable: `AIRequest`.
- Prompt text: none.
- Branch condition: include exactly V3 request fields; continue to Step 31.
- Expected result: no credential, attachment byte, absolute path, or unknown field enters the request.
- Failure behavior: missing required field goes to Step 34.

### Step 31

- Action: `Get Contents of URL` using POST JSON.
- Input: on-device `WebhookURL`, `AIRequest`.
- Output variable: `AIResponse`.
- Prompt text: none.
- Branch condition: 2xx JSON → Step 32; timeout/network/non-2xx → Step 34.
- Expected result: one bounded response is returned.
- Failure behavior: do not retry automatically and do not mutate Source/User variables.

### Step 32

- Action: `Get Dictionary from Input`, followed by `If` checks.
- Input: untrusted `AIResponse`.
- Output variable: validated AI fields only.
- Prompt text: none.
- Branch condition: `ok=true`, `schema_version=3`, required keys/bounds valid, project allowlisted → Step 33; otherwise → Step 34.
- Expected result: raw JSON and unknown fields never reach the note.
- Failure behavior: invalid JSON/schema/unknown field goes to fallback.

### Step 33

- Action: `Text`, then `Show Result`, then `Choose from Menu`.
- Input: validated fields formatted by `SHORTCUT_AI_PREVIEW_FORMAT.md`.
- Output variable: `AcceptedAISuggestions`.
- Prompt text: `接受 AI 建議並保存？`
- Branch condition: `接受並保存` → append a clearly labelled unconfirmed AI section and Step 35; `只保存原始筆記` → Step 35 without AI; `取消` → Step 16.
- Expected result: user sees mobile-friendly text, never raw JSON.
- Failure behavior: any formatting issue goes to Step 34.

### Step 34

- Action: `Choose from Menu`.
- Input: AI error while Source/User variables remain unchanged.
- Output variable: `AIFailureChoice`.
- Prompt text: `AI 整理失敗`.
- Branch condition: `保存原始筆記` → Step 35; `重試` → Step 29; `取消` → Step 16.
- Expected result: failure cannot erase the capture.
- Failure behavior: repeated failure still offers Quick Save; never claim AI succeeded.

### Step 35

- Action: `Text`, then `URL Encode` × 3.
- Input: `VaultID`, `Filename=00_Inbox/<Timestamp>`, final Markdown.
- Output variable: `EncodedVault`, `EncodedFile`, `EncodedContent`.
- Prompt text: none.
- Branch condition: continue to Step 36.
- Expected result: each URI component is encoded separately and Inbox remains flat.
- Failure behavior: if `VaultID=EXAMPLE_VAULT_ID` or blank, show `請先在裝置填入私人 Vault ID。` and stop.

### Step 36

- Action: `Text`.
- Input: encoded variables.
- Output variable: `ObsidianURI`.
- Prompt text: none.
- Branch condition: build `obsidian://new?vault=[EncodedVault]&file=[EncodedFile]&content=[EncodedContent]`.
- Expected result: URI contains no `overwrite` and targets one direct Inbox note.
- Failure behavior: if URI is too long, return to preview and shorten only user-approved text; do not drop raw content silently.

### Step 37

- Action: `Open URLs`.
- Input: `ObsidianURI`.
- Output variable: none.
- Prompt text: none.
- Branch condition: terminal after handoff.
- Expected result: Obsidian receives the create-note request.
- Failure behavior: show `未能交給 Obsidian；請返回預覽複製內容。`; do not claim note creation or sync.

### Step 38

- Action: `Show Notification`.
- Input: URI handoff result only.
- Output variable: none.
- Prompt text: `已交給 Obsidian；請確認筆記及 Remotely Save 狀態。`
- Branch condition: terminal.
- Expected result: status wording stays within observed evidence.
- Failure behavior: never display `已同步` unless the user verifies sync separately.

## Build completion check

- Fast path works with airplane mode and AI disabled.
- Preview occurs before both Quick Save and AI save.
- Cancel at every menu creates no note.
- Source/User/AI layers remain separate.
- `EXAMPLE_VAULT_ID` is replaced only on device.
- Complete Scenario 1 and Scenario 3 in `docs/TRAVEL_E2E_ACCEPTANCE.md`; keep status pending until observed.
