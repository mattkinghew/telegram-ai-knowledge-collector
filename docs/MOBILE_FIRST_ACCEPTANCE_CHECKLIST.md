# Mobile-first Insight Capture Acceptance Checklist

## Status

Not yet device-accepted. Every case below is `NOT RUN` until manually executed
on the real device. This file defines acceptance; it is not evidence that the
Shortcut, URI, Remotely Save, Make.com, or Gemini works.

Use sanitized test data and record only privacy-safe evidence references.

This checklist preserves the detailed original cases. Use
`MOBILE_DEVICE_ACCEPTANCE_V2.md` as the current staged execution order and
`IPHONE_SHORTCUT_BUILD_SPEC_V3.md` for the full Shortcut after Stage 1 passes.

## Stage 1 — Minimal Architecture Smoke Test

Run this test before every later device case. Build only the temporary
four-action `BKC Mobile Test` Shortcut specified in
`IPHONE_SHORTCUT_BUILD_SPEC_V2.md`.

- [ ] The Obsidian URI opens without adding Share Sheet, Gemini, OCR, PDF
      extraction, or menus.
- [ ] Exactly one test note is directly visible at
      `00_Inbox/BKC-Mobile-Test`.
- [ ] Traditional Chinese text is intact.
- [ ] Frontmatter and Markdown headings are intact.
- [ ] Remotely Save produces one readable synchronized note at the intended
      approved destination.
- [ ] No duplicate note or sync conflict is observed.
- [ ] No Vault identifier, private path, credential, or private content is
      recorded in repository evidence.

Record the observed result exactly as follows:

```markdown
## Mobile Architecture Test

- Obsidian URI: success / failure
- 00_Inbox note: success / failure
- Chinese: correct / incorrect
- Markdown/YAML: correct / incorrect
- Remotely Save: success / failure
- Duplicate: yes / no
- Sync conflict: yes / no
- Error:
- Screenshot available: yes / no
```

After recording the result, stop. Later device cases remain `NOT RUN` until
Stage 1 is accepted and a later goal is explicitly started.

## Global Acceptance

- [ ] No Mac required.
- [ ] No Terminal required.
- [ ] No JSON handoff required for normal use.
- [ ] One Shortcut handles all normal input modes.
- [ ] Three default questions maximum.
- [ ] Raw content preserved.
- [ ] User preview before save.
- [ ] AI optional.
- [ ] AI failure falls back safely.
- [ ] One Markdown note created directly in `00_Inbox`.
- [ ] No secret or private path written.

## Device Test Cases

| ID | Case and procedure | Expected result | Status |
|---:|---|---|---|
| 1 | Launch with no input, choose `輸入文字`, enter sanitized text, answer the core questions, and Quick Save. | Preview shows the exact raw text; one direct-Inbox note is created without Mac, Terminal, JSON, AI, or AI section. | NOT RUN |
| 2 | Launch with no input, choose `語音輸入`, dictate sanitized text, edit the transcript, confirm, and Quick Save. | Edited transcript is shown before save and preserved as raw content; cancel is available before confirmation. | NOT RUN |
| 3 | Share a public Safari URL and Quick Save. | Exact HTTP/HTTPS URL and shared title when available are recorded; no webpage fetch or invented page summary occurs. | NOT RUN |
| 4 | Share selected text from a supported app. | Exact selected text is preserved separately from user answers and any AI suggestions. | NOT RUN |
| 5 | Share a sanitized screenshot and enter a manual description. | Source type, safe filename when available, and description are recorded; no OCR claim and no silent discard. | NOT RUN |
| 6 | Share a sanitized PDF and enter a manual description. | Source type, safe filename, and description are recorded; no parsing, byte embedding, or upload claim. | NOT RUN |
| 7 | Disable network access or use an unavailable AI endpoint, choose AI Save, then accept fallback. | Error is understandable; all reviewed input remains; Quick Save creates the original note without AI suggestions. | NOT RUN |
| 8 | With the sanitized scenario configured, choose AI Save and accept a schema-valid response. | Suggestions are previewed, explicitly confirmed, and kept under `AI 整理建議`; raw content and user answers remain unchanged. | NOT RUN |
| 9 | Return invalid JSON or an unknown field from the test scenario. | Shortcut rejects enrichment, identifies invalid output without exposing internals, preserves input, and offers Quick Save. | NOT RUN |
| 10 | Cancel once during input review and once at the final save menu. | No Obsidian URI opens, no note is created, and no network call occurs after cancellation. | NOT RUN |
| 11 | Run two captures within the same second or force the same short title. | Shortcut regenerates timestamp or adds a suffix; two unique notes result and neither overwrites/appends to the other. | NOT RUN |
| 12 | Capture Traditional Chinese text and title. | Frontmatter remains valid and Chinese characters render unchanged in filename/title/body. | NOT RUN |
| 13 | Capture content containing `&`, `#`, `%`, `?`, `=`, `/`, quotes, and line breaks. | Separately URI-encoded vault/file/content values produce intact Markdown with no query truncation or wrong path. | NOT RUN |
| 14 | Test input near the documented 50,000-character bound and then input above it. | In-bound input is reviewed and saved or enriched within device limits; oversized AI request is stopped clearly and can Quick Save without truncating raw content. | NOT RUN |
| 15 | After a successful Quick Save, run or observe the approved Remotely Save sync and inspect the intended second device/location. | The same note appears once at the approved destination; success is recorded only after direct observation. | NOT RUN |

## AI Contract Checks

- [ ] Request rejects unknown fields.
- [ ] Request rejects non-HTTP/HTTPS URL sources.
- [ ] Request contains no credentials, absolute local paths, or attachment bytes.
- [ ] Response has at most three key points.
- [ ] Response uses only an allowed project or `null`.
- [ ] Response uses only the documented `note_type` and `confidence` enums.
- [ ] Uncertain scalar/list output uses `null`/empty array.
- [ ] AI suggestions are not labelled as confirmed facts.

## Privacy and Failure Checks

- [ ] Dictation provider and privacy settings reviewed.
- [ ] Remotely Save destination and scope approved.
- [ ] Make.com history and retention reviewed.
- [ ] Gemini processing and retention reviewed.
- [ ] No webhook URL, token, Vault path, or account identifier saved in notes or
      repository files.
- [ ] No employer, client, health, credential, or personal data used in tests.
- [ ] Every cancellation and failure leaves no partial note or external write,
      except the explicitly confirmed Quick Save.

## Acceptance Record

Complete only after testing:

```text
Device:
iOS version:
Obsidian version:
Shortcut version:
Remotely Save configuration reference:
Make.com scenario reference:
Test date:
Tester:
Passed cases:
Failed cases:
Evidence location:
Open issues:
Decision: ACCEPTED / NOT ACCEPTED
```

Do not record credentials, webhook URLs, personal Vault paths, or private
content in this file.
