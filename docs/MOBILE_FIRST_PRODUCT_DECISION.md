# Mobile-first Insight Capture Product Decision

## Status

Proposed and specified. Not yet device-accepted.

This decision changes product priority, not the verified status of the existing
CLI or JSON handoff. No iPhone Shortcut, Obsidian URI, Remotely Save flow, or
Make.com/Gemini scenario has been built or tested by this design package.

## Decision

The primary product experience will be a single mobile-first capture flow:

```text
Text / URL / Dictation / Shared Item
→ one iPhone Shortcut
→ three core questions
→ optional AI enrichment
→ user preview
→ Obsidian URI
→ direct 00_Inbox note
→ Remotely Save sync
```

Quick Save is the default reliability path. It must work without Gemini,
Make.com, a Mac, Terminal, or the JSON handoff. AI enrichment is optional,
reviewed by the user, and must fall back to Quick Save when unavailable or
invalid.

## Previous Primary Flow

```text
Mobile JSON
→ manual transfer
→ desktop validate
→ preview
→ import
→ Obsidian
```

This remains a controlled fallback. Its existing privacy, protected-path,
validation, preview, and explicit-import guarantees are not removed or
weakened.

## Product Roles

### Primary

- Obsidian Mobile for reviewed note creation.
- One iPhone Shortcut for normal text, URL, dictation, image, and file capture.
- Remotely Save for user-configured synchronization after the local note is
  created.

### Optional enrichment

- Make.com receives only input the user has reviewed.
- Gemini returns schema-constrained suggestions.
- The user accepts or rejects suggestions before the note is created.

### Desktop integrity and maintenance toolkit

The existing CLI remains the verified desktop toolkit for:

- validation;
- protected-path enforcement;
- duplicate review;
- bounded metadata search;
- date audit;
- report generation;
- controlled JSON fallback.

### Fallback

The existing versioned JSON mobile handoff remains available when direct mobile
capture is unsuitable or when a controlled desktop validation step is desired.

## P0/P1 Boundaries

P0 specifies local Markdown construction and an `obsidian://new` Quick Save.
It does not fetch webpages, run OCR, parse documents, upload attachments, or
call AI.

P1 specifies optional Make.com/Gemini enrichment. It does not fetch URLs,
upload attachments, write to Obsidian automatically, run in the background, or
store data permanently unless the user explicitly configures an approved
storage policy.

Images and files are never silently discarded. P0 records their source type,
filename when available, and the user's description. The actual binary is not
embedded in the request or note by this design.

## Safety and Product Principles

- Raw content is immutable input and remains separate from AI suggestions.
- Three default questions maximum; additional context is conditional.
- Preview and explicit confirmation precede every save.
- Notes are created only as unique direct children of `00_Inbox`.
- Private employer and client names are not hard-coded.
- Vault identifiers, webhook URLs, and credentials are configuration values,
  never repository content.
- AI output is suggestion, not confirmed fact.
- Capture must not fail solely because AI is unavailable.
- The Shortcut must not delete, move, publish, archive, or overwrite notes.

## Evidence Required Before Product Claim Changes

Do not update README product claims until the actual Shortcut has been built and
the acceptance checklist has been executed on a real device. At minimum,
evidence must show Share Sheet, no-input, URI encoding, failure fallback,
direct-Inbox creation, and Remotely Save synchronization behavior.
