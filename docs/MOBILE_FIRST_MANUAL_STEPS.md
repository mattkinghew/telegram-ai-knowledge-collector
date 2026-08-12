# Mobile-first Manual Steps

## Status

```text
GATE A USER-ACCEPTED
GATE B USER-REPORTED PASS
P1.0 DEVICE ACCEPTED BY USER REPORT
P1.1 OFFLINE IMPLEMENTATION COMPLETE
GATE C NOT RUN
```

Gate A and Gate B were accepted from the user's report. Codex did not operate
the device, inspect a real Vault, or verify Remotely Save. Do not place a real
Vault identifier, private path, credential, account detail, or private
screenshot in this repository.

## P1.1 — Current Manual Work

1. Edit the existing Shortcut named `收集靈感到 Obsidian` using
   `IPHONE_SHORTCUT_P1_1_SHARE_SHEET_ACTION_MAP.md`. Do not create a second
   production Shortcut.
2. Enter the real Vault identifier only in the local Shortcut. Keep
   `EXAMPLE_VAULT_ID` in repository material.
3. Enable Share Sheet input only for URL, text, image, PDF, and file types.
4. Confirm no-input launch still shows only typed text, voice input, clipboard,
   and cancel.
5. Confirm URL/text input does not require re-entry; image/file input asks one
   manual description and performs no OCR, parse, read, copy, or upload.
6. Confirm Insight is required, Context and Action accept blank, and no title,
   project, output-goal, AI, or classification prompt appears.
7. Confirm the final preview menu contains only Save and Cancel.
8. Run all eight cases in `MOBILE_P1_1_DEVICE_ACCEPTANCE.md`.
9. Inspect each created note directly. A notification or Obsidian opening is
   not proof of a successful write.
10. Test Remotely Save independently and inspect the approved destination.
11. Record only sanitized pass/fail results and usability observations.

## Deferred Work

Do not configure or call Make.com or Gemini, add a webhook, or offer an AI
button in P1.1. AI device integration belongs to P1.2.

Do not add OCR, PDF parsing, file extraction, attachment upload, or webpage
fetching. P1.1 keeps these inputs as local references with user descriptions.

Do not generate or commit an unsigned `.shortcut` package. Do not
reverse-engineer Apple's Shortcut file format.

## Evidence Boundary

Use fictional or public-safe content. Capture only the minimum evidence area
needed, redact identifiers and account details, and store evidence only in a
user-approved location.

## Exact Next Action

Edit or sync the existing Shortcut from the P1.1 Share Sheet Action Map and run
Gate C.
