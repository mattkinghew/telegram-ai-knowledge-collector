# iPhone Shortcut P1.0 Action Map

## Status and Boundary

This is the implementation guide for one Shortcut named:

```text
收集靈感到 Obsidian
```

It implements Quick Save only. It does not use Shortcut Input, Share Sheet,
Gemini, Make.com, a webhook, OCR, file parsing, attachment upload, automatic
classification, deadlines, tags, or JSON handoff.

Keep the real Vault identifier only in the local Shortcut. Repository examples
must use `EXAMPLE_VAULT_ID`.

## Stable Variables

Create and retain these variable names:

```text
RawContent
SourceType
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

`RawContent`, `Insight`, `Context`, and `Action` are separate values. Blank
validation may inspect a copy, but must not trim or replace the saved value.

## Phase A — Input Menu

1. Add **Choose from Menu**.
2. Add exactly these menu items:

```text
輸入文字
語音輸入
使用剪貼簿
取消
```

### Typed branch — `輸入文字`

1. Add **Ask for Input** with input type Text.
2. Prompt: `你想記錄甚麼？`
3. Save the result as `RawContent`.
4. Use **Match Text** with `\S` against a copy of `RawContent`.
5. If there is no match, show `請輸入要保存的內容。` and **Stop This
   Shortcut**. Do not open a URI.
6. Set `SourceType` to `personal`.

### Voice branch — `語音輸入`

1. Add **Dictate Text** and store its result temporarily as `Transcript`.
2. Add **Ask for Input** with input type Text.
3. Prompt: `請檢查或修改語音內容`
4. Set the default answer to `Transcript`.
5. Save the edited result as `RawContent`.
6. Use **Match Text** with `\S` against a copy. If there is no match, show
   `請保留要保存的語音文字。` and stop.
7. Set `SourceType` to `voice_transcript`.

The editable confirmation is required. Dictation output is not automatically
verified. This specification makes no privacy or on-device-processing claim
about dictation.

### Clipboard branch — `使用剪貼簿`

1. Add **Get Clipboard**.
2. Convert the result to text without changing its content; set `RawContent`.
3. Use **Match Text** with `\S` against a copy.
4. If there is no match, show `剪貼簿沒有可保存的文字。` and **Stop This
   Shortcut**.
5. Set `SourceType` to `clipboard`.

### Cancel branch — `取消`

Add **Stop This Shortcut**. Do not create a note.

## Phase B — Reflection Questions

After a valid `RawContent` exists:

1. Add **Ask for Input** with input type Text.
   Prompt: `這裡最值得記住甚麼？`
   Store as `Insight`.
2. Use **Match Text** with `\S` against a copy of `Insight`. If there is no
   match, show `請寫下一句最值得記住的內容。` and stop. Do not create a
   note.
3. Add **Ask for Input** with input type Text.
   Prompt: `它可以幫我處理甚麼？（可以留空）`
   Store as `Context`. Blank is valid.
4. Add **Ask for Input** with input type Text.
   Prompt: `如果要用到它，我下一步可以做甚麼？（可以留空）`
   Store as `Action`. Blank is valid.

Do not add another menu after Question 3. Set these constants without asking:

```text
source = blank
project = blank
output_goal = collect
ai_status = none
```

## Phase C — Date and Collision-safe Filename

1. Add **Current Date**.
2. Format it as `yyyy-MM-dd'T'HH:mm:ssXXX`; store as `CreatedAt`.
3. Format the same date as `yyyy-MM-dd-HHmmss`; store as
   `FilenameTimestamp`.
4. Add **Random Number**, minimum `1000`, maximum `9999`; store the result as
   `UniqueSuffix`.
5. Use a **Text** action to set `NoteFile`:

```text
00_Inbox/[FilenameTimestamp]-[UniqueSuffix]
```

This native four-digit random suffix is the P1.0 collision control. Gate B
must still test rapid double capture; offline tests do not prove iOS randomness
or Obsidian collision behavior.

If the installed Shortcuts version labels the action differently, use its
native equivalent that returns one integer from 1000 through 9999, convert the
result to four text digits, and keep the same `NoteFile` pattern. Do not replace
the suffix with Insight, Raw Content, a URL, or a manually entered title.

## Phase D — Markdown

Add one **Text** action and store it as `Markdown`:

```markdown
---
status: inbox
created: [CreatedAt]
source_type: [SourceType]
source:
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

Keep both optional headings when Context or Action is blank. Do not add an AI
section. `Insight` should be one line so the note has one stable H1.

## Phase E — Preview and Decision

1. Display the complete `Markdown` using **Quick Look** or **Show Result**.
2. Add **Choose from Menu** with exactly:

```text
保存
取消
```

3. `取消` uses **Stop This Shortcut**. No note is created.
4. Continue to URI construction only in `保存`.

Do not add a return/edit loop, multiple previews, AI button, or project picker.
P1.0 is measuring capture friction.

## Phase F — Obsidian URI

Only after the user selects `保存`:

1. Set the local `VaultID` value. Documentation uses
   `EXAMPLE_VAULT_ID`; never commit the real value.
2. Apply **URL Encode** separately:
   - `VaultID` → `EncodedVault`
   - `NoteFile` → `EncodedFile`
   - `Markdown` → `EncodedContent`
3. Use one **Text** action to create `ObsidianURI`:

```text
obsidian://new?vault=[EncodedVault]&file=[EncodedFile]&content=[EncodedContent]
```

4. Add **Open URLs** for `ObsidianURI`.

Do not add `overwrite` or `append`. Do not write to a local filesystem path.
The Shortcut may state that it handed the URI to Obsidian; note creation must
be confirmed by direct inspection during Gate B.

## Remotely Save Boundary

The Shortcut does not invoke, configure, monitor, or control Remotely Save.
Its responsibility ends when Obsidian creates the note. Sync acceptance is
tested externally by the user.

## Build Location Options

Option A:

```text
Mac Shortcuts app
→ build or edit the Shortcut
→ user-managed Shortcuts sync
→ run on iPhone
```

Option B:

```text
build directly on iPhone
```

The Mac-to-iPhone Shortcuts sync path has not been tested in this project. Do
not generate or commit an unsigned `.shortcut` package and do not
reverse-engineer Apple's Shortcut file format.
