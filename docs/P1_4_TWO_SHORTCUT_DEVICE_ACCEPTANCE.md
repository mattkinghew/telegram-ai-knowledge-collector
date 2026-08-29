# P1.4 Two-Shortcut Device Acceptance

Overall status: `MANUAL_ACCEPTANCE_PENDING`.

Repository tests do not prove iPhone, Siri, dictation, Shortcuts, Obsidian,
Remotely Save, Make/Gemini, or network behavior. Use fictional or public-safe
content and record observed evidence only.

| Field | Record |
|---|---|
| Device / OS | |
| Shortcut version | |
| Pass / Fail | |
| Capture time | |
| Local note observed | Yes / No |
| Sync observed | Pass / Fail / Not tested |
| Unexpected prompt | |
| Data loss / mutation | |

## Scenario A — Voice

```text
launch 語音閃念 → speak once → optional correction → 保存
```

Pass only if there are no title/project/Insight/Context/Action/category/output
questions, the exact confirmed transcript remains in Markdown, cancellation
creates no note, and the status message does not claim sync.

## Scenario B — Content

Test one URL and one selected/shared text:

```text
Share → 收集內容 → 整理 → 一般整理 → 保存
```

Pass only if source classification requires no manual category, the URL/text is
exact, URL-only does not produce a false summary, and one local note is observed.

## Scenario C — Offline

Disable live AI or connectivity, then run one voice and one content capture.
Pass only if both save locally with full source text/reference,
`ai_status: pending` where processing was requested, no automatic retry starts,
and `只收藏` remains `ai_status: none`.

## Scenario D — Sync

Confirm as four separate observations:

1. `Sync on Save` or the intended Remotely Save mode is enabled.
2. Obsidian opens after the Shortcut URI handoff.
3. The note exists locally with expected content.
4. The same note later appears on the approved remote/second device.

Do not mark Scenario D passed from a notification alone.
