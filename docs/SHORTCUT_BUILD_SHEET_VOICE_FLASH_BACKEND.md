# Shortcut Build Sheet — Voice Flash with P1.5 Backend

Status: current hybrid build sheet. Complete device execution remains pending.

## Preconditions

- Preserve the existing `語音閃念` P1.4 local Markdown builder.
- Configure the endpoint and optional bearer token as private Shortcut values,
  not in Git or note content.
- Set a bounded network timeout. Do not add automatic retry loops.

## Actions

1. **Dictate Text** once and store the exact result as `RawTranscript`.
2. If empty, stop without creating a note.
3. Optionally show **Ask for Input** prefilled with `RawTranscript`; store the
   confirmed value as `FinalTranscript`.
4. Build a dictionary using the minimum contract below. `source` and
   `allowed_projects` may be omitted; the backend defaults them safely.

```text
schema_version = 1
capture_type = voice
source_type = voice_transcript
raw_content = FinalTranscript
requested_processing = voice_structure
```

The backend interprets omitted fields as `source = null` and
`allowed_projects = []`. Include either field only when the Shortcut
intentionally needs a non-default value. URL and file-reference source types
still require a valid `source`.

5. **Get Contents of URL**: POST JSON to `{endpoint}/api/v1/capture`. Add the
   bearer header only when configured.
6. If HTTP 200 and the validated envelope contains processed Markdown, set
   `NoteMarkdown` to `result.markdown` and `AI Status` to `suggested`.
7. Otherwise, run the unchanged P1.4 local builder using `FinalTranscript`, set
   `AI Status` to `pending`, and include a short actionable reason without any
   token or stack trace.
8. URL-encode `NoteMarkdown` and open `obsidian://new` using the already approved
   local destination logic.
9. Show one final notification: processed, or locally saved and pending.

## Failure matrix

| Condition | Required behavior |
|---|---|
| Backend unreachable or timeout | Save exact transcript locally as pending |
| HTTP 401 | Save locally; ask the user to review private auth configuration |
| HTTP 413/422 | Save locally; report invalid/oversized request |
| HTTP 202 pending | Save locally; retain returned capture ID as optional metadata |
| HTTP 500 or malformed response | Save locally; do not expose response internals |
| User cancels before save | Do not send or save |

The backend response is optional enrichment. It is never a prerequisite for the
local note.
