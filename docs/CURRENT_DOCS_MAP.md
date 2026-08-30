# Current Documentation Map

P1.5 backend sheets are `CURRENT HYBRID`. P1.4 two-entry sheets are `CURRENT
FALLBACK` and must remain usable without the backend. P1.0–P1.3 implementation
documents are `REFERENCE`; historical contracts are retained.

| Document | Classification | Use |
|---|---|---|
| `docs/P1_5_HYBRID_ARCHITECTURE.md` | CURRENT HYBRID | Architecture, trust boundaries, package and dependency decisions |
| `docs/SHORTCUT_BACKEND_API_CONTRACT.md` | CURRENT HYBRID | Version-1 Shortcut/API contract and failure handling |
| `docs/SHORTCUT_BUILD_SHEET_VOICE_FLASH_BACKEND.md` | CURRENT HYBRID | Build `語音閃念` with optional backend enrichment |
| `docs/SHORTCUT_BUILD_SHEET_CONTENT_CAPTURE_BACKEND.md` | CURRENT HYBRID | Build `收集內容` with optional backend enrichment |
| `docs/P1_5_AUTH_SECURITY_MODEL.md` | CURRENT HYBRID | Dev and deployed single-user auth boundary |
| `docs/P1_5_LOGGING_PRIVACY_POLICY.md` | CURRENT HYBRID | Content-safe logging and retention requirements |
| `docs/P1_5_DATA_LIFECYCLE.md` | CURRENT HYBRID | Raw/result/retry/review lifecycle and no-delete rule |
| `docs/P1_5_DEPLOYMENT_OPTIONS.md` | CURRENT HYBRID | One recommended and one fallback deployment path |
| `docs/P1_5_PRODUCTION_CHECKLIST.md` | MANUAL ACCEPTANCE | Required live security, backup, Gemini and device gates |
| `docs/P1_5_DEVICE_LIVE_ACCEPTANCE_RUNBOOK.md` | MANUAL ACCEPTANCE | Backend-ON and mandatory backend-OFF iPhone evidence |
| `docs/P1_5_GEMINI_LIVE_SMOKE_TEST.md` | MANUAL ACCEPTANCE | Four fictional live modes plus controlled failure/retry |
| `docs/P1_5_STAGING_DEPLOYMENT_CHECKLIST.md` | MANUAL ACCEPTANCE | Staging configuration, security, persistence and rollback gates |
| `docs/P1_5_BACKUP_RESTORE_DRILL.md` | MANUAL ACCEPTANCE | Fictional SQLite backup, clean restore and integrity evidence |
| `docs/P1_5_WEB_PWA_DEVICE_ACCEPTANCE.md` | MANUAL ACCEPTANCE | Real-iPhone Web/PWA navigation, state and action evidence |
| `docs/P1_5_ACCEPTANCE_MATRIX.md` | CURRENT HYBRID | Evidence boundary by feature |
| `docs/P1_5_TECHNICAL_AUDIT.md` | CURRENT HYBRID | Full technical/security/privacy/product audit |
| `docs/P1_4_SIMPLIFIED_MOBILE_PRODUCT_DECISION.md` | CURRENT | CURRENT FALLBACK — two-entry local product rule |
| `docs/SHORTCUT_BUILD_SHEET_VOICE_FLASH_V2.md` | CURRENT | CURRENT FALLBACK — backend-independent `語音閃念` |
| `docs/SHORTCUT_BUILD_SHEET_CONTENT_CAPTURE_V2.md` | CURRENT | CURRENT FALLBACK — backend-independent `收集內容` |
| `docs/P1_4_OFFLINE_BEHAVIOR.md` | CURRENT | CURRENT FALLBACK — lossless local/offline recovery |
| `docs/PENDING_ENRICHMENT_CONTRACT_V1.md` | CURRENT | CURRENT FALLBACK — pending-save meaning and fields |
| `docs/P1_4_TWO_SHORTCUT_DEVICE_ACCEPTANCE.md` | DEVICE_TEST | Four real-device fallback scenarios |
| `docs/PRIVATE_VALUES_SETUP.md` | CURRENT | CURRENT FALLBACK — private device values outside Git |
| `docs/ACTIVE_PROJECTS_MOBILE_SETUP.md` | CURRENT | CURRENT FALLBACK — maintain a 3–8 project allowlist |
| `docs/MANUAL_ONLY_WORK_MATRIX.md` | MANUAL ACCEPTANCE | Remaining device/service-only evidence |
| `docs/TRAVEL_QUICK_START.md` | REFERENCE | Earlier P1.2 travel operating card |
| `docs/VOICE_CAPTURE_CONTRACT_V1.md` | REFERENCE | P1.3 voice contract reused by P1.4 |
| `docs/SHORTCUT_AI_PREVIEW_FORMAT.md` | REFERENCE | Earlier mobile AI preview format |
| `docs/TRAVEL_E2E_ACCEPTANCE.md` | DEVICE_TEST | Earlier travel E2E pack |
| `docs/VOICE_CAPTURE_DEVICE_ACCEPTANCE.md` | REFERENCE | Earlier voice acceptance pack |
| `docs/TRAVEL_DEVICE_FINAL_ACCEPTANCE.md` | REFERENCE | Earlier detailed device pack |
| `docs/MOBILE_P1_0_DEVICE_ACCEPTANCE.md` | REFERENCE | P1.0 device evidence |
| `docs/MOBILE_P1_1_DEVICE_ACCEPTANCE.md` | REFERENCE | P1.1 Share Sheet evidence |
| `docs/IPHONE_SHORTCUT_BUILD_SPEC_V2.md` | REFERENCE | Earlier combined design |
| `docs/IPHONE_SHORTCUT_BUILD_SPEC_V3.md` | REFERENCE | Earlier P1.2 design |
| `docs/IPHONE_SHORTCUT_P1_0_ACTION_MAP.md` | REFERENCE | Earlier manual capture actions |
| `docs/IPHONE_SHORTCUT_P1_1_SHARE_SHEET_ACTION_MAP.md` | REFERENCE | Earlier Share Sheet actions |
| `docs/IPHONE_SHORTCUT_PROJECT_UPDATE_ACTION_MAP.md` | REFERENCE | Earlier project-update actions |
| `docs/MOBILE_CAPTURE_CONTRACT_V1.md` | REFERENCE | Historical source/user fields |
| `docs/KNOWLEDGE_OUTPUT_CONTRACT_V1.md` | REFERENCE | Historical output-mode contract |
| `docs/TRAVEL_OFFLINE_MODE.md` | REFERENCE | Earlier offline boundary |
| `docs/TRAVEL_PROJECT_OPERATIONS_CONTRACT_V1.md` | REFERENCE | Earlier project operations |
| `docs/TRAVEL_PROJECT_REVIEW_ROUTINE.md` | REFERENCE | Earlier review routine |
| `docs/MAKE_GEMINI_ENRICHMENT_SPEC_V1.md` | REFERENCE | Historical Gemini V1 |
| `docs/MAKE_GEMINI_ENRICHMENT_SPEC_V2.md` | REFERENCE | Historical Gemini V2 |
| `docs/MAKE_GEMINI_ENRICHMENT_SPEC_V3.md` | REFERENCE | Historical optional Gemini V3 |
| `docs/MAKE_GEMINI_TRAVEL_SETUP_CHECKLIST.md` | CURRENT | Earlier optional Make/Gemini setup checklist |
| `docs/MAKE_GEMINI_FIELD_MAPPING_WORKSHEET.md` | REFERENCE | Earlier V3 field mapping |
| `prompts/gemini-voice-structured-capture-v1.md` | REFERENCE | Historical voice prompt |
| `docs/TRAVEL_READINESS_STATUS.md` | DEVICE_TEST | Earlier conservative travel evidence status |
| `docs/SHORTCUT_BUILD_SHEET_KNOWLEDGE_CAPTURE.md` | REFERENCE | Earlier knowledge capture |
| `docs/SHORTCUT_BUILD_SHEET_PROJECT_UPDATE.md` | REFERENCE | Earlier project update |
| `docs/SHORTCUT_BUILD_SHEET_VOICE_CAPTURE.md` | REFERENCE | Earlier voice capture |

No historical file is deleted or classified as production evidence.
