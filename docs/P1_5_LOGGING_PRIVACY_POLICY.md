# P1.5 Logging and Privacy Policy

## Allowed production log fields

- `capture_id`;
- processing status and bounded error code;
- processing mode;
- duration in milliseconds;
- service-level health/availability metadata that contains no content.

## Prohibited log content

Never log a transcript, article body, selected text, source URL, project name,
Markdown output, provider prompt/response, auth header/token, API key, cookie,
request body, raw exception object, Vault path, device identifier, or private
company/personal content.

Provider error messages are untrusted. The service maps them to a fixed safe
message before response or storage. Unexpected exceptions return a generic
error and are not exposed as stack traces.

## Retention and access

P1.5 does not implement a log sink or retention policy. Before deployment, the
operator must set the platform to the shortest useful retention, restrict log
access to the single operator, disable request-body capture, and document how
to purge an incident log. This is a production acceptance item, not an offline
claim.

## Data minimization

- SQLite is an operational queue/store, not the canonical knowledge base.
- Backend never reads or writes a real Vault.
- PWA caches only public shell assets, never API responses or raw content.
- Reports are human-selected previews and are never automatically sent or
  published.
- No analytics, telemetry, crash-reporting SDK, RAG, embedding, or external
  indexing dependency is present.

Automated tests assert that logs exclude raw content, source, and auth values.
The repository privacy scan covers tracked files only and does not inspect a
Vault or protected path.

