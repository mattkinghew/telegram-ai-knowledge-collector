# P1.5 Acceptance Matrix

`Yes` means repository evidence exists in this branch. `No` means not verified;
it is not a prediction of whether the feature would work live.

| Feature | Offline implemented | Automated tested | Device tested | Live service tested | Production ready | Notes |
|---|---:|---:|---:|---:|---:|---|
| P1.4 local fallback | Yes | Yes | No | No | No | Existing contracts preserved; real two-Shortcut run pending |
| Capture/status/list/retry API | Yes | Yes | No | No | No | Authenticated local TestClient coverage |
| Strict request/payload validation | Yes | Yes | No | No | No | 128 KiB body, 50k content, bounded fields/lists |
| SQLite pending/raw preservation | Yes | Yes | No | No | No | No delete path or automatic cleanup |
| Mock provider processing modes | Yes | Yes | No | No | No | Deterministic fictional output only |
| Gemini provider boundary | Yes | Yes | No | No | No | Live calls intentionally disabled/pending |
| Article extraction and SSRF controls | Yes | Yes | No | No | No | Local fixture only; DNS-rebinding residual risk documented |
| Video reference behavior | Yes | Yes | No | No | No | No download, scrape, or transcription |
| Markdown generation | Yes | Yes | No | No | No | Source, extracted text, AI suggestions separated |
| Shortcut backend contracts | Yes | No | No | No | No | Documentation cannot execute a real Shortcut |
| Today / Inbox / Projects / Pending / Reports | Yes | Yes | No | No | No | Static asset/API tests; no browser automation by scope |
| Search and safe operational edits | Yes | Yes | No | No | No | Metadata filters, review and project allowlist |
| PWA shell | Yes | Yes | No | No | No | Shell caching only; installability not device-verified |
| Auth/CORS/security headers | Yes | Yes | No | No | No | Production fail-closed configuration tested |
| Logging privacy | Yes | Yes | No | No | No | No external log sink configured |
| Report preview | Yes | Yes | No | No | No | Human selection; no send/publish |
| Recommended Render architecture | Yes | No | No | No | No | Official-doc review only; no deployment created |
