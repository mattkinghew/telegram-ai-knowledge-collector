# Privacy and Protected Paths

## Mandatory exclusions

The default policy blocks these paths before filesystem inspection:

- `20_Areas/25_Self_Management/**`
- `25_Self_Management/**`
- `Private/**`
- `Credentials/**`
- `.env`
- `.obsidian/**`

The runtime also reads `90_System/Protected_Paths.md` and applies additional listed patterns.

`bkc init` preserves existing custom rules and appends only missing mandatory patterns. It does not overwrite the file.

## Forbidden operations

Protected content must not be listed, traversed, opened, summarized, stat-ed, hashed, copied, moved, renamed, deleted, indexed, embedded, sent to an external provider, or included in reports.

Symbolic-link files and paths with symbolic-link ancestors are rejected. Review and report notes must also be existing regular Markdown files lexically inside the selected Vault.

## Duplicate detection boundary

- Only direct Markdown children matching `00_Inbox/*.md` are candidates.
- Each candidate must be a regular non-symlink file with no symlink ancestor.
- Protected-path checks happen before candidate metadata is opened.
- Only the bounded `## Metadata` section is read; Source Notes, summaries, key points, relevance, actions, and other note bodies are not read.
- The check stops as unavailable above 5,000 direct candidates.
- At most five stable, Vault-relative match paths are written to a new note.
- No external index, AI provider, upload, recursive scan, deletion, merge, or movement is used.

## Source handling

- Original files are not copied or deleted.
- Large media is registered by path and metadata only.
- URL fetching is off by default.
- Explicit URL fetching accepts only public HTTP/HTTPS destinations and validates DNS results and every redirect before connection.
- Google Drive links are stored as evidence links only.
- No automatic upload exists.
- Private company documents are out of scope.
- The CLI does not require `.env` or API keys.

## Metadata search boundary

- `bkc search` lists only direct `00_Inbox/*.md` candidates and never recurses.
- The shared candidate scanner applies Vault, Protected Paths, regular-file, and symlink guards before a candidate is opened.
- The bounded reader stops after H1 and `## Metadata`; it does not read body sections to answer a query.
- Keyword search uses only Title, Suggested Category, Action Required, Related Project, Related Area, Source Filename, Source Type, File Type, Processing Status, Duplicate Status, and Duplicate Match Type.
- Source URL, Local File, External File Link, Content Hash, and all body content are excluded from matching and output.
- Text and JSON output use Vault-relative paths only.
- Search writes no Vault files, creates no database or persistent index, and calls no external AI or service.
- More than 5,000 direct candidates is a hard failure rather than a partial result.

## Date-review boundary

- `bkc due` reuses the same direct Inbox scanner and bounded H1/Metadata reader.
- It parses only Deadline, Resource Expiry, Reminder Date, Reminder Note, and
  other allowlisted event-display metadata.
- Dynamic status is calculated in memory and is not written to notes.
- Malformed date fields are ignored with capped local diagnostics.
- Text and JSON exclude absolute paths, source URLs, local files, external file
  links, content hashes, Source Notes, and other body content.
- No notification, scheduler, Calendar write, database, index, network, external
  AI, automatic move, archive, or deletion is used.
