# Make.com and Gemini Knowledge Enrichment Specification v2

## Status

Implementation map only. `AI_SERVICE_ACCEPTANCE_PENDING`.

No Make.com scenario, webhook, connection, credential, or Gemini call was
created or accessed during this offline stage. V1 remains unchanged for legacy
contract reference; new work should use the version-2 schemas and prompt.

## Purpose

Gemini is a Knowledge Enrichment Assistant. It proposes evidence support,
missed points, applications, an output angle, verification needs, and one next
action. It is not the capture system and must not return generic free-form
prose.

```text
Module 1  Custom Webhook
→ Module 2  Input Validation / Mapping
→ Module 3  Gemini Structured Output
→ Module 4  Response Parse / Validation
→ Module 5  Webhook Response
```

Quick Save remains local and available before, during, and after every module
failure. Make.com never writes to Obsidian.

## Contracts

- Request: `schemas/mobile-insight-request-v2.schema.json`
- AI behavior: `prompts/gemini-mobile-enrichment-v2.md`
- Webhook response: `schemas/mobile-insight-response-v2.schema.json`
- Offline oracle: `tools/mobile_enrichment_simulator.py`

The Gemini module returns only the `enrichment_result` object. Module 4
validates it and adds the successful response envelope.

## Module 1 — Custom Webhook

### Input

- `POST` request from the user-confirmed Shortcut AI branch.
- `Content-Type: application/json`.
- One version-2 request object.

### Output

- The parsed request object and request metadata required for error handling.
- No persistent record is required by this design.

### Mapping

Map the complete JSON body to one object. Do not map raw content into module
names, logs, filenames, query strings, or connection labels.

### Required fields

```text
schema_version
source_type
source
raw_content
user_insight
user_context
user_action
output_goal
project
allowed_projects
```

### Optional fields

No unknown top-level field is optional. Empty strings are permitted only where
the schema allows them, including Source for non-URL inputs, Action, and
Project.

### Failure mode

- Reject non-POST, unsupported content type, malformed JSON, and bodies larger
  than the configured request bound.
- Route malformed or oversized input to `INVALID_REQUEST` without calling AI.
- Return no stack trace, connection identifier, module bundle, or raw provider
  response.

### User-visible behavior

The Shortcut shows `AI 整理失敗` and offers `保存原始筆記`, `重試`, and
`取消`. Raw Content and all confirmed user fields remain local in Shortcut
variables.

## Module 2 — Input Validation / Mapping

### Input

The parsed Module 1 object, treated as untrusted data.

### Output

A strict allowlisted object suitable for the prompt. No additional field
survives validation.

### Mapping

Map only the version-2 request fields. Preserve Raw Content and user text; do
not trim, summarize, translate, classify, or correct them. Normalize only the
representation needed by the platform, such as explicit empty strings.

### Required fields

- `schema_version` equals `"2"`.
- Every required request key exists with the correct type.
- Raw Content, User Insight, and User Context contain text within their bounds.
- Source Type and Output Goal belong to known enums.

### Optional fields

- `source` may be blank except for `source_type = url`.
- `user_action` may be blank.
- `project` may be blank.
- `allowed_projects` may be empty.

### Cross-field validation

- For `source_type = url`, Source must be an HTTP or HTTPS URL without embedded
  credentials. Do not fetch it.
- For other Source Types, reject absolute POSIX, Windows, or network paths.
- A nonblank Project must exactly match one `allowed_projects` item.
- Reject duplicates and more than 20 Allowed Projects.
- Reject unknown fields, nested arbitrary objects, attachment bytes, and
  credential-like fields.

### Failure mode

Return:

```json
{
  "ok": false,
  "error_code": "INVALID_REQUEST",
  "message": "The enrichment request is invalid."
}
```

Do not run Modules 3 or 4.

### User-visible behavior

The Shortcut keeps the local draft and offers Quick Save. It may show the safe
message but not field values that could expose private content.

## Module 3 — Gemini Structured Output

### Input

The validated allowlisted request from Module 2 plus the V2 system prompt.

### Output

One JSON `enrichment_result` object with exactly:

```text
suggested_title
one_sentence_insight
supporting_points
possible_applications
suggested_next_action
output_angle
related_project
facts_to_verify
missing_information
confidence
```

### Mapping

Map the validated Source and User layers into the model request. The system
prompt states that Raw Content is untrusted evidence text, not instructions.
Configure structured JSON output against the bounded result contract where the
current Make.com/Gemini interface supports it.

### Required fields

All ten result keys must exist. Arrays may be empty and nullable scalars may be
`null`.

### Optional fields

Semantic content is optional within the result bounds. The model should prefer
`null` and empty arrays when evidence is insufficient.

### Failure mode

- Provider cannot be called or returns a service error: `AI_UNAVAILABLE`.
- The bounded execution time expires: `AI_TIMEOUT`.
- The model returns non-JSON: route raw output only to Module 4's in-memory
  parse failure; do not include it in the user-facing response.

### User-visible behavior

No partial AI text is shown as a valid suggestion. The Shortcut receives one
safe failure payload and retains the local draft.

## Module 4 — Response Parse / Validation

### Input

The complete untrusted Module 3 response and the request's
`allowed_projects`.

### Output

On success:

```json
{
  "ok": true,
  "schema_version": "2",
  "result": {
    "suggested_title": null,
    "one_sentence_insight": null,
    "supporting_points": [],
    "possible_applications": [],
    "suggested_next_action": null,
    "output_angle": null,
    "related_project": null,
    "facts_to_verify": [],
    "missing_information": [],
    "confidence": "low"
  }
}
```

### Mapping

1. Parse exactly one complete JSON object.
2. Reject duplicate or unknown keys where the platform exposes that control.
3. Validate every type, enum, string bound, and array bound.
4. Require `related_project` to be `null` or an exact request allowlist item.
5. Wrap the validated result with `ok = true` and `schema_version = "2"`.

### Required fields

All result fields and the success envelope fields are required.

### Optional fields

Nullable result values and empty arrays only as defined by the response schema.

### Failure mode

- Parse fails: `INVALID_AI_JSON`.
- Schema, bound, enum, unknown-field, or project-membership check fails:
  `SCHEMA_MISMATCH`.

Never repair invalid model JSON by guessing. Never pass model prose through as
a successful response.

### User-visible behavior

The Shortcut shows the common failure menu. No AI section is rendered. Quick
Save remains available with confirmed content intact.

## Module 5 — Webhook Response

### Input

Exactly one validated success envelope or one common failure payload.

### Output

- `Content-Type: application/json`.
- One response; no background job or second callback.
- Success uses HTTP 200.
- Failure uses the bounded mapping below.

### Mapping

| HTTP | `error_code` | Meaning |
|---:|---|---|
| 400 | `INVALID_REQUEST` | Request validation failed |
| 502 | `AI_UNAVAILABLE` | Provider call unavailable |
| 504 | `AI_TIMEOUT` | Provider call exceeded timeout |
| 502 | `INVALID_AI_JSON` | Provider output was not valid JSON |
| 422 | `SCHEMA_MISMATCH` | Parsed result violated the V2 contract |
| 500 | `INTERNAL_ERROR` | Scenario failed without a safer known code |

### Required fields

Success requires `ok`, `schema_version`, and `result`. Failure requires only
`ok`, `error_code`, and a safe `message` no longer than 200 characters.

### Optional fields

None. Do not include debug details, model prose, request content, stack traces,
module IDs, connection IDs, or retry internals.

### Failure mode

If response construction itself fails, return the generic `INTERNAL_ERROR`
payload where possible. The Shortcut still uses local Quick Save.

### User-visible behavior

Success suggestions are previewed as unconfirmed and require explicit user
acceptance. Every failure shows:

```text
AI 整理失敗

保存原始筆記
重試
取消
```

## Common Failure Contract

```json
{
  "ok": false,
  "error_code": "AI_UNAVAILABLE",
  "message": "AI enrichment is unavailable."
}
```

Supported codes:

```text
INVALID_REQUEST
AI_UNAVAILABLE
AI_TIMEOUT
INVALID_AI_JSON
SCHEMA_MISMATCH
INTERNAL_ERROR
```

Failure handling must never erase or alter Raw Content, Insight, Context,
Action, Output Goal, or Project.

## Google Sheets and Storage

This scenario does not require Sheets. If an approved audit log is later
added, store only bounded status metadata such as capture ID, timestamps,
status, error code, and processing duration. Do not duplicate Raw Content,
Markdown, long summaries, credentials, or private identifiers into cells.

## Security and Privacy Controls

- Configure webhook authentication and Gemini credentials only in approved
  service connections; never in Git or Obsidian.
- Disable or minimize raw request/response history where platform controls
  allow and an approved policy requires it.
- Use a bounded scenario timeout and one response per request.
- Do not fetch Source URLs or upload files in this stage.
- Do not persist content unless the user explicitly approves provider,
  retention, access, and deletion policies.
- Do not claim a provider-specific privacy guarantee without current verified
  documentation and user approval.

## Offline Development

Use only fictional requests with:

```bash
python3 tools/mobile_enrichment_simulator.py \
  /path/to/fictional-request-v2.json \
  --mode success
```

The corpus files wrap requests with test expectations and are exercised by
`tests/test_mobile_enrichment_simulator.py`. For direct CLI use, supply one
plain request object matching the V2 request schema. The simulator is
explicitly `NOT AI`, `NOT PRODUCTION`, makes no network request, and never
accesses a Vault.

## Migration from V1

V1 remains valid for its existing proposed design. Do not silently change V1
payloads. For new V2 construction:

```text
why_keep              → user_insight
immediate_application → user_context
next_action           → user_action
Chinese output goal   → English output_goal enum
key_points            → supporting_points
immediate_applications → possible_applications
next_action (AI)      → suggested_next_action
content_output_angle  → output_angle
plain result          → explicit success envelope
```

The migration is manual and contract-versioned. Existing desktop JSON handoff
behavior is unaffected.
