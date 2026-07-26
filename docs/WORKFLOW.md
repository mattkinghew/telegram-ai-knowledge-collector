# Business Knowledge Capture Workflow

## Initialize Known MVP Paths

The command must point to the existing vault. It will not create a new vault.

```bash
bkc init --vault "/absolute/path/to/Matt_Space"
```

The initializer confirms `00_Inbox` exists, creates missing approved system files/templates, detects `10_Work/11_Projects` before `10_Projects`, and refuses to guess a project root when neither exists.

## Capture Text

```bash
bkc capture \
  --vault "/absolute/path/to/Matt_Space" \
  --text "New-role onboarding notes..." \
  --title "Onboarding notes" \
  --related-project "14_New_Role_90_Day"
```

## Register a URL

```bash
bkc capture \
  --vault "/absolute/path/to/Matt_Space" \
  --url "https://example.com/resource" \
  --title "Resource to review" \
  --deadline "2026-08-31"
```

Remote fetch is off by default. Use `--fetch-url` only for public, non-sensitive HTTP/HTTPS pages. Fetching is explicit and limited to 2 MB.

## Register a Local File

```bash
bkc capture \
  --vault "/absolute/path/to/Matt_Space" \
  --file "/absolute/path/to/non-sensitive-file.pdf" \
  --external-file-link "https://drive.google.com/..."
```

Supported registration: PDF, DOCX, TXT, MD, JPG/JPEG, PNG, MP3, MP4.

## Summary Modes

- `disabled` (default): records `Summary Status: pending`.
- `manual`: accepts `--manual-summary`.
- `optional-ai-disabled`: exposes the adapter boundary but never calls an AI provider.

No provider means no fabricated summary.

## Human Review

```bash
bkc review \
  --vault "/absolute/path/to/Matt_Space" \
  --note "/absolute/path/to/Matt_Space/00_Inbox/NOTE.md" \
  --category "重要知識" \
  --action-required "Discuss with manager" \
  --mark summary \
  --mark classification \
  --mark action
```

The system never automatically deletes or moves a note.

## Progress Report Draft

```bash
bkc report \
  --vault "/absolute/path/to/Matt_Space" \
  --type weekly \
  --period "2026-07-20 to 2026-07-26" \
  --completed "/absolute/path/to/completed-note.md" \
  --in-progress "/absolute/path/to/in-progress-note.md" \
  --blocker "Awaiting access approval" \
  --commitment "Complete stakeholder map"
```

The report is written to `14_New_Role_90_Day/03_Progress_Reports/` under the detected existing project root.

## Validation

```bash
bkc validate --vault "/absolute/path/to/Matt_Space"
```

Validation checks only known MVP paths. It does not scan the entire vault.
