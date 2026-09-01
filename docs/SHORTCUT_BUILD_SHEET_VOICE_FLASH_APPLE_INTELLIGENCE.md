# Shortcut Build Sheet — 語音閃念 Apple Intelligence Local Assist

Status: optional device enhancement for P1.5. The existing backend contract and
P1.4 local fallback remain authoritative. This is not a new Shortcut.

## Preconditions

- Keep the existing `語音閃念` Shortcut and its final Save/Cancel decision.
- Keep the backend endpoint and token in private Shortcut configuration.
- Use fictional/mock content for acceptance. Never put API keys, Vault paths,
  or private model settings in the Shortcut or repository.
- Local model availability depends on the device and runtime; it is not
  guaranteed to be offline or available on every iPhone.

## Exact action order

1. **Dictate Text** — save the exact output as `RawTranscript`.
2. **Ask for Input** — let the user edit; save as `FinalTranscript`.
3. **Set Variable** — `FinalTranscript`.
4. **Use Model** — transcript cleanup with the prompt below; on unavailable,
   keep `CleanTranscript = FinalTranscript`.
5. **Set Variable** — `CleanTranscript`.
6. **Use Model** — record-type suggestion with the prompt below; accept only one
   allow-listed value, otherwise use manual selection.
7. **Choose from Menu** — show `建議：{{label}}`, then `使用建議` or `改類型`.
8. **Set Variable** — final `RecordType`.
9. **Get Contents of URL** — POST the existing backend request using
   `raw_content = CleanTranscript` and `requested_processing = voice_structure`.
10. **If** validated HTTP success — use backend Markdown.
11. **Otherwise** — run the local structured fallback below.
12. **Open Obsidian** — use the existing `obsidian://new` destination logic.
13. **Show Notification** — processed, or locally saved and pending.

`RawTranscript` and `FinalTranscript` must remain available. Cleanup must never
overwrite the original evidence. `RecordType` is a Shortcut-side display and
routing value; do not add it, `SuggestedRecordType`, or `ai_status` to the P1.5
request because the backend intentionally rejects unknown fields.

## Transcript cleanup prompt

```text
只整理以下語音轉錄的：
- 標點
- 斷句
- 明顯口語贅詞
- 明顯語音辨識錯誤

不得：
- 增加新事實
- 增加 deadline
- 增加人物
- 增加任務
- 增加決策
- 改變原意

保留：
- 中英混合
- 專有名詞
- 技術名稱

只輸出修正後內容。
```

## Record-type suggestion prompt

```text
根據以下內容，判斷最適合的記錄類型。

只可以輸出以下其中一個值：
free
daily_control
work_log
reflection
todo
meeting_followup

不要解釋。

內容：
{{CleanTranscript}}
```

The user must explicitly choose the suggestion or override it through the
existing menu. Never silently accept local classification.

## Backend request boundary

```json
{
  "schema_version": "1",
  "capture_type": "voice",
  "source_type": "voice_transcript",
  "raw_content": "{{CleanTranscript}}",
  "requested_processing": "voice_structure"
}
```

Omitted `source` and `allowed_projects` retain the backend defaults. The local
assist prompt, model response, `RawTranscript`, `RecordType`, and local model
configuration are not sent to the backend.

## Local structured fallback

Run only when the backend is unavailable, times out, returns a malformed or
invalid response, or returns a safe failure. Use `CleanTranscript` and
`RecordType` to produce a lightweight draft, set `ai_status = local_suggested`,
and label it as locally suggested. Do not claim backend validation. Preserve
`FinalTranscript` under `## 原始語音記錄` and preserve uncertainty under
`待確認事項`.

For `daily_control`, use the existing daily-control template with unchecked
items by default. Only mark a task complete when the transcript explicitly
states completion; never invent owners, deadlines, decisions, or assignments.
For `free`, `work_log`, `reflection`, `todo`, and `meeting_followup`, keep the
same lightweight rule: structure only stated content and leave unknown fields
blank or under `待確認事項`.

If Apple Intelligence is unavailable, use `FinalTranscript` and the existing
manual RecordType menu. If the backend is also unavailable, save the current
P1.4 raw/pending note instead. Capture must not fail because local AI is absent.
