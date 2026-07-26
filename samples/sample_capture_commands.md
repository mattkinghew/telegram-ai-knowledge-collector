# Sample Capture Commands

```bash
bkc capture \
  --vault "/absolute/path/to/Matt_Space" \
  --text "$(cat samples/sample_text.txt)" \
  --title "AWS learning resource" \
  --deadline "2026-08-31" \
  --related-project "14_New_Role_90_Day"
```

Expected classification suggestion: `資源`.

```bash
bkc capture \
  --vault "/absolute/path/to/Matt_Space" \
  --file "/absolute/path/to/meeting-audio.mp3" \
  --title "Meeting audio"
```

Expected processing status: `awaiting_transcription`.
