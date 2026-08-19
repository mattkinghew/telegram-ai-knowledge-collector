# Make + Gemini Field Mapping Worksheet

Status: `AI_SETUP`. This worksheet contains fictional examples only. Configure the real webhook and provider connection privately; do not paste credentials into a module field, log, repository, or screenshot.

## Request mapping

| Module | Source field | Destination field | Required | Example value | Failure handling |
|---|---|---|---:|---|---|
| Custom Webhook | request body | bundle | Yes | V3 JSON object | Missing/non-JSON → HTTP 400 `INVALID_REQUEST`; Quick Save remains available |
| Validate Input | `schema_version` | validated `schema_version` | Yes | `3` | Not exactly `3` → `INVALID_REQUEST` |
| Validate Input | `raw_content` | prompt Source layer `raw_content` | Yes | `A fictional public article...` | Blank/>50,000 → `INVALID_REQUEST`; do not call Gemini |
| Validate Input | `source_type` | prompt Source layer `source_type` | Yes | `article` | Not in V3 enum → `INVALID_REQUEST` |
| Validate Input | `source` | prompt Source layer `source` | Yes | `https://example.com/article` | Wrong source/type pairing, credentials, path, or non-HTTP URL → reject |
| Validate Input | `user_insight` | prompt User layer `user_insight` | Yes | `Start with one pilot.` | Blank/>2,000 → reject |
| Validate Input | `user_context` | prompt User layer `user_context` | Yes | `Project Alpha planning.` | Blank/>2,000 → reject |
| Validate Input | `user_action` | prompt User layer `user_action` | Yes, may be blank | `Define acceptance criteria.` | >1,000 → reject |
| Validate Input | `output_goal` | prompt control `output_goal` | Yes | `project_knowledge` | Not in V3 enum → reject |
| Validate Input | `requested_output` | prompt control `requested_output` | Yes | `recommendation` | Not one of seven V3 modes → reject |
| Validate Input | `project` | prompt User layer `project` | Yes, may be blank | `Project Alpha` | Nonblank but not allowlisted → reject |
| Validate Input | `allowed_projects[]` | response allowlist | Yes, may be empty | `["Project Alpha"]` | >20, duplicate, multiline, or invalid item → reject |
| Gemini Structured Output | validated Source/User/control fields | prompt variables | Yes | Exact validated object | Never fetch URL/file; timeout → `AI_TIMEOUT`; provider/network → `AI_UNAVAILABLE` |
| Response Envelope | Gemini JSON object | `result` | Yes | strict V3 object | Do not repair prose/JSON by guessing |

## Response mapping

| Module | Source field | Destination field | Required | Example value | Failure handling |
|---|---|---|---:|---|---|
| Parse AI JSON | `suggested_title` | preview `標題` | Yes, nullable | `Fictional travel knowledge suggestion` | Missing/unknown type/>200 → `SCHEMA_MISMATCH` |
| Parse AI JSON | `one_sentence_insight` | preview `一句重點` | Yes, nullable | `Use an offline-first capture.` | Missing/unknown type/>500 → schema failure |
| Parse AI JSON | `core_points[]` | preview `核心` | Yes | two short points | More than 3 or item >500 → schema failure |
| Parse AI JSON | `why_it_matters` | preview `為何重要` | Yes, nullable | `It preserves evidence.` | Missing/unknown type/>500 → schema failure |
| Parse AI JSON | `practical_applications[]` | preview `可立即使用` | Yes | `Create a reviewed note.` | More than 3 or item >500 → schema failure |
| Parse AI JSON | `suggested_next_action` | preview `下一步` | Yes, nullable | `Run the fictional checklist.` | Missing/unknown type/>500 → schema failure |
| Parse AI JSON | `recommended_output` | internal mode label | Yes, nullable | `recommendation` | Must equal `requested_output`; otherwise schema failure |
| Parse AI JSON | `short_article_draft` | preview `AI 草稿` | Yes, nullable | `AI draft\n...` | Non-short-article mode must be null; bounds/label failure → schema failure |
| Parse AI JSON | `facts_to_verify[]` | preview `待核實` | Yes | one risk item | More than 5 or item >500 → schema failure |
| Parse AI JSON | `missing_information[]` | preview `欠缺資料` | Yes | `No transcript supplied.` | More than 5 or item >500 → schema failure |
| Parse AI JSON | `related_project` | preview `相關專案` | Yes, nullable | `Project Alpha` | Non-null value must appear in request allowlist |
| Parse AI JSON | `confidence` | preview `信心` | Yes | `medium` | Only `low`, `medium`, `high` accepted |
| Build Success | validated fields | `{ok,schema_version,result}` | Yes | `ok=true`, version `3` | Unknown/missing field → `SCHEMA_MISMATCH` |
| Webhook Response | success envelope | Shortcut dictionary | Yes | strict JSON | Never include provider prose, prompt, stack trace, module/connection ID |

## Failure response mapping

| Condition | HTTP suggestion | `error_code` | Shortcut result |
|---|---:|---|---|
| Invalid request | 400 | `INVALID_REQUEST` | Show bounded message; Quick Save |
| Valid JSON but schema mismatch | 422 | `SCHEMA_MISMATCH` | Discard AI layer; Quick Save |
| Provider unavailable | 502 | `AI_UNAVAILABLE` | Preserve Source/User variables; Quick Save or manual retry |
| Provider returned invalid JSON | 502 | `INVALID_AI_JSON` | Do not display raw provider text; Quick Save |
| Timeout | 504 | `AI_TIMEOUT` | No automatic loop; Quick Save or one explicit retry |
| Unexpected internal failure | 500 | `INTERNAL_ERROR` | Generic message only; no stack trace |

Use `samples/travel_ai_requests/` and `samples/travel_ai_responses/` for manual copy-paste testing. They are deterministic simulator references, not live-service evidence.
