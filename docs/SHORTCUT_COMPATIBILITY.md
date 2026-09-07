# iPhone Shortcut 相容性契約

本文件針對目前 backend 與既有 Shortcut 的 V0.1 驗收。`id` 是 canonical
識別欄位；`capture_id` 只為 backwards compatibility 保留。Shortcut 應以
`id` 建立後續 GET URL，並只在 `status == "processed"` 時讀取 `result`；只在
`status == "failed"` 時讀取 `error.message`。

## 回應矩陣

| 情境 | HTTP | `id` | `capture_id` | `status` | `result` | `error` |
|---|---:|---|---|---|---|---|
| POST accepted | 202 | 有 | 有 | `pending` | 無 | 無 |
| POST synchronous success | 200 | 有 | 有 | `processed` | 有 | 無 |
| GET pending | 200 | 有 | 有 | `pending` | 無 | 無 |
| GET processing | 200 | 有 | 有 | `processing` | 無 | 無 |
| GET processed | 200 | 有 | 有 | `processed` | 有 | 無 |
| GET failed | 200 | 有 | 有 | `failed` | 無 | 有 |
| unknown capture ID | 404 | 無 | 無 | 無 | 無 | 有 |

## 最小 JSON

POST accepted:

```json
{"id":"cap_xxx","capture_id":"cap_xxx","status":"pending"}
```

POST synchronous success / GET processed:

```json
{"id":"cap_xxx","capture_id":"cap_xxx","status":"processed","result":{}}
```

GET pending:

```json
{"id":"cap_xxx","capture_id":"cap_xxx","status":"pending"}
```

GET processing:

```json
{"id":"cap_xxx","capture_id":"cap_xxx","status":"processing"}
```

GET failed:

```json
{"id":"cap_xxx","capture_id":"cap_xxx","status":"failed","error":{"code":"AI_TIMEOUT","message":"AI processing timed out — capture was saved."}}
```

Unknown ID:

```json
{"error":{"code":"NOT_FOUND","message":"Capture was not found."}}
```

HTTP 500 目前表示 POST/retry 的 processing failure；此時 body 仍有
`status: "failed"` 與 `error`。GET 已儲存的 failed capture 是 HTTP 200。
Shortcut 不應因為 500 丟失 `id` 或停止保存原始輸入；目前是否把 domain
failure 改成 HTTP 200，待真機驗收後再決定。

## HTTP 500 的完整範圍（目前行為）

以下情況在 POST `/api/v1/capture` 或 POST retry 會回 HTTP 500，且會先將
capture 保存為 `failed`：

- AI provider 回傳 `AI_UNAVAILABLE`、`AI_TIMEOUT`、`AI_AUTH_FAILED`、
  `AI_RATE_LIMITED`、`NETWORK_UNAVAILABLE` 等 processing failure。
- URL extraction 失敗或不支援內容型別（例如 `URL_FETCH_FAILED`）。
- provider 回傳 malformed/不符合 `ProviderResult` 的結果；目前安全映射為
  `INTERNAL_ERROR`。
- 未預期的 processing exception；目前安全映射為 `INTERNAL_ERROR`。
- failed capture 的 manual retry 再次 processing failure。

這些是 domain/job processing failures，不是表示 capture 沒有被接受的
transport failure；raw input 已在 processing 前寫入 SQLite。真正的 HTTP
transport/server failures 仍包括 authentication（401）、request validation
（422）、unknown ID（404）、retry state/limit（409）與未處理的 server
exception（500，但不保證有 capture id）。

建議：對行動 Shortcut，domain failure 長期較適合回 HTTP 200 並以
`status: "failed"` 表示，因為這能讓 Shortcut 一律解析 JSON 並保留 id；
但 V0.1 暫不改，先用真機確認 Shortcut 是否能讀取 HTTP 500 response body。
