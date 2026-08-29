# P1.4 Offline Behavior

Status: `OFFLINE_IMPLEMENTED` / device acceptance pending.

## Voice

```text
device dictation produces text
→ preserve confirmed transcript
→ AI unavailable or disabled
→ ai_status: pending
→ local Obsidian URI handoff
```

The repository does not claim that dictation itself works offline; that depends
on device, language, operating-system settings, and provider configuration. If
no transcript is produced, stop without saving invented content.

## Content

- Shared/selected/clipboard text: preserve exact text and save locally.
- URL only: preserve exact URL; processing remains `pending`.
- Video URL: preserve URL and only any user-supplied takeaway/shared text; do
  not claim a transcript.
- Image/file/PDF: preserve a safe filename reference only; do not access bytes.
- `只收藏`: `ai_status: none`; no network call.
- `整理` while AI/content is unavailable: `ai_status: pending`; no data loss.

## Recovery

Before URI construction, keep the complete Markdown in a Shortcut variable.
If timestamp, encoding, Vault placeholder validation, Obsidian handoff, or AI
processing fails, display that draft for manual copy. Do not silently shorten
or discard raw content.

## Sync

Offline local availability is not proof of remote availability. Remotely Save
may run later after connectivity returns. P1.4 does not control it and does not
display `已同步` without a separately observed result.
