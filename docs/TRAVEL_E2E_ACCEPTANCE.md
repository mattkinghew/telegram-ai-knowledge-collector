# Travel End-to-End Acceptance

Status: `DEVICE_TEST` / all scenarios pending. Use fictional or public-safe content. These three scenarios replace the need to complete 15 separate tests before travel; keep `docs/TRAVEL_DEVICE_FINAL_ACCEPTANCE.md` as the detailed reference pack.

## Record rule

For each scenario record date/device, actual result, note filename, and Pass/Fail. A repository test or simulator result cannot prove iPhone, Obsidian, Remotely Save, Make, or Gemini behavior.

## Scenario 1 — Knowledge Capture

### A. Safari and sync

1. In Safari open a public test URL.
2. Share → `收集靈感到 Obsidian`.
3. Select `一般 URL`, enter a short fictional Insight, choose `快速保存`.
4. Confirm preview preserves the exact URL and user text.
5. Save, open the created note in `00_Inbox`, and verify there was no overwrite.
6. Let Remotely Save run under its approved configuration; verify the same note appears on the second device.

### B. Voice

1. Launch the same Shortcut directly.
2. `語音輸入` → dictate a fictional note → edit/confirm transcript.
3. Enter Insight → Fast capture → preview → save.
4. Verify the confirmed text, not an earlier transcript, is in the note.

### Acceptance

- [ ] Exact source preserved.
- [ ] Exact confirmed content preserved.
- [ ] Existing note was not overwritten.
- [ ] Both notes are direct children of `00_Inbox`.
- [ ] Remotely Save sync was observed, not inferred.

Result: `PENDING`.

## Scenario 2 — Project Operations

1. Morning: run `更新專案進度`; select a fictional project; enter Completed/Current progress and Next Action; save.
2. Later: run it again for the same project with a new update and different Next Action.
3. Confirm both Markdown notes remain readable and separate.
4. Copy only those explicit fictional records into the dashboard/report input shape.
5. Run:

```bash
python3 tools/mobile_progress_report.py samples/travel-progress-records.json
python3 tools/project_dashboard_reference.py samples/project-dashboard-v1.json
```

6. Review the generated text; do not claim an automatic Vault report.

### Acceptance

- [ ] Project name preserved in both updates.
- [ ] Morning and later progress remain readable and separate.
- [ ] Next Action preserved exactly.
- [ ] Explicit input produces a useful, concise report draft.
- [ ] No unselected Inbox content enters the output.

Result: `PENDING`.

## Scenario 3 — Knowledge to Output

### A. Without live AI

1. Share a fictional/public article → Deep Capture.
2. Enter user Insight, Context, Action, requested output `recommendation`.
3. On the repository host run the matching fictional request through the simulator:

```bash
python3 tools/mobile_enrichment_simulator.py \
  samples/travel_ai_requests/recommendation.json --travel-v3
```

4. Format the deterministic response using `docs/SHORTCUT_AI_PREVIEW_FORMAT.md` and inspect the mobile preview structure.
5. Repeat with `short_article.json`; confirm the draft is labelled `AI 草稿`.

### B. With live AI later (optional)

1. Use only a public article approved for external processing.
2. Call the privately configured Make webhook from the Shortcut.
3. Inspect the formatted result, never raw JSON.
4. Disable network or use the controlled timeout path; confirm the menu offers `保存原始筆記`.
5. Quick Save the original capture and verify no Source/User field was lost.

### Acceptance

- [ ] Source, User, and AI layers are visibly separate.
- [ ] Output is concise and useful after human review.
- [ ] Short article is clearly marked as an AI draft.
- [ ] AI failure preserves original content and Quick Save.
- [ ] Live AI remains `PENDING` if optional setup was not performed.

Result: `PENDING`.

## Final device decision

Required before travel: Scenario 1 and Scenario 2 pass. Scenario 3A should pass for preview/recovery understanding. Scenario 3B is optional and may remain pending.

Overall: `MANUAL_ACCEPTANCE_PENDING`.
