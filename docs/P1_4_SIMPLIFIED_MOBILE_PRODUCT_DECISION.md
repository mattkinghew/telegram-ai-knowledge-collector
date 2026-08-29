# P1.4 Simplified Mobile Product Decision

Status: `OFFLINE_IMPLEMENTED` / device acceptance pending.

## Decision

The recommended daily mobile surface is reduced to two Shortcuts:

```text
有嘢想講      → 語音閃念
有外部內容    → 收集內容
```

The user should not need to remember schemas, processing layers, note types, or
internal project architecture during normal capture.

## Daily entry rules

### `語音閃念`

```text
Launch → Dictate → optional transcript correction → process or pending → save
```

It never requires title, project, Insight, Context, Action, tags, category,
deadline, or output-type questions. P1.3 Voice Contract V1 remains canonical.

### `收集內容`

```text
Share → detect source → 整理 / 只收藏 / 取消 → save
```

Supported references are URL, shared/selected text, video URL, image filename,
file/PDF filename, and direct-launch clipboard fallback. The primary flow does
not ask for Insight, Context, Action, project, category, or AI provider/model.

`整理` exposes only `一般整理`, `轉短文章`, and `深入建議`. The existing
`project_knowledge` mode stays supported at the contract/configuration layer;
`task`, `decision`, and `learning_note` remain legacy-compatible advanced modes
and are not shown in the P1.4 primary UI.

## Status of earlier Shortcuts

| Earlier Shortcut | P1.4 status |
|---|---|
| `收集靈感到 Obsidian` | Fallback / reference / legacy-compatible |
| `更新專案進度` | Fallback for explicit structured reporting |
| `語音快速記錄` | Replaced as the recommended name by `語音閃念`; contract retained |

No earlier schema, prompt, validator, fixture, or document is deleted. P1.0,
P1.1, P1.2, and P1.3 behavior remains available for regression and recovery.

## Non-goals

- No Web App, API, backend, queue worker, autonomous retry, or deployment.
- No URL fetch, article scrape, browser automation, OCR, file parsing, upload,
  video download, audio extraction, or automatic transcription.
- No direct control of Remotely Save and no claim that local save equals sync.
- No real Vault, private project value, credential, or webhook access.

## Evidence boundary

`tools/two_entry_capture_reference.py` is an offline reference contract. It can
validate, classify, and render fictional inputs; it is not an installed iPhone
Shortcut, live AI service, Obsidian integration, or sync result.
