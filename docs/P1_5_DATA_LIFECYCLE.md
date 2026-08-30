# P1.5 Data Lifecycle

1. `POST /api/v1/capture` validates the complete request before creating a row.
2. The store assigns an opaque UUID and writes `source`, `raw_content`, requested
   processing, project allowlist, and timestamps with status `pending`.
3. Processing changes status to `processing`. It does not mutate the original
   source or raw content.
4. A successful provider result is validated, stored separately as structured
   JSON, and rendered into separate Markdown. Status becomes `processed`.
5. Fetch/provider failure stores a bounded error code/message and returns to
   `pending`; unexpected internal failure becomes `failed`. Original capture
   fields remain present.
6. Manual retry clears the previous error, increments `retry_count`, and runs
   processing again. The maximum is two; there is no background retry loop.
7. Review may change only `reviewed` and an allowlisted project assignment.
   Dismiss sets operational `processing_dismissed`; neither deletes raw data.
8. Report preview reads only explicitly selected IDs and creates an in-memory
   response. It does not send, publish, or create a Vault note.

P1.5 has no API delete route, retention job, automatic cleanup, automatic move,
or automatic export. Database/disk removal is an explicit operator action
outside the application and requires a backup/retention decision. The portable
canonical artifact remains Markdown delivered locally by the Shortcut.
