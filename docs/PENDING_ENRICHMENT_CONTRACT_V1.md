# Pending Enrichment Contract V1

Status: `CURRENT` / local record contract only.

`ai_status: pending` means requested processing was not completed. It never
means a job, worker, retry, backend, or provider call exists.

## Required recoverable fields

```yaml
created: "<timezone-aware ISO-8601>"
source_type: <article_url|social_post|selected_text|video_url|image_reference|file_reference|clipboard_text|voice_transcript>
source: "<exact URL, safe filename, or blank>"
requested_processing: <summary|recommendation|short_article|project_knowledge|voice_structure>
ai_status: pending
```

The note body also retains the exact supplied `raw_content` or
`raw_transcript`. A URL/image/file reference may have blank raw content; this
must remain pending and must not receive a fabricated summary.

## State meanings

| `ai_status` | Meaning |
|---|---|
| `none` | User chose `只收藏`; no processing requested or claimed |
| `pending` | Processing requested but unavailable, unsafe, or unsupported now |
| `suggested` | A validated, unconfirmed suggestion was rendered for review |

P1.4 does not use `processed` because AI output is not confirmed evidence.

## Later processing boundary

A future explicit foreground action may read one user-selected note, revalidate
the fields, ask for data-sharing approval, and produce a suggestion. P1.4 does
not implement that action, autonomous retry, background watcher, queue,
schedule, network service, or Vault scan.
