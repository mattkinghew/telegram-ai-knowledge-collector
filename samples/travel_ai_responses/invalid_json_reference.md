# Invalid JSON Reference

Provider output example (intentionally not valid JSON):

```text
{"ok": true, "result":
```

Expected Make handling: discard the untrusted provider text, return `INVALID_AI_JSON` with `quick_save_available=true`, and let the Shortcut use Quick Save. Never paste the malformed provider output into the Obsidian note.
