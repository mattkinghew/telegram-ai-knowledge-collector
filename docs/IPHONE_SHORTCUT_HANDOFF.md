# iPhone Shortcut Manual Handoff

These are build instructions only. This repository does not ship an unsigned
Shortcut package, credential profile, configuration profile, network service,
or direct-to-Vault automation.

## Shortcut A: Text or shared URL

1. Accept Share Sheet input or use Ask for Input.
2. Ask the user to select Text or URL.
3. Ask for a title.
4. Ask for optional action required.
5. Ask for optional related project and related area.
6. Ask whether a deadline, resource expiry, or reminder is needed; when yes,
   request a specific date in `YYYY-MM-DD`.
7. Create `handoff_id` from current date/time plus a short random value using
   only letters, digits, `-`, `_`, `.`, or `:`.
8. Format current time as ISO-8601 with timezone for `captured_at`.
9. Build the exact schema-version-1 dictionary. Include every required key and
   use an empty string for unused optional values.
10. Convert the dictionary to JSON text.
11. Show a final review screen containing title, type, dates, action, project,
    area, and content.
12. Let the user choose Save or Cancel.
13. On Save, write one `.json` file to a location the user selects.

Do not store an API key, directly write into the Obsidian Vault, call external
AI, upload to Google Drive, automatically transfer to the Mac, or execute the
import command.

## Shortcut B: Voice transcript text

1. Run Dictate Text or another transcription method selected by the user.
2. Display the resulting transcript.
3. Ask the user to edit, confirm, or cancel.
4. Ask for title and optional action, project, area, and dates.
5. Set `source_type` to `voice_transcript`, place only resulting text in
   `content`, and keep `source_url` empty.
6. Build every schema-version-1 field.
7. Show a final review screen.
8. Save one `.json` file only after user confirmation.

Voice transcription privacy depends on the device, operating-system settings,
keyboard/dictation provider and user configuration. This repository only
receives the resulting text file and does not perform transcription.

Do not dictate confidential employer, client, health, credential or personal
data unless the user is authorized to process it with the selected device and
transcription provider.

Do not assume dictation is offline, on-device, end-to-end encrypted, or withheld
from Apple or another provider. The user must verify the actual device,
operating-system, language, keyboard, provider, and account settings.

## Manual transfer options

### Option 1: AirDrop

iPhone creates JSON → user reviews file → AirDrop to Mac → user runs validate →
user runs preview → user explicitly runs import.

### Option 2: User-approved iCloud folder

Save JSON to a dedicated folder outside the Vault → wait for sync → manually
select the exact file → validate → preview → import.

Do not use company data unless company policy permits the selected storage and
sync service. Do not save the handoff directly into the Vault, and do not
configure the CLI to watch the folder.

### Option 3: Manual Files transfer

Save to Files → transfer using a method chosen and approved by the user →
validate the exact file → preview → import.

Google Drive is not assumed or configured.

## Mac commands

```bash
bkc handoff validate --file "/path/to/handoff.json"
bkc handoff preview --file "/path/to/handoff.json"
bkc handoff import \
  --vault "/absolute/path/to/Example_Business_Vault" \
  --file "/path/to/handoff.json"
```

Use `preview --show-content` only when terminal history and screen recording are
appropriate for that content. It displays at most 2,000 characters.

After import, review the generated note:

```bash
bkc review \
  --vault "/absolute/path/to/Example_Business_Vault" \
  --note "/absolute/path/returned/by/import.md" \
  --mark handoff
```

For voice transcript notes also add `--mark transcript`. File cleanup remains a
manual user decision; the CLI never deletes or moves the JSON.
