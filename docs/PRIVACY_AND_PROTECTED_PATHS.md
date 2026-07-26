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

## Forbidden operations

Protected content must not be listed, traversed, opened, summarized, stat-ed, hashed, copied, moved, renamed, deleted, indexed, embedded, sent to an external provider, or included in reports.

## Source handling

- Original files are not copied or deleted.
- Large media is registered by path and metadata only.
- URL fetching is off by default.
- Google Drive links are stored as evidence links only.
- No automatic upload exists.
- Private company documents are out of scope.
- The CLI does not require `.env` or API keys.
