# Make + Gemini Travel Enrichment Specification v3

## Why V3

V2 remains unchanged. P1.2 adds `requested_output`, video source types, renamed bounded result fields, mode-specific short article output, and an explicit Quick Save failure flag. These are backward-incompatible contract changes, so V3 uses new schemas and prompt files.

## Flow

Validated webhook request → provider structured JSON → strict V3 response validation → success preview or safe failure → user chooses save.

## Request and response

- Request: `schemas/mobile-insight-request-v3.schema.json`.
- Prompt: `prompts/gemini-mobile-enrichment-v3.md`.
- Response: `schemas/mobile-insight-response-v3.schema.json`.
- Offline oracle: `tools/mobile_enrichment_simulator.py --travel-v3`.

```bash
python3 tools/mobile_enrichment_simulator.py \
  samples/mobile-insight-request-v3.json \
  --travel-v3
```

Every parse, schema, timeout, network, or provider failure leaves Raw Content, Insight, Context, Action, Output Goal, and Project unchanged and returns the Quick Save path. No source URL is fetched and no attachment is uploaded in this stage.
