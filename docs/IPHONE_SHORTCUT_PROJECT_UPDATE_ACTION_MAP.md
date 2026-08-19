# iPhone Shortcut — Project Update Action Map

Shortcut name: `更新專案進度`

Target: complete a factual update in 60 seconds or less. No AI, Mac, Terminal, Make.com, or network is required for note construction.

## Private setup

Copy the structure from `config/example-active-projects.json` into one private on-device Dictionary or List. Replace fictional values locally. Do not commit employer, client, account, or confidential project names.

## Action sequence

1. `Choose from List`: private active projects; cancel exits without saving.
2. `Ask for Input` (required): `今日完成了甚麼？`
3. `Ask for Input` (optional): `目前正在做甚麼？`
4. `Ask for Input` (required): `下一步是甚麼？`
5. `Ask for Input` (optional): `有沒有 blocker / 待確認？`
6. `Ask for Input` (optional): `Evidence / Link`.
7. Build Markdown from `templates/mobile-progress-update-v1.md`; percent-encode each dynamic value independently.
8. `Choose from Menu`: `Save Progress` or `取消`.
9. On save, open an `obsidian://new` URI targeting a flat Inbox filename. Preview the complete draft before this action.

## Failure handling

- Empty required answers: show a short validation message and return to the field.
- Cancel: write nothing.
- URI failure or very large content: keep the entered text visible, shorten the update, Quick Save, and process later.
- Sync unavailable: keep the note in the local Vault; Remotely Save may sync later when connectivity returns.

Action labels vary by iOS version. Use the native equivalent only; no third-party action or unsigned `.shortcut` file is required.

Status: `MANUAL_ACCEPTANCE_PENDING` until the real Shortcut and Vault flow are tested.
