# P1B Metadata-only Inbox Search

## Purpose

`bkc search` retrieves reviewable Inbox records without reading note bodies or building an index. It is a bounded local metadata query, not full-text or semantic search.

## Scope

Only direct Markdown children matching `00_Inbox/*.md` are candidates. The shared Inbox scanner enforces:

- selected Vault boundary;
- direct flat Inbox location;
- regular Markdown file;
- no symlink file or symlink ancestor;
- Protected Paths;
- maximum 5,000 candidates.

Above 5,000 candidates the command fails without returning a partial result.

## Read boundary

For each safe candidate, the reader obtains only:

- the first H1 title;
- the `## Metadata` section.

It stops before the next second-level heading. One-line Summary, Key Points, Relevance, Suggested Actions, Source Notes, Manual Review, and all other body content are excluded.

## Filters

Supported filters:

- `--title`: case-insensitive title substring;
- `--query`: case-insensitive substring over the explicit keyword allowlist;
- repeatable `--category`;
- inclusive `--created-from` and `--created-to`;
- inclusive `--deadline-from` and `--deadline-to`;
- mutually exclusive `--has-deadline` and `--missing-deadline`;
- inclusive `--resource-expiry-from` and `--resource-expiry-to`;
- mutually exclusive `--has-resource-expiry` and `--missing-resource-expiry`;
- inclusive `--reminder-from` and `--reminder-to`;
- mutually exclusive `--has-reminder` and `--missing-reminder`;
- `--related-project` and `--related-area` substrings;
- repeatable `--source-type`;
- repeatable `--file-type`, using case-insensitive exact equality;
- repeatable `--processing-status`;
- repeatable `--duplicate-status`;
- mutually exclusive `--has-action` and `--missing-action`.

The keyword allowlist is Title, Suggested Category, Action Required, Reminder
Note, Related Project, Related Area, Source Filename, Source Type, File Type,
Processing Status, Duplicate Status, and Duplicate Match Type.

Repeated filters within one field use OR. Different fields use AND.

## Sorting and limits

Sort modes:

- `created-desc` (default);
- `created-asc`;
- `deadline-asc`;
- `deadline-desc`;
- `title-asc`;
- `title-desc`.

Invalid or missing dates sort last. Deadline missing values remain last in either direction. Title uses Unicode-aware `casefold()`. Vault-relative path ascending is the stable tie-breaker.

The result limit defaults to 50, with a minimum of 1 and maximum of 200. `total_matches` reports all matches before the result limit.

## Output

Text output contains a compact record list. `--format json` emits UTF-8 JSON on stdout. Diagnostics and warnings go only to stderr.

Results may also expose Resource Expiry, Reminder Date, and Reminder Note. They
never expose Source URL, Local File, External File Link, Content Hash, absolute
Vault path, or note body content.

## Malformed notes

Missing H1 uses the filename stem with a diagnostic. Missing metadata fields become empty. Invalid Created or Deadline becomes missing and produces a diagnostic. One malformed note does not block other results.

At most 20 diagnostics are printed. Additional diagnostics are summarized.

## Runtime and exclusions

Python 3.9 or newer is supported. Search is read-only and requires no API key, network, external AI, database, SQLite, persistent/background index, embedding, RAG, vector store, UI, OCR, transcription, automatic move, deletion, or duplicate resolution.

## Known limitations

- Metadata-only matching cannot find terms that exist only in note bodies.
- Substring matching does not use regex, stemming, fuzzy matching, or token expansion.
- File type is exact rather than substring matching.
- Search inspects current flat Inbox metadata on every invocation and intentionally does not cache or index it.
