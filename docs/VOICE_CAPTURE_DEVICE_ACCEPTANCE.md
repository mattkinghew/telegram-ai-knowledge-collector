# Voice Capture Device Acceptance

Status: `DEVICE_TEST`. Repository tests do not prove Siri, dictation, iPhone,
Obsidian, Remotely Save, Make, Gemini, or network behavior.

For each test, record observed values rather than expected claims:

| Field | Record |
|---|---|
| Pass / Fail | |
| Capture time | |
| Transcript correction needed | Yes / No |
| Structure useful | Yes / No |
| Wrong classification | |
| Missing information | |
| Remotely Save result | Pass / Fail / Not tested |

### Test 1 — 30-second work update

Speak one completed item, one in-progress item, and one clear next action. Pass
only if the transcript remains exact after optional correction, structure does
not invent progress, preview appears once, and one save creates a reviewable
note.

### Test 2 — Knowledge or article reflection

Speak a takeaway from fictional or public-safe material without claiming a
project. Pass only if it becomes knowledge, not completed work, and project
association stays empty unless explicitly spoken and allowlisted.

### Test 3 — Mixed work and idea

Speak one work update plus `可以寫成文章` without committing to write it. Pass
only if the note uses mixed structure and keeps the article under content ideas,
not next actions.

### Test 4 — Offline or no-AI fallback

Disable `VoiceAIEnabled` or connectivity, then dictate once. Pass only if the
note saves with `ai_status: pending`, includes the full transcript, does not
ask for another dictation, and does not start an automatic retry.

### Test 5 — Cantonese and English mixed speech

Speak a short mixed-language update with punctuation or a technical term. Pass
only if any correction is optional, the final confirmed transcript remains
verbatim in Markdown, and structure does not translate or rewrite the source.

Acceptance remains pending until all five tests contain device-observed evidence.
