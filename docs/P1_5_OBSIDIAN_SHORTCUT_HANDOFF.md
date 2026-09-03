# P1.5 Obsidian Shortcut Handoff

## Scope and boundary

The backend returns Markdown and handoff metadata; it never opens, scans, or
writes an Obsidian Vault. The iPhone Shortcut owns the local write. Remotely
Save remains an Obsidian-side sync responsibility.

```text
iPhone Shortcut → POST /api/v1/capture → capture_id
                                  ↘ pending/processing
Shortcut → GET /api/v1/captures/{capture_id} → result.markdown + handoff
Shortcut local write → Obsidian local file → Remotely Save sync
```

Only fictional or user-approved local test content belongs in acceptance tests.
Do not place a Vault path, Vault identifier, credential, or secret in the API
payload or this repository.

## Response contract

Existing `result.markdown` and `result.provider_result` remain unchanged. A
successful response adds `result.obsidian_handoff`:

```json
{
  "markdown": "# Fictional capture\n",
  "suggested_filename": "2026-09-03-Fictional capture.md",
  "suggested_date": "2026-09-03",
  "record_type": "free",
  "title": "Fictional capture",
  "folder_key": "free"
}
```

`folder_key` is logical only. The device may map it to a local folder:

| Logical key | Suggested local folder |
| --- | --- |
| `daily_control` | `Daily` |
| `work_log` | `Work` |
| `reflection` | `Reflection` |
| `todo` | `Tasks` |
| `meeting_followup` | `Meetings` |
| `free` | `Inbox` |

The device layer may override these labels. The backend does not know the
resulting absolute folder path.

## Async mobile capture contract

When the live Gemini provider is selected, `POST /api/v1/capture` persists the
raw capture and returns promptly with HTTP `202`, `status: "pending"`, and
`error_code: "PROCESSING_QUEUED"`. The server then processes that same
`capture_id` in a bounded background task. MockProvider keeps its existing
immediate processed response for compatibility and fast acceptance tests.

The authenticated Shortcut must poll `GET /api/v1/captures/{capture_id}`:

1. POST once and save `capture_id` plus the original raw input in Shortcut
   variables.
2. If the response is `processed`, consume its `result` immediately.
3. If it is `pending` or `processing`, wait 2 seconds and GET the status again.
4. Repeat for at most 15 attempts (30 seconds total), then stop with a
   user-facing "still processing; retry later" message. Never poll forever.
5. Stop immediately on `processed` or `failed`. For `failed`/`pending` with an
   error, retain `capture_id` and use the authenticated manual retry action;
   do not create a duplicate capture.

The GET response is the persisted capture record. On success it contains
`status: "processed"`, `raw_content`, `markdown`, and structured `result`;
the Shortcut uses `result.obsidian_handoff.markdown` and
`result.obsidian_handoff.suggested_filename` for the local write. On pending
or processing, `result`/`markdown` are absent; raw content remains persisted.

## Filename and duplicate policy

`suggested_filename` is `YYYY-MM-DD-<safe title>.md`. CJK is preserved;
filesystem-invalid characters, control characters, repeated dots, and path
separators are replaced or removed. Whitespace is bounded and the title is
limited to 100 characters. The result is always one filename component with a
`.md` extension.

If the local destination already contains that name, the Shortcut should keep
the original Markdown and append a deterministic numeric suffix:
`...-2.md`, then `...-3.md`, and so on. It must not overwrite an existing note
without an explicit user action. The backend does not inspect the Vault to
detect collisions.

## Exact Shortcut steps

After the existing `MarkdownOutput` extraction (for a processed response):

1. Get Dictionary Value `result` from the processed API response.
2. Get Dictionary Value `markdown` and `obsidian_handoff` from `result`.
3. Read `suggested_filename`, `suggested_date`, `record_type`, `title`, and
   `folder_key` from `obsidian_handoff`.
4. Choose a device-local destination using the logical folder mapping above.
5. Apply the collision rule before writing; never use a path supplied by the
   backend.
6. Write the exact `markdown` string as UTF-8 Markdown.
7. Open the created note in Obsidian and confirm the original source section is
   present.

### Option A — Obsidian URI

Use Obsidian URI or Advanced URI only if the installed version is confirmed to
support safe creation of a new note with encoded file and content values. Encode
vault/file/content independently in the Shortcut. The Vault name or ID stays
in the device Shortcut configuration, not in this backend response.

### Option B — Files action (preferred fallback)

Use Shortcuts `Save File` (or the equivalent local file-write action) to write
the Markdown into the user-selected Obsidian local folder. Do not hardcode an
absolute path in the backend or repository. This option is preferred when URI
creation is unavailable or behaves differently on the installed Obsidian
version.

Both options mean:

```text
Shortcut writes local note → Obsidian sees file → Remotely Save syncs on its own schedule/settings
```

The Shortcut must not claim that Remotely Save completed unless the user
actually observes that sync.

## Failure and rollback

If the API response is pending/failed, do not write a processed note from a
missing `result`. Preserve the returned `capture_id` and raw content for manual
retry through the authenticated API. If a local write fails, keep the Markdown
in Shortcut output/clipboard for review and retry the local write manually.

Rollback is device-local: delete only the fictional/test note created by the
Shortcut, or move it to the device's normal local recovery location. Do not
delete backend captures and do not alter Remotely Save settings as part of this
handoff.

## Privacy checklist

- No real Vault access occurs in backend code or automated tests.
- No absolute Vault path or private folder name is returned by the API.
- Raw content remains in the Markdown and backend capture record; generated
  suggestions are visibly unconfirmed.
- API authentication remains required for capture endpoints.
- Use fictional fixtures for repository and staging acceptance.
- Never place API tokens, provider credentials, or private work content in a
  Shortcut export, log, issue, test fixture, or this document.
