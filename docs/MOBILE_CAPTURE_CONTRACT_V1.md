# Mobile Capture Contract v1

## Status

`IMPLEMENTATION_CONTRACT_COMPLETE` for offline reference use.

`DEVICE_ACCEPTANCE_PENDING`. This contract has not been proven on an iPhone,
in Obsidian Mobile, or through Remotely Save.

## Purpose

This is the one canonical representation used to compare the future Shortcut,
the mobile Markdown note, the optional enrichment request, and the existing
JSON fallback. The existing handoff schema remains a separate, supported
desktop-import contract.

The primary layer order is always:

```text
Source material → confirmed user reflection → optional AI Suggestions
```

AI output must never overwrite or silently upgrade source or user content.

## Canonical Fields

| Field | Required | Meaning | Limit |
|---|---:|---|---:|
| `schema_version` | yes | Contract version; exactly `"1"` | fixed |
| `captured_at` | yes | ISO-8601 timestamp with UTC offset | seconds retained |
| `source_type` | yes | One source enum below | fixed enum |
| `source` | yes | URL, public-safe filename, or blank | 2,048 characters |
| `raw_content` | yes | Original user-entered or shared material | 50,000 characters |
| `insight` | yes | User answer to the first reflection question | 2,000 characters |
| `context` | yes | User answer to the second reflection question | 2,000 characters |
| `action` | yes; blank allowed | User answer to the optional third question | 1,000 characters |
| `output_goal` | yes | One output goal enum below | fixed enum |
| `project` | yes; blank allowed | User-confirmed project, never an AI guess | 200 characters |

Unknown fields are rejected by the offline reference validator. Line endings
are normalized to `LF`; whitespace inside Raw Content is otherwise preserved.
Raw Content, Insight, and Context must contain non-whitespace text. Action and
Project may be blank.

## Canonical Concepts

### Raw Content

Original user-entered or shared material. It is immutable evidence input and
must never be overwritten, summarized in place, trimmed, or corrected by AI.

### Source

The origin of the capture. Supported source types are:

```text
personal
clipboard
voice_transcript
url
shared_text
image_reference
file_reference
```

For `url`, Source must be the original HTTP or HTTPS URL. P0 does not fetch the
page. For image or file references, Source may contain a public-safe filename;
it must not contain an absolute local path or attachment bytes.

### Insight

The user's answer to:

```text
這裡最值得記住甚麼？
```

It is confirmed user interpretation, not an AI summary.

### Context

The user's answer to:

```text
它可以幫我處理甚麼？
```

It may describe a project, problem, decision, content idea, learning objective,
or future work. It is free text and does not force classification.

### Action

The user's answer to:

```text
如果要用到它，我下一步可以做甚麼？
```

It is optional and may be left blank for later review.

### Output Goal

The optional compact menu is normalized to one English enum:

| Value | Display label |
|---|---|
| `collect` | 只收藏 |
| `task` | 任務 |
| `content` | 內容素材 |
| `project_knowledge` | 專案知識 |
| `progress` | 工作進度 |
| `decision` | 決策記錄 |

The Shortcut may default to `collect`; it must not ask for category, tags,
priority, deadline, confidence, or duplicate status during normal capture.

### Project

An optional user-confirmed project. Blank means no reliable project is known.
AI may later suggest only an allowlisted project, and that suggestion remains
separate until the user accepts it.

### AI Suggestions

Optional, unconfirmed enrichment returned in a versioned response envelope.
It is never part of Raw Content, Insight, Context, or Action. Quick Save omits
the entire `## AI 整理建議` section. AI failure must preserve every confirmed
field and offer Quick Save.

## Markdown Mapping

```text
raw_content → ## 原始內容
insight     → ## 最值得記住
context     → ## 可以幫我處理
action      → ## 下一步
AI result   → ## AI 整理建議 (only after user review)
```

Frontmatter contains only lightweight workflow fields. Multiline user content
stays in body sections. Project may be blank; no large tag array is generated.

## Filename and Collision Rule

The default direct-Inbox filename is:

```text
00_Inbox/YYYY-MM-DD-HHmmss
```

No title is required during capture. A later review may rename the file or
improve `# Quick Capture`. If a second capture occurs in the same second, the
caller must add an explicit numeric suffix such as `-2` before opening
Obsidian. The reference renderer exposes this behavior deterministically; it
does not inspect a Vault for collisions.

## Obsidian URI Contract

```text
obsidian://new?vault=<encoded>&file=<encoded>&content=<encoded>
```

Vault, file, and content are encoded independently using standard percent
encoding. Exactly one of each query parameter is produced. The reference tool
constructs this string but never opens it or infers a Vault identifier.

## Implementation Oracle

`tools/mobile_capture_reference.py` provides dependency-free pure functions:

```text
normalize_capture_input
validate_mobile_capture
render_mobile_markdown
build_mobile_filename
build_obsidian_uri
```

It is a development/test oracle, not the primary product runtime. It performs
no Vault access, network request, AI call, or Obsidian action.

## Legacy Mapping

The existing version-1 mobile JSON handoff is preserved unchanged. When a
future manual migration is required, map concepts explicitly:

```text
handoff content            → Raw Content
handoff source URL         → Source
mobile why_keep            → Insight
mobile immediate_application → Context
mobile next_action         → Action
```

No automatic conversion is added in this stage.
