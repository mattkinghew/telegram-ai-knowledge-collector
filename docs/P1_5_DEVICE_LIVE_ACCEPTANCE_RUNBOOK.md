# P1.5 Device and Live Acceptance Index

Status: `PREPARED`; required external evidence remains pending except the
Backend OFF user report below. Use fictional/public-safe inputs only.

## Canonical procedures

- Backend ON Mock device test:
  `P1_5_BACKEND_ON_DEVICE_ACCEPTANCE.md`.
- Live Gemini four-mode and failure test:
  `P1_5_GEMINI_LIVE_SMOKE_TEST.md`.
- iPhone Web/PWA test:
  `P1_5_WEB_PWA_DEVICE_ACCEPTANCE.md`.

Do not duplicate those procedures in another document. Record evidence only in
their tables or a sanitized acceptance result derived from them.

## Backend OFF accepted boundary

Result: `USER_REPORTED_DEVICE_PASS`.

The user reported observing:

```text
backend unreachable
-> P1.4 local fallback
-> raw/pending note
-> local Obsidian write
-> Remotely Save observed by user
```

This is user-reported device evidence. It was not reproduced by repository
automation or Codex. No timing, screenshot, device detail, or earlier fictional
payload is inferred. The unchanged P1.4 fallback remains mandatory in every
Backend ON, Live Gemini, and staging test.
