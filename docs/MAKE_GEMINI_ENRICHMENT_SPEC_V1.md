# Make.com and Gemini Enrichment Specification v1

## Status

Proposed and specified. Not configured or executed. No importable Make.com
blueprint is supplied because no sanitized exported blueprint was provided.

This file is preserved as the V1 contract. New P0.9 implementation should use
`MAKE_GEMINI_ENRICHMENT_SPEC_V2.md`, the version-2 schemas, and the version-2
Knowledge Enrichment prompt. V1 field names and response semantics are not
silently changed.

## Purpose

This optional P1 scenario enriches one user-reviewed mobile request. It returns
suggestions only. It does not own capture reliability and never writes to
Obsidian.

```text
Custom Webhook
→ validate request
→ Gemini structured-output call
→ parse and validate response
→ return JSON
```

Quick Save remains available before, during, and after every scenario failure.

## Scenario Modules

### 1. Custom Webhook

- Accept `POST` with `Content-Type: application/json`.
- Apply an explicit body-size limit compatible with the request schema.
- Receive only the fields in
  `schemas/mobile-insight-request-v1.schema.json`.
- Do not accept credentials, local absolute paths, or raw attachment bytes.
- Configure webhook authentication in Make.com if required; never place a
  secret in the repository, Obsidian note, or public documentation.

### 2. Validate required request fields

Reject before the model call when:

- JSON is malformed;
- required fields are absent;
- unknown fields exist;
- values exceed schema bounds;
- `source_type=url` does not have an HTTP/HTTPS `source`;
- a non-URL source contains a local absolute path;
- an output goal is outside the enum;
- `allowed_projects` exceeds its limit or contains duplicates.

The JSON Schema is the machine-readable contract. Make.com validation must also
enforce platform controls that the schema engine does not support consistently.

### 3. Gemini structured-output call

- Store the Gemini credential only in an authorized Make.com connection.
- Use `prompts/gemini-mobile-enrichment-v1.md` as the behavioral instruction.
- Provide the validated request object, including `allowed_projects`.
- Request JSON structured output matching
  `schemas/mobile-insight-response-v1.schema.json`.
- Do not add fetched URL content or attachment data.

### 4. Parse and validate response

Reject the response when:

- it is not one complete JSON object;
- a required field is absent or an unknown field exists;
- `key_points` contains more than three entries;
- `note_type` or `confidence` is outside its enum;
- `related_project` is neither `null` nor an exact member of the request's
  `allowed_projects`;
- a value exceeds its bound.

The `related_project` membership rule is a cross-payload check and must run
after JSON Schema validation.

### 5. Return JSON response

On success, return the validated response object directly with HTTP 200 and
`Content-Type: application/json`. Do not return model prose, Markdown, internal
module output, or credential details.

Example failure:

```json
{
  "ok": false,
  "error_code": "AI_UNAVAILABLE",
  "message": "AI enrichment is unavailable. Save the original note instead."
}
```

Recommended failure mapping:

| HTTP | `error_code` | Meaning |
|---:|---|---|
| 400 | `INVALID_REQUEST` | Request failed validation |
| 413 | `REQUEST_TOO_LARGE` | Configured size limit exceeded |
| 422 | `INVALID_AI_RESPONSE` | Model output failed validation |
| 429 | `RATE_LIMITED` | Provider or scenario limit reached |
| 502 | `AI_UNAVAILABLE` | Provider unavailable or call failed |
| 504 | `AI_TIMEOUT` | Processing exceeded timeout |

Messages must be safe for display. Do not include provider payloads, stack
traces, connection identifiers, or secrets.

## Data and Security Boundaries

- No API key in Shortcut.
- No API key in Obsidian.
- No credential in repository.
- No automatic Obsidian write from Make.com.
- No URL fetch in P1.
- No attachment upload in P1.
- No background processing.
- No permanent storage unless explicitly configured and privacy-approved.
- No logging of raw content unless explicitly approved and minimized.
- No employer, client, health, credential, or personal data without
  authorization for the complete device-to-provider flow.

The user must review provider retention, regional processing, Make.com history,
and Gemini data-use settings before sending real content. This document does
not assert a specific current policy.

## Operational Controls

- Configure a bounded scenario timeout.
- Return one response for one request; do not queue background work.
- Use scenario history only as necessary for testing, then apply an approved
  retention policy.
- Redact or disable raw request/response logging where platform controls allow.
- Never treat retries as permission to create a note. Only the user-confirmed
  Shortcut opens Obsidian.
- The Shortcut must treat every failure as recoverable through Quick Save.

## Validation Before Enabling

1. Use only sanitized sample data.
2. Confirm request rejection for unknown fields and non-HTTP sources.
3. Confirm response rejection for a fourth key point and disallowed project.
4. Confirm provider timeout produces the documented failure object.
5. Confirm no raw request is retained beyond the approved setting.
6. Confirm the Shortcut previews successful suggestions.
7. Confirm all failure paths preserve raw content and offer Quick Save.
