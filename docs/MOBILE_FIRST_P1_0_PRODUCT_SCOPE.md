# Mobile-first P1.0 Product Scope

## Status

```text
GATE A USER-ACCEPTED
P1.0 OFFLINE CONTRACT VERIFIED
GATE B USER-REPORTED PASS
P1.0 DEVICE ACCEPTED BY USER REPORT
P1.1 SHARE SHEET OFFLINE IMPLEMENTED
GATE C SHARE SHEET DEVICE ACCEPTANCE PENDING
AI NOT IMPLEMENTED ON DEVICE
```

Gate A and Gate B are user-reported device results. They were not verified by
repository automation or Codex, and no private device evidence is stored here.
This file remains the frozen P1.0 scope; P1.1 is specified separately.

## Frozen Scope

P1.0 is exactly:

```text
ONE SHORTCUT
QUICK SAVE ONLY
NO AI
NO SHARE SHEET
```

Shortcut name:

```text
收集靈感到 Obsidian
```

The normal experience is:

```text
Launch
→ choose typed, voice, or clipboard
→ provide Raw Content
→ answer one required reflection question
→ optionally answer two reuse questions
→ preview
→ Save or Cancel
→ Obsidian 00_Inbox
```

Target normal capture time is at most 60 seconds, with a desired observed
median of about 30–45 seconds. These are targets, not measured results.

## Supported Entry Modes

The first menu contains only:

1. `輸入文字`
2. `語音輸入`
3. `使用剪貼簿`
4. `取消`

The normalized source types are:

| Entry mode | `source_type` | `source` |
|---|---|---|
| Typed | `personal` | blank |
| Voice | `voice_transcript` | blank |
| Clipboard | `clipboard` | blank |

## Three-question Model

Required:

```text
這裡最值得記住甚麼？
```

This becomes `Insight`, must contain non-whitespace text, and is used as the
Markdown H1.

Optional:

```text
它可以幫我處理甚麼？（可以留空）
```

This becomes `Context`.

Optional:

```text
如果要用到它，我下一步可以做甚麼？（可以留空）
```

This becomes `Action`.

Blank Context and Action retain their section headings with blank bodies.

## Fixed Defaults

P1.0 does not ask for a title, project, category, priority, deadline, tags,
output type, or AI mode.

```text
project = blank
output_goal = collect
ai_status = none
```

The filename never contains Insight, Raw Content, a URL, or a manually entered
title. It uses:

```text
00_Inbox/YYYY-MM-DD-HHmmss-NNNN
```

`NNNN` is a locally generated four-digit suffix.

## Explicitly Deferred

P1.1 owns Shortcut Input branching, Safari Share Sheet, selected text sharing,
Photos, Files/PDF, and Telegram sharing. The core capture interaction is tested
first.

P1.2 owns Gemini, Make.com, webhooks, AI options, automatic project
classification, and AI-generated metadata.

OCR, PDF parsing, attachment upload, deadline prompts, tag generation, and the
JSON handoff as a normal flow are also excluded from P1.0.

## Product Decision Gate

Gate B must answer whether the Shortcut is meaningfully better than opening
Obsidian and typing directly. Technical note creation alone is insufficient.
