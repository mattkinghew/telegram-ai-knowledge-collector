# Mobile Capture Privacy Model

## Status

Architecture and operating boundary only. No device, sync service, Make.com,
or Gemini privacy property was verified in this offline stage.

## Quick Save Data Flow

```text
iPhone
→ Obsidian Mobile
→ user-configured Remotely Save
```

Quick Save does not require Gemini, Make.com, a webhook, a Mac, Terminal, or
the existing JSON handoff. The Shortcut constructs one reviewed Markdown note
and opens an Obsidian URI. Actual local storage, app permissions, and sync
behavior remain device-dependent.

Data in the Quick Save note:

- Source Type and a URL, safe filename, or blank Source;
- Raw Content;
- confirmed Insight, Context, and optional Action;
- optional user-confirmed Project and Output Goal;
- capture timestamp and workflow status.

Quick Save omits the entire AI Suggestions section.

## AI Enrichment Data Flow

```text
iPhone
→ Make.com
→ Gemini
→ Make.com
→ iPhone
→ user preview
→ Obsidian Mobile
```

Only use AI enrichment for content the user is permitted to send to the
configured external services.

The Shortcut must show a network-use choice before sending. The request is
limited to the version-2 allowlist; it contains no credential, attachment
bytes, absolute local path, or arbitrary nested object. AI output is untrusted,
schema-validated, visibly labelled as suggested, and added only after explicit
acceptance.

## Default to Quick Save / No AI

Do not send these categories to external enrichment by default:

```text
credentials
private client information
sensitive employer documents
health information
financial account data
unapproved personal data
```

Also use Quick Save when sharing permission, provider retention, account/data
region, service history, access control, or deletion policy is unknown.

## Source-specific Boundaries

### URL

Store the original HTTP/HTTPS URL. P0.9 does not fetch it. A URL or title alone
does not support a summary of page contents.

### Voice transcript

The user reviews and confirms transcript text before it becomes Raw Content.
Dictation privacy depends on the device, operating-system configuration,
language, keyboard, and selected provider. This repository makes no claim that
dictation is offline, private, on-device, or encrypted.

### Image

Store a user description and optional non-sensitive filename. Do not OCR,
upload, embed, or infer unseen content in this stage.

### File or PDF

Store a user description and optional non-sensitive filename. Do not parse,
upload, or embed file bytes. Never store an absolute local path in the mobile
contract.

### Clipboard

Read only after the user selects the clipboard path. Preview before continuing.
Do not send clipboard content to AI without a second explicit user choice.

## Remotely Save Boundary

Remotely Save is user-configured infrastructure, not repository code. The user
must review the chosen provider, remote location, encryption settings, access
control, conflict behavior, retention, and device permissions. A successful
Obsidian URI does not prove synchronization.

Test first with fictional content. Store evidence only in an approved location
and omit Vault identifiers, account names, remote paths, credentials, and
private screenshots from Git.

## Make.com and Gemini Boundary

- Store webhook and provider credentials only in approved service connections.
- Do not commit or put credentials in Shortcut notes, logs, prompts, schemas,
  or fixtures.
- Treat request history, provider logs, and model output as potential data
  retention surfaces.
- Minimize or disable raw-content logging where approved controls permit.
- Use safe error messages without echoing source or user content.
- Validate model output before display or Markdown rendering.
- Keep Quick Save available if services are unavailable or unapproved.

No provider-specific privacy, encryption, residency, retention, or training-use
guarantee is asserted here. Current service terms and organizational approval
must be checked before real data is sent.

## Threat and Control Summary

| Risk | Control in this design | Evidence status |
|---|---|---|
| Raw content lost during AI failure | separate local variables and Quick Save fallback | offline contract tested; device pending |
| Model invents facts | bounded prompt, verification fields, explicit AI label | contract tested; service quality pending |
| Disallowed project suggestion | allowlist plus response cross-check | offline test covered |
| URI corruption | independent percent encoding and decode equality tests | offline test covered; device pending |
| Secret committed | placeholders, fixture scan, staged-diff review | repository review required per commit |
| Private path exposed | schema/custom rejection and privacy scan | offline test covered |
| Sync conflict | direct device acceptance and pilot metric | device/pilot pending |
| External retention unknown | default Quick Save and approval gate | user/service review pending |

## User Approval Checklist Before AI

- [ ] The content category is permitted for the configured services.
- [ ] The Make.com account/workspace is approved.
- [ ] The Gemini connection and intended data-use setting are approved.
- [ ] Request/response history and retention have been reviewed.
- [ ] Raw logging is minimized according to the approved policy.
- [ ] The Shortcut uses a local webhook placeholder until configured on device.
- [ ] Failure fallback has passed with fictional content.

If any item is unresolved, use Quick Save only.
