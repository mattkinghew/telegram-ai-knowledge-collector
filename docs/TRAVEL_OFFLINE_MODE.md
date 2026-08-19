# Travel Offline Mode

## Expected behavior

| Flow | Offline expectation | Boundary |
|---|---|---|
| Typed capture | Works through local Quick Save | Device acceptance still required |
| Voice | Depends on device dictation availability | No privacy/offline claim is made |
| Clipboard | Works with copied text | Device acceptance still required |
| Shared text | Works as local text | Share Sheet acceptance pending |
| URL reference | Saves the URL without fetch | Page content is not evidence |
| Project update | Builds local Markdown | Shortcut acceptance pending |
| Quick Save | Does not require AI | Obsidian URI acceptance is device-specific |
| AI enrichment | Unavailable offline | Preserve all user layers |
| Remotely Save | May wait for connectivity | No sync guarantee is claimed |

## Fast and Deep capture

- Fast: Share → Insight → Quick Save. Context and Action are optional.
- Deep: Share → Insight → Context → Action → optional AI enrichment. Never force this path.

## Travel recovery

- AI unavailable: use Quick Save.
- Sync unavailable: the note remains in the local Obsidian Vault and may sync later.
- Unsupported Share Sheet input: copy the link/text and use Clipboard capture.
- URI fails on large content: preserve the source, make a shorter Quick Save, and process later.

Recovery never deletes, overwrites, or silently transforms the original capture.

## Privacy default

Use Quick Save, not AI enrichment, for private employer content, client data, credentials, financial details, health information, personal identifying data, or unapproved internal documents. AI enrichment is opt-in only when the user is permitted to send the supplied content to the configured external provider. This repository makes no Make.com or Gemini privacy guarantee.
