# OB Editor V0.1 — Backend Test Plan

All AI tests use fake providers. No paid model or network call is allowed.

| Case | Expected behaviour |
|---|---|
| Valid capture | HTTP success; UUID capture ID; one of the four canonical states; raw input persisted. |
| Missing required input | HTTP 422; bounded `INVALID_REQUEST`; no capture row created. |
| pending → processing → processed | Statuses are observable/persisted in order; processed response contains `result`. |
| AI processing failure | Final state is `failed`; nested error has sanitized code/message; raw input remains. |
| Malformed AI response | Final state is `failed` with schema/JSON error; malformed payload and raw input are not echoed into the error. |
| Processing timeout | Final state is `failed` with `AI_TIMEOUT`; raw input remains recoverable. |
| Unknown capture ID | HTTP 404 with `NOT_FOUND`; no traceback or internal details. |
| Raw recovery after failure | GET still returns exact raw content; failed response omits `result`. |
| Deferred acceptance | POST returns only accepted ID and `pending`; no queue-specific client state. |
| Processed contract | POST and GET use the same `id/status/result` semantics. |

Existing auth, payload-limit, URL-security, retry, provider, operations, and
Web/PWA suites remain regression coverage.
