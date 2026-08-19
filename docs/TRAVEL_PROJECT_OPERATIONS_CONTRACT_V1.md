# Travel Project Operations Contract v1

## Purpose

A phone-first, Markdown only project model for short travel updates. It adds no database, Kanban dependency, Dataview dependency, cloud backend, account, RAG, or agent.

## Concepts

| Concept | Meaning | Minimum fields |
|---|---|---|
| Project | Named outcome or maintained work stream | name, status |
| Status | Current bounded state | active, paused, blocked, completed |
| Progress Update | One 30–60 second factual update | Project, Completed / Progress, Next Action |
| Next Action | One concrete user-confirmed step | text |
| Blocker | Optional impediment or pending approval | text |
| Decision | Confirmed choice with rationale | choice, rationale |
| Evidence | Approved link plus short description | description, link |
| Due Date | User-confirmed calendar date | YYYY-MM-DD |
| Report Item | Explicitly selected update, task, decision, due event, or evidence | type, title, detail |

## Rules

- Store project status and updates as plain Markdown.
- Keep `project`, `type`, status and review dates minimal.
- A report includes only records explicitly selected by the user; never every Inbox note.
- Do not infer completion, schedule buffer, blocker resolution, or evidence validity.
- Private employer/client values replace fictional project samples only on the user's device and are not committed.

## Offline reference commands

```bash
python3 tools/mobile_progress_report.py samples/travel-progress-records.json
python3 tools/project_dashboard_reference.py samples/project-dashboard-v1.json
```

Both commands read only the explicit fictional JSON argument and print deterministic Markdown. They do not access a Vault, scan an Inbox, call AI, or use the network.

The existing `bkc report` remains unchanged because it validates selected Vault notes and writes into one established project path. P1.2 therefore uses the isolated reference builder rather than widening that command's Vault scope. Human selection is represented only by `selected_records`.
