# iPhone 真機驗收測試

## Online backend handoff

- Production base URL: `https://capture.lamlab.cc`
- POST endpoint: `https://capture.lamlab.cc/api/v1/capture`
- GET endpoint: `https://capture.lamlab.cc/api/v1/captures/{id}`
- Authentication: `Authorization: Bearer <private token>`; never put the token
  in this document, a URL, note content, screenshot, or log.
- Health endpoint: `https://capture.lamlab.cc/health` (public, no capture data).

The hostname is the existing Cloudflare Named Tunnel ingress to the local
LaunchAgent-managed FastAPI runtime. Online V0.1 validation is not complete
until the exact deployed runtime commit and authenticated fictional smoke
results are recorded in `docs/ONLINE_V01_VALIDATION.md`.

## 共用設定

- 使用現有 `/api/v1/capture`，保持目前 Authorization 與 HTTPS 設定；不修改
  Shortcut。線上測試使用上述 production base URL；localhost 僅用於本機
  fake-provider 驗證。
- POST body 使用 schema version `1`。以 POST 回應的 `id` 呼叫
  `GET /api/v1/captures/{id}`。
- `result` 只在 `processed` 讀取；`error.message` 只在 `failed` 讀取。
- 每個 processing failure 後，以 GET 確認 `raw_content` 等於送出內容。

| Case | Setup | POST 預期 | GET sequence / final | raw recovery | Shortcut 行為 |
|---|---|---|---|---|---|
| A normal text | selected text + `summary` | 200, `processed`, `result` | processed | 保留 | 讀 result，保存/開啟 note |
| B URL capture | public HTTP(S) URL + `article_url` | 200 processed 或 500 failed（依 extraction/provider） | 若 failed，GET 200 failed | 保留 URL/raw input | 顯示失敗訊息，不丟原文 |
| C delayed processing | Gemini/deferred mode；先記錄 POST 的 202 | 202, `pending`, no result | `pending` → `processing` → `processed`（也可能 GET 時已完成） | 保留 | 以 id 輪詢；只處理四種 status |
| D AI failure | test-only `FailureProvider("AI_UNAVAILABLE")` | 500, `failed`, error | GET 200 failed | 保留 | 顯示 `error.message`，保留 capture id |
| E malformed result | test-only provider 回傳不符合 ProviderResult | 500, `failed`, `INTERNAL_ERROR` | GET 200 failed | 保留 | 顯示通用失敗，不讀 result |
| F timeout | test-only `FailureProvider("AI_TIMEOUT")` | 500, `failed`, `AI_TIMEOUT` | GET 200 failed | 保留 | 顯示 timeout 訊息，不重送未確認的 capture |

## 驗收步驟

1. A/B/C 逐一送出，保存 HTTP status、response JSON、capture id 與 GET
   時間序列。
2. D/E/F 使用本機 fake-provider 測試先確認 backend 行為；真機只驗證
   Shortcut 對現有 response 的解析與顯示，不呼叫付費模型。
3. 每個 failed case 以 GET 驗證 `raw_content`；不得以 Shortcut note
   是否建立作為 raw persistence 的唯一證據。
4. 記錄 Shortcut 是否能在 HTTP 500 body 仍讀取 JSON。若不能，這是目前
   唯一需要在真機驗收後決定的 API 相容性風險。

## 通過條件

- status 只出現 `pending|processing|processed|failed`。
- processed 有 `result`；其他狀態沒有 `result`。
- failed 有非空 `error.code` 與 `error.message`。
- 每個 failure 的 raw input 可由 GET record recovery。
