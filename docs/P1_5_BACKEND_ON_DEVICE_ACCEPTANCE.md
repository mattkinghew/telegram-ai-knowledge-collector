# P1.5 Backend ON Device Acceptance

Status: `PENDING`. This is the single canonical Backend ON MockProvider device
runbook. Use fictional content only; do not record tokens, private paths, account
names, or private screenshots.

## Exact flow

```text
iPhone Voice Flash and Content Capture, tested separately
-> reachable P1.5 backend
-> MockProvider
-> processed result
-> Markdown
-> local Obsidian note
-> Remotely Save
```

Set `APP_ENV=production`, `AI_PROVIDER=mock`, `ENABLE_LIVE_AI=false`, token auth,
explicit CORS, and a persistent SQLite path. Live Gemini is not required and
must remain disabled.

Backend ON acceptance requires both Test A and Test B below. Use the exact
fictional voice input from the accepted Backend OFF session if it was retained
outside Git. If it was not retained, use the following once for Test A; do not
reconstruct or invent the earlier payload:

```text
今日完成 Project Alpha 嘅 CSV mapping，
下一步要測 invalid URL，
另外想到可以寫一篇 AI pricing short post。
```

For Test B, share this fictional selected text directly. Do not use an external
URL for the first device acceptance:

```text
Project Lantern is a fictional school workshop pilot. The team tested one CSV
mapping with synthetic records. The pilot has not been deployed.
```

## Test A — Voice Flash

```text
語音閃念
-> backend
-> voice_structure processed
-> Markdown
-> local Obsidian note
-> Remotely Save
```

## Test B — Content Capture

```text
Share fictional selected text
-> 收集內容
-> backend
-> summary processed
-> Markdown
-> local Obsidian note
-> Remotely Save
```

## Two-run procedure

1. Record the exact backend commit and sanitized endpoint host.
2. Confirm `GET /health` returns HTTP 200.
3. Run Test A exactly once. Do not manually resubmit it.
4. Record the 2xx response, `capture_id`, `status=processed`, and returned
   Markdown or structured result; query the stored record and compare raw text.
5. Confirm exactly one local Obsidian note for Test A, then separately observe
   the same note after Remotely Save.
6. Run Test B exactly once and repeat the same response, stored-raw, local-note,
   duplicate, and Remotely Save checks with a distinct `capture_id`.

| Required evidence | Voice Flash | Content Capture | Safe evidence reference |
|---|---|---|---|
| Request succeeded | | | |
| HTTP 2xx | | | |
| Non-empty, distinct `capture_id` | | | |
| `status = processed` | | | |
| Markdown or structured result returned | | | |
| Local Obsidian note created | | | |
| Original raw content preserved | | | |
| Remotely Save observed | | | |
| Duplicate note: yes/no | | | |
| Error, if any | | | |

Result remains `PENDING` until the user supplies real-device evidence. Local
TestClient, MockProvider unit tests, and a successful HTTP response without the
device-side note/sync observations do not satisfy this gate.
