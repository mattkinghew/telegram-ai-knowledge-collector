# Mobile-first Manual Steps

## Status

```text
GATE A USER-ACCEPTED
P1.0 BUILD OR SYNC PENDING
GATE B NOT RUN
```

Gate A was accepted from the user's report. Codex did not operate the device,
inspect a real Vault, or verify Remotely Save. Do not place a real Vault
identifier, private path, credential, account detail, or private screenshot in
this repository.

## P1.0 — Current Manual Work

1. Build one Shortcut named `收集靈感到 Obsidian` from
   `IPHONE_SHORTCUT_P1_0_ACTION_MAP.md`, either in the Mac Shortcuts app with
   user-managed Shortcuts sync or directly on the iPhone.
2. Enter the real Vault identifier only in the local Shortcut. Keep
   `EXAMPLE_VAULT_ID` in repository material.
3. Confirm the input menu contains only typed text, voice input, clipboard, and
   cancel.
4. Confirm Insight is required, Context and Action accept blank, and no title,
   project, output-goal, AI, or classification prompt appears.
5. Confirm the final preview menu contains only Save and Cancel.
6. Run all eight cases in `MOBILE_P1_0_DEVICE_ACCEPTANCE.md`.
7. Inspect the created note directly. A notification or Obsidian opening is not
   proof of a successful write.
8. Test Remotely Save independently and inspect the approved destination.
9. Record only sanitized pass/fail results and usability observations.

## Deferred Work

Do not enable Shortcut Input or Share Sheet types in P1.0. Safari URL, selected
text, Photos, Files/PDF, and Telegram sharing belong to P1.1.

Do not configure or call Make.com or Gemini, add a webhook, or offer an AI
button in P1.0. AI device integration belongs to P1.2.

Do not generate or commit an unsigned `.shortcut` package. Do not
reverse-engineer Apple's Shortcut file format.

## Evidence Boundary

Use fictional or public-safe content. Capture only the minimum evidence area
needed, redact identifiers and account details, and store evidence only in a
user-approved location.

## Exact Next Action

Build or sync the completed P1.0 Shortcut and run Gate B.
