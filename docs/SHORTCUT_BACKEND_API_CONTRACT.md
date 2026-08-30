# Shortcut Backend API Contract

Status: P1.5 current hybrid contract. P1.4 local capture remains the mandatory fallback.

## Shortcut-owned fields

The Shortcut may know only:

- endpoint URL;
- optional bearer token stored outside the repository;
- `capture_type`, `source_type`, `source`, `raw_content`;
- `requested_processing` and up to eight `allowed_projects`.

It must not contain a Gemini prompt, model name, provider response schema,
provider-specific retry logic, or a Vault path.

## Request

`POST /api/v1/capture` with `Content-Type: application/json` and, when token
authentication is enabled, `Authorization: Bearer <user-configured-token>`.

```json
{
  "schema_version": "1",
  "capture_type": "voice",
  "source_type": "voice_transcript",
  "source": null,
  "raw_content": "Fictional transcript for local testing.",
  "requested_processing": "voice_structure",
  "allowed_projects": ["Fictional Project"]
}
```

Accepted processing modes are `raw_save`, `voice_structure`, `summary`,
`recommendation`, `short_article`, and `project_knowledge`. The API rejects
unknown fields and unsupported capture/source/mode combinations.

## Success and local delivery

HTTP 200 with `ok: true`, `status: processed`, an opaque `capture_id`, and
`result.markdown` is a processed success. The Shortcut must still ask Obsidian
to create the local note; the backend never writes to a Vault.

Validate all four conditions before using backend Markdown:

1. HTTP status is 200.
2. `ok` is exactly true.
3. `status` is exactly `processed`.
4. `result.markdown` is a non-empty string.

## Accepted pending response

HTTP 202 with `ok: false`, `status: pending`, `capture_id`, and `error_code`
means the operational record exists but smart processing did not complete.
The Shortcut must create the normal P1.4 local raw/pending note. It must not
substitute an error message for the original user content.

Expected error codes include `NETWORK_UNAVAILABLE`, `AI_UNAVAILABLE`,
`AI_TIMEOUT`, `INVALID_AI_JSON`, `SCHEMA_MISMATCH`, `URL_FETCH_FAILED`,
`UNSUPPORTED_CONTENT_TYPE`, `PAYLOAD_TOO_LARGE`, `INVALID_REQUEST`, and
`INTERNAL_ERROR`.

## Backend unreachable contract

Timeout, DNS failure, TLS failure, no response, malformed JSON, HTTP 4xx/5xx,
or an invalid success envelope all take the same local-safe branch:

```text
retain original input
-> build P1.4 raw/pending Markdown locally
-> open obsidian://new
-> show that smart processing remains pending
```

Do not automatically retry in a loop. A later human action may use
`POST /api/v1/captures/{capture_id}/retry` when a capture ID exists. The API
permits at most two manual retries.

## Limits and privacy

- Total request body: 128 KiB.
- `raw_content`: 50,000 characters.
- `source`: 2,048 characters.
- `allowed_projects`: at most eight names, each at most 80 characters.
- HTTP/HTTPS URL only for URL source types; image/file references are safe
  filenames only.
- Do not send credentials, private company files, real Vault paths, or
  protected-path content.
- Never log or display the bearer token.
