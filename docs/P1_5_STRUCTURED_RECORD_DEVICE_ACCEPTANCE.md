# P1.5.x Structured Record Device Acceptance

Status: `PENDING`. This is a manual iPhone acceptance worksheet; repository
tests do not count as device evidence. Use only fictional or public-safe voice
text and the existing `語音閃念` Shortcut.

## Procedure

For each record type, run:

```text
voice → cleanup → explicit RecordType choice → authenticated backend
→ MockProvider → inspect deterministic Markdown → local Obsidian note
```

Do not use a real Vault, Remotely Save credential, Gemini credential, or private
work content. Preserve the confirmed transcript and compare it with the
`## 📝 原始語音記錄` section.

## UTF-8 device check

Include `繁體中文`, `English`, an emoji, and technical terms such as
`Gemini API`, `Cloud`, `RecordType`, and `AI Agent` in one fictional capture.
Quick Look must show readable `每日控制台`, `系統防呆檢查`, `今日時間箱`, and
`原始語音記錄` headings. Reject the case if mojibake appears, such as
`æ...`, `å...`, or `ç...`.

## Cases

| RecordType | Fictional input | HTTP status | capture status | Markdown inspected | raw preserved | Pass/Fail |
|---|---|---|---|---|---|---|
| `daily_control` | 「完成 fictional sync；AI learning 仲要 verify。」 | | | | | |
| `work_log` | 「完成 fictional CSV mapping，下一步測試 fallback。」 | | | | | |
| `reflection` | 「今日 fictional review 順利，但測試 coverage 可以改善。」 | | | | | |
| `todo` | 「下一步檢查 fictional endpoint；日期未有明確提及。」 | | | | | |
| `meeting_followup` | 「fictional meeting 提到 API contract；未指定負責人。」 | | | | | |
| `free` | 「這是一則 fictional free capture。」 | | | | | |

## Evidence fields

- device and capture time:
- selected RecordType and whether it was overridden:
- HTTP success and authenticated request:
- `capture_id`:
- `status = processed`:
- expected template headings visible:
- local note created:
- original confirmed transcript preserved:
- no duplicate observed:
- Remotely Save observed (if used):
- user observation / Pass or Fail:

Only the user's device observation can change this document from `PENDING` to
an accepted result. Do not record tokens, headers, full private payloads, or
provider raw responses.
