# Universal Voice Capture Contract V1

Status: `CURRENT` / offline reference implementation complete; device and live
AI acceptance pending.

## Product contract

```text
Siri / Shortcut
→ Dictate Text
→ editable transcript confirmation
→ structured extraction or offline fallback
→ preview
→ Obsidian
```

The interaction principle is **speak once, review once, save once**. After
dictation, title, project, tags, type, Insight, Context, and Action questions
are forbidden. Editing the transcript is optional.

This is an additive P1.3 contract. Existing mobile enrichment V1/V2/V3
contracts remain unchanged.

## V3 compatibility decision

The existing Gemini V3 request requires manually supplied `user_insight`,
`user_context`, `user_action`, `output_goal`, `requested_output`, and `project`.
Its response has bounded knowledge-enrichment fields but no separate
`completed`, `in_progress`, `blockers`, `decisions`, or `content_ideas` arrays.
Reusing it would either reintroduce the post-dictation questionnaire or blur
work evidence into knowledge suggestions. P1.3 therefore uses dedicated voice
V1 schemas and prompt instead of modifying or bloating V3.

## Canonical input

```json
{
  "schema_version": "1",
  "captured_at": "",
  "source_type": "voice_transcript",
  "raw_transcript": "",
  "allowed_projects": []
}
```

- `captured_at` is a timezone-aware ISO-8601 device timestamp.
- `raw_transcript` is required, limited to 50,000 characters, and remains the
  authoritative source.
- `allowed_projects` contains at most 20 unique, device-local display names.
  The user does not select one during voice capture.
- Unknown fields are rejected.

## Canonical structured output

```json
{
  "suggested_title": "",
  "capture_type": "mixed",
  "one_sentence_summary": "",
  "completed": [],
  "in_progress": [],
  "next_actions": [],
  "blockers": [],
  "decisions": [],
  "knowledge": [],
  "content_ideas": [],
  "project_updates": [],
  "facts_to_verify": [],
  "related_projects": [],
  "confidence": "medium"
}
```

`capture_type` is one of `work`, `knowledge`, `idea`, `learning`, or `mixed`.
Use `mixed` when several material types occur in one transcript. Do not force
one type.

## Extraction invariants

- Extract only transcript-supported information.
- Never invent completion, deadline, blocker, decision, or project association.
- Empty evidence produces an empty array.
- Preserve ambiguity; use `facts_to_verify` where appropriate.
- Topic mentions alone do not prove progress. `我睇咗一篇講 Agent Pricing`
  must not become `Completed: Agent Pricing project`.
- `related_projects` values must be exact members of `allowed_projects`, and a
  clear transcript association is still required. Uncertainty returns `[]`.
- `聽日要跟進`, `下一步要`, `記得要`, and `之後需要` may be confirmed
  `next_actions` when they express intent.
- `可能可以` and `可以考慮` normally remain knowledge or ideas, not tasks.
- `可以寫成文章`, `可以用來做 proposal`, `可以做 post`, and
  `可以變成 teaching material` enter `content_ideas` unless a separate clear
  commitment is spoken.

The JSON schema and Python validator enforce shape, bounds, types, and project
allowlisting. They cannot independently prove semantic faithfulness; prompt,
preview, user review, and test fixtures enforce that operating boundary.

## Markdown behavior

`tools/voice_capture_reference.py` validates both layers before rendering. The
renderer omits every empty optional section and always retains:

```markdown
## 原始語音轉錄
<exact validated raw_transcript>
```

AI structure is labeled `ai_status: suggested` and
`review_status: unreviewed`. It is never treated as confirmed work evidence.

## Offline and failure behavior

If AI is disabled, unavailable, timed out, returns invalid JSON, or fails
schema validation, immediately render:

```markdown
---
type: voice_capture
ai_status: pending
---
# Voice Capture
## 原始語音轉錄
...
```

The full reference renderer also keeps `created`, `source_type`, and
`review_status`. Capture must not wait for AI, discard the transcript, or ask
the user to dictate again. `ai_status: pending` documents possible later human
or explicit foreground processing; no autonomous retry is implemented.

## Trust and privacy boundary

- Dictation privacy depends on device and OS settings and is not verified here.
- Model output is untrusted and must pass schema validation before preview.
- No repository tool calls AI, network, Obsidian, or a Vault.
- Do not store a real Vault identifier, webhook, token, project list, or
  transcript in the repository.
