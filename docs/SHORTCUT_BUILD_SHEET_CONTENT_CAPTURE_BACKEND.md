# Shortcut Build Sheet — Content Capture with P1.5 Backend

Status: current hybrid build sheet. Complete device execution remains pending.

## Input routing

Keep the existing `收集內容` P1.4 detection order and preserve the untouched
input locally:

| Shared input | `source_type` | `source` | `raw_content` |
|---|---|---|---|
| Public article URL | `article_url` | URL | selected/shared text or empty |
| Public social URL | `social_post` | URL | selected/shared text or empty |
| Video URL | `video_url` | URL | empty unless a transcript was supplied |
| Supplied video transcript | `video_transcript` | URL | transcript |
| Selected/shared text | `selected_text` | null | exact text |
| Clipboard fallback | `clipboard_text` | null | exact text |
| Image reference | `image_reference` | safe filename | optional caption |
| File reference | `file_reference` | safe filename | optional note |

Never send a filesystem path, file bytes, image bytes, credentials, or a Vault
identifier.

## Actions

1. Receive Share Sheet input; otherwise ask whether to use the clipboard.
2. Detect input type and retain the original URL/text/reference.
3. Ask only `整理`, `只收藏`, or `取消`.
4. `取消`: stop with no network or local write.
5. `只收藏`: skip the backend and run the P1.4 local raw builder with
   `ai_status: none`.
6. `整理`: choose one of `summary`, `recommendation`, `short_article`, or
   `project_knowledge`, then POST the version-1 capture dictionary.
7. On validated HTTP 200 processed success, use `result.markdown`.
8. On every other outcome, build the P1.4 local raw/pending note from the
   original Share Sheet values. Do not replace the source with extracted text.
9. Open the local note through `obsidian://new`; Remotely Save remains a separate
   device-local synchronization concern.

## URL and video rules

- The backend may fetch only public HTTP/HTTPS article/social URLs with its
  SSRF, redirect, MIME, size, and timeout limits.
- A URL-only failure stays pending and must never be presented as a completed
  article summary.
- A video URL is preserved as a reference. P1.5 does not download, scrape,
  transcribe, or extract video/audio.
- If the user supplies transcript text, only that text is eligible for
  processing.

## Backend failure acceptance

Disable the local server or use an unreachable fictional endpoint, then verify
that `整理` still creates the same P1.4 local raw/pending note. This manual device
scenario is mandatory before live use; repository tests can validate the
contract but cannot operate the real Shortcut or Vault.

