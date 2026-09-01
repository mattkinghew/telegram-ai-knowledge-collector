# P1.5.x Apple Intelligence Local Assist — Device Acceptance

Status: preparation only. Record only user-observed iPhone evidence; repository
tests do not prove Shortcut execution or Apple Intelligence availability.

## Test data

Use fictional/public-safe text only. Do not use real Vault content, employer or
client material, credentials, or private model configuration.

Suggested voice input:

`今日完成 Project Alpha 嘅 CSV mapping，下一步要測 invalid URL，另外想到可以寫一篇 AI pricing short post。`

## Acceptance cases

| Case | Action | Record user-observed result |
|---|---|---|
| A | Dictate, edit, run cleanup | Cleanup improves punctuation/segments without changing facts; `FinalTranscript` remains available |
| B | Run suggestion | Exactly one allow-listed `SuggestedRecordType` is shown |
| C | Choose **使用建議**, then repeat and choose **改類型** | Final `RecordType` follows the explicit user choice |
| D | Backend reachable with `AI_PROVIDER=mock` | Authenticated request succeeds, backend Markdown is returned, Obsidian note opens, raw transcript is preserved |
| E | Make backend unreachable or force a safe failure | Local structured fallback is saved with `ai_status = local_suggested`; no backend success is claimed |
| F | Disable/unavailable Apple Intelligence | Existing manual RecordType path still reaches backend or the P1.4 raw/pending fallback |

## Evidence fields

- Date/time and device model, if the user chooses to record them
- Case A–F result: PASS / FAIL / NOT RUN
- Whether original `FinalTranscript` was preserved
- Whether the user accepted or overrode the suggestion
- HTTP status and capture status for Case D only
- Whether local Obsidian write occurred
- For Case E, fallback status and whether manual retry remained possible
- Any observed error message, excluding tokens, prompts, raw private content,
  and provider responses

## Boundaries

- Apple Intelligence is optional and device/runtime-dependent; do not claim it
  is always offline.
- The backend remains authoritative for validated structured processing.
- Local fallback is a draft only and must retain uncertainty.
- Do not mark this document as accepted until the user supplies direct device
  observations for the relevant cases.
