# Business Knowledge Capture Workflow

## Initialize Known MVP Paths

The command must point to the existing vault. It will not create a new vault.

```bash
bkc init --vault "/absolute/path/to/Example_Business_Vault"
```

The initializer confirms `00_Inbox` exists, creates missing approved system files/templates, detects `10_Work/11_Projects` before `10_Projects`, and refuses to guess a project root when neither exists.

If one approved root already contains `14_New_Role_90_Day`, all init, validation, and reporting operations reuse it. If both approved roots contain that project, the command stops. Existing Protected Paths rules are preserved and missing required rules are appended. Conflicting user templates are preserved while one stable `.v2` managed template is created.

## Capture Text

```bash
bkc capture \
  --vault "/absolute/path/to/Example_Business_Vault" \
  --text "New-role onboarding notes..." \
  --title "Onboarding notes" \
  --related-project "14_New_Role_90_Day"
```

## Register a URL

```bash
bkc capture \
  --vault "/absolute/path/to/Example_Business_Vault" \
  --url "https://example.com/resource" \
  --title "Resource to review" \
  --deadline "2026-08-31" \
  --resource-expiry "2026-09-15" \
  --reminder-date "2026-08-24" \
  --reminder-note "Review requirements"
```

Remote fetch is off by default. Use `--fetch-url` only for public, non-sensitive HTTP/HTTPS pages. Fetching is explicit and limited to 2 MB.

Before each connection and redirect, the fetcher rejects localhost, private, loopback, link-local, multicast, reserved, and unspecified addresses. It uses a 15-second timeout and a fixed redirect limit.

## Register a Local File

```bash
bkc capture \
  --vault "/absolute/path/to/Example_Business_Vault" \
  --file "/absolute/path/to/non-sensitive-file.pdf" \
  --external-file-link "https://drive.google.com/..."
```

Supported registration: PDF, DOCX, TXT, MD, JPG/JPEG, PNG, MP3, MP4.

## Summary Modes

- `disabled` (default): records `Summary Status: pending`.
- `manual`: accepts `--manual-summary`.
- `optional-ai-disabled`: exposes the adapter boundary but never calls an AI provider.

No provider means no fabricated summary.

## Exact Duplicate Suggestion

Before writing a new note, capture checks only the metadata section of direct `00_Inbox/*.md` files. It compares complete SHA-256 content hashes and conservatively normalized HTTP/HTTPS URLs.

The check does not recurse, read note bodies, call a website, infer semantic similarity, or choose a canonical note. A duplicate warning never blocks saving. The new note records `unique`, `exact_duplicate_suggested`, or `check_unavailable`.

URL normalization lower-cases the scheme and IDNA hostname, removes the HTTP/HTTPS default port and fragment, and maps an empty path to `/`. It preserves path case, a non-empty trailing slash, query text/order/value, percent encoding, and the HTTP/HTTPS distinction.

## Human Review

```bash
bkc review \
  --vault "/absolute/path/to/Example_Business_Vault" \
  --note "/absolute/path/to/Example_Business_Vault/00_Inbox/NOTE.md" \
  --category "重要知識" \
  --action-required "Discuss with manager" \
  --mark summary \
  --mark classification \
  --mark action \
  --mark duplicate
```

The duplicate checkbox records that a human reviewed the suggestion. It does not confirm, delete, merge, or move either note.

The system never automatically deletes or moves a note.

Mobile handoff notes add `Mobile handoff reviewed`. Voice-transcript notes also
add `Voice transcript checked`; marking it updates `Transcript Review Status`
from `pending` to `reviewed`.

```bash
bkc review \
  --vault "/absolute/path/to/Example_Business_Vault" \
  --note "/absolute/path/to/Example_Business_Vault/00_Inbox/NOTE.md" \
  --mark handoff \
  --mark transcript
```

Deadline, Resource Expiry, and Reminder Date accept only `YYYY-MM-DD`. Review
can set these fields or clear them explicitly. `--clear-reminder` clears both
Reminder Date and Reminder Note. `--mark dates` records manual review without
checking Action confirmed or changing classification.

Review and report accept only existing regular `.md` files inside the selected Vault. Protected paths, symlink files, and symlink ancestors are rejected before content is read.

## Metadata-only Inbox Search

```bash
bkc search \
  --vault "/absolute/path/to/Example_Business_Vault" \
  --related-project "14_New_Role_90_Day"
```

Search is read-only and considers only direct `00_Inbox/*.md` files. It reads the H1 title and bounded `## Metadata` section, stopping before One-line Summary, Key Points, Relevance, Suggested Actions, Source Notes, Manual Review, or any other body section.

Supported filters include title, allowlisted metadata keyword, category, created/deadline ranges, deadline/action presence, related project/area, source type, exact file type, processing status, and duplicate status. Repeated values for one field use OR; filters across fields use AND.

```bash
bkc search \
  --vault "/absolute/path/to/Example_Business_Vault" \
  --category "重要知識" \
  --category "資源" \
  --has-deadline \
  --sort deadline-asc \
  --limit 50
```

Sort modes are `created-desc` (default), `created-asc`, `deadline-asc`, `deadline-desc`, `title-asc`, and `title-desc`. Missing dates remain last. The Vault-relative path is the stable tie-breaker.

Use `--format json` for JSON. Diagnostics stay on stderr, so stdout remains valid JSON. Search stops without partial results above 5,000 direct candidates; the result limit defaults to 50 and must be from 1 through 200.

Resource Expiry and Reminder Date support inclusive range and presence filters.
Reminder Note participates in `--query` because it is allowlisted Metadata.

## Read-only Date Review

```bash
bkc due \
  --vault "/absolute/path/to/Example_Business_Vault" \
  --as-of "2026-07-26" \
  --window-days 14
```

Each note may yield a deadline, resource-expiry, and reminder event. Status is
calculated from the explicit reference date: negative is overdue, zero is due
today, 1 through the window is due soon, and later is upcoming. Upcoming events
are hidden by default.

Repeated event-type and status filters use OR; different fields use AND. The
default sort is date ascending, with reminder before deadline before resource
expiry, then Vault-relative path. The command reads only bounded H1 and Metadata
from direct Inbox notes and writes nothing.

Every text and JSON event includes:

```text
<event_type>::<YYYY-MM-DD>::<00_Inbox/direct-note.md>
```

## Progress Report Draft

```bash
bkc report \
  --vault "/absolute/path/to/Example_Business_Vault" \
  --type weekly \
  --period "2026-07-20 to 2026-07-26" \
  --completed "/absolute/path/to/completed-note.md" \
  --in-progress "/absolute/path/to/in-progress-note.md" \
  --blocker "Awaiting access approval" \
  --commitment "Complete stakeholder map"
```

The report is written to `14_New_Role_90_Day/03_Progress_Reports/` under the detected existing project root.

Date review does not automatically populate reports. Run `bkc due`, identify
relevant events, then explicitly repeat `--due-selection`:

```bash
bkc report \
  --vault "/absolute/path/to/Example_Business_Vault" \
  --type daily \
  --period "2026-08-01" \
  --as-of "2026-08-01" \
  --window-days 14 \
  --due-selection "reminder::2026-08-08::00_Inbox/example.md" \
  --due-selection "deadline::2026-08-15::00_Inbox/example.md"
```

The handoff validates all keys and current event dates before rendering. Any
invalid or stale selection stops the complete operation. Identical keys are
deduplicated with a warning, different events from one note stay distinct, and
the maximum is 50 supplied keys.

Selected events are recalculated against `--as-of` and `--window-days`, sorted
by date, event type, title, and relative path, then rendered between In Progress
and Evidence. Explicit upcoming events remain included. Without selections, the
existing report contains no Date Review section.

## Validation

```bash
bkc validate --vault "/absolute/path/to/Example_Business_Vault"
```

Validation checks only known MVP paths. It does not scan the entire vault.

## Explicit Mobile Handoff

One handoff file contains one schema-v1 object. The CLI reads only the exact
path supplied by the user and never scans its parent folder:

```bash
bkc handoff validate --file "/path/to/handoff.json"
bkc handoff preview --file "/path/to/handoff.json"
bkc handoff import \
  --vault "/absolute/path/to/Example_Business_Vault" \
  --file "/path/to/handoff.json"
```

The first two commands do not read the Vault. Import validates the complete
handoff before using the existing capture pipeline. It creates one direct Inbox
note atomically, keeps the handoff file unchanged, and emits duplicate warnings
on stderr. No command deletes, moves, archives, watches, uploads, or batches
handoff files. See `HANDOFF_SCHEMA_V1.md` and `IPHONE_SHORTCUT_HANDOFF.md`.

## Runtime

Use an existing Python 3.9 or newer interpreter:

```bash
PYTHON_BIN="$(command -v python3)"
"$PYTHON_BIN" --version
```

No API key is required.
