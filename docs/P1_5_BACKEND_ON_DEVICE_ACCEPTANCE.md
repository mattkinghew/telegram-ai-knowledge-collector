# P1.5 Backend ON Device Acceptance

Status: `PENDING`. This is the single canonical Backend ON MockProvider device
test. Use fictional content only; do not record tokens, private paths, account
names, or private screenshots.

## Exact flow

```text
iPhone
-> Voice Flash or Content Capture
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

Use the exact fictional input from the accepted Backend OFF session if it was
retained outside Git. If it was not retained, use the following once for
Backend ON, then repeat Backend OFF with the same input; do not reconstruct or
invent the earlier payload:

```text
今日完成 Project Alpha 嘅 CSV mapping，
下一步要測 invalid URL，
另外想到可以寫一篇 AI pricing short post。
```

## One-run procedure

1. Record the exact backend commit and sanitized endpoint host.
2. Confirm `GET /health` returns HTTP 200.
3. Run one backend-aware Shortcut capture. Do not manually resubmit it.
4. Record the 2xx response, `capture_id`, `status=processed`, and returned
   Markdown or structured result.
5. Query `GET /api/v1/captures/{capture_id}` and compare the stored fictional
   raw content with the input.
6. Confirm exactly one local Obsidian note exists, then separately observe the
   same note after Remotely Save.

| Required evidence | Observed | Safe evidence reference |
|---|---|---|
| Request succeeded | | |
| HTTP 2xx | | |
| Non-empty `capture_id` | | |
| `status = processed` | | |
| Markdown or structured result returned | | |
| Local Obsidian note created | | |
| Original raw content preserved | | |
| Remotely Save observed | | |
| Duplicate note: yes/no | | |
| Error, if any | | |

Result remains `PENDING` until the user supplies real-device evidence. Local
TestClient, MockProvider unit tests, and a successful HTTP response without the
device-side note/sync observations do not satisfy this gate.
