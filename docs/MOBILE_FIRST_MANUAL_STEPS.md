# Mobile-first Manual Steps

## Status

Manual implementation checklist. None of these steps has been completed or
device-tested by Codex.

Use sanitized test content first. Do not use employer, client, health,
credential, or personal data until the complete device, sync, webhook, provider
retention, and access policy has been approved.

## Stage 1 — Minimal Architecture Smoke Test

Do only this stage now. Do not build the Share Sheet, input menu, dictation,
Gemini, OCR, PDF extraction, or other full-workflow branches.

1. In iOS Shortcuts, create a temporary Shortcut named `BKC Mobile Test`.
2. Add **Text** and paste the exact fixed Markdown from
   `IPHONE_SHORTCUT_BUILD_SPEC_V2.md`.
3. Add **URL Encode** for the complete Markdown.
4. Add a **Text** action that builds the documented `obsidian://new` URI using
   the local Vault identifier, `00_Inbox/BKC-Mobile-Test`, and the encoded
   Markdown. Keep the repository placeholder as `EXAMPLE_VAULT_ID`.
5. Add **Open URLs** and run the Shortcut once with sanitized content.
6. Inspect Obsidian directly. Confirm the note is a direct child of
   `00_Inbox`, and verify the Chinese text and Markdown/YAML.
7. Run or wait for the approved Remotely Save sync, then inspect the intended
   second device or approved destination directly.
8. Record the complete Stage 1 result in
   `MOBILE_FIRST_ACCEPTANCE_CHECKLIST.md` without a Vault identifier, private
   path, account detail, webhook URL, or private screenshot.

Stop after Step 8. Do not infer success from Shortcuts or Obsidian opening;
record only directly observed note creation and synchronization.

## Later Full Workflow Steps — Not Yet Authorized

The following steps remain proposed for later goals. Do not execute them until
Stage 1 is accepted and the next goal is explicitly started.

| Step | Manual action | Expected result | Failure symptoms |
|---:|---|---|---|
| 1 | In iOS Shortcuts, create one Shortcut named `收集靈感到 Obsidian` using `IPHONE_SHORTCUT_BUILD_SPEC_V3.md`. | One editable Shortcut contains the no-input, Share Sheet, preview, Quick Save, and optional AI branches. | Multiple competing capture Shortcuts, missing cancel paths, or raw content replaced during editing. |
| 2 | Enter the real Vault ID or a selected public-safe Vault name into the local `VaultID` Shortcut variable. Do not add it to this repository. | The generated URI targets the intended Vault without exposing a local filesystem path. | Obsidian reports that the Vault cannot be found or opens the wrong Vault. |
| 3 | Open Shortcut Details and enable Share Sheet input for URL, plain text, rich text, image, and file. | The Shortcut appears for each enabled supported input. | Shortcut absent from Share Sheet or input arrives with the wrong type. |
| 4 | Grant only the clipboard, dictation, and app-opening permissions required by the chosen paths. Review the iOS privacy prompts. | Each chosen path runs after an explicit user action and cancel remains available. | Repeated permission errors, automatic clipboard reads, dictation unavailable, or Obsidian cannot open. |
| 5 | Test the `obsidian://new` Quick Save URI with sanitized text, Chinese characters, `&`, `#`, `%`, `?`, and `/`. | One uniquely named Markdown note appears directly in `00_Inbox`; content is intact and no existing note is overwritten. | Wrong Vault/folder, nested Inbox folder, truncated content, literal percent escapes, duplicated query parameters, overwrite, or no note. |
| 6 | Install and configure Remotely Save on the real device according to its current approved documentation and storage policy. | The newly created test note synchronizes to the approved target and remains readable on the intended second device. | Authentication failure, conflict copy, wrong remote path, missing note, duplicate note, or unexpected private data transfer. |
| 7 | In Make.com, create the five-module scenario from `MAKE_GEMINI_ENRICHMENT_SPEC_V2.md` with sanitized sample data. | A valid sample request produces one version-2 success envelope. | Unknown fields pass validation, model prose is returned, bounded arrays overflow, or a module stores unexpected data. |
| 8 | Create or authorize the required Make.com connection using the account and data region approved by the user. | The scenario can receive the sanitized webhook request without exposing connection details to the Shortcut. | Unauthorized connection, wrong account/workspace, connection identifier or secret visible in output. |
| 9 | Store the Gemini credential only in an authorized Make.com connection. | The model call succeeds without any API key in Shortcut, Obsidian, repository, logs, or response. | Key visible in Shortcut/repository, authentication error, or secret included in scenario output/history. |
| 10 | Copy the generated webhook URL into the local `WebhookURL` Shortcut variable. Never commit or place it in a note. | AI Save posts only after review and receives a response; Quick Save makes no webhook call. | Placeholder remains, 404/authorization error, requests fire before review, or URL appears in saved Markdown. |
| 11 | Execute every case in `MOBILE_FIRST_ACCEPTANCE_CHECKLIST.md` on the real iPhone and record evidence without private content. | All required cases have observed results and pass/fail status; failures preserve raw content and allow safe exit or Quick Save. | Cases marked passed without evidence, device behavior differs from the specification, or failure loses user input. |
| 12 | Approve data privacy choices for dictation, Remotely Save, Make.com history, Gemini processing, logs, retention, and allowed content. | A written user decision identifies permitted data, providers, retention, and prohibited sensitive content. | Provider settings are unknown, raw content persists unexpectedly, or sensitive content is tested without authorization. |

## Exact First iPhone Action

Open the Shortcuts app, tap `+`, rename the new Shortcut to
`BKC Mobile Test`, then add **Text** with the fixed Markdown in
`IPHONE_SHORTCUT_BUILD_SPEC_V2.md`. Enter the real Vault identifier only in
the local Shortcut. Do not enter a webhook URL or build the full input flow at
this stage.

## Evidence Boundary

For acceptance evidence, capture only the minimum screen area needed. Redact
Vault identifiers, webhook URLs, account names, notification contents, and any
personal data. Store evidence only in a user-approved location; do not add
device screenshots or secrets to this repository.
