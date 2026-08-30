# P1.5 Web/PWA Device Acceptance

Status: `PREPARED` / iPhone evidence pending. Use fictional captures only.
Never record the bearer token, raw content, account identity, or private paths.

## Test record

| Evidence | Record |
|---|---|
| iPhone / iOS | |
| Safari version | |
| App commit / deployment | |
| Orientation(s) | Portrait / Landscape |
| Home Screen install supported | Yes / No / Not tested |
| Test time (UTC) | |

## Preconditions

- [ ] Backend health and token authentication are working over HTTPS.
- [ ] Fictional records include processed, pending, reviewed/unreviewed,
  assigned/unassigned, and at least two projects.
- [ ] Keep the token in the PWA password field only; do not save or screenshot it.

## Navigation and states

For every view, confirm readable text without zoom, comfortable tap targets,
no clipped controls, and no horizontal page overflow.

| Area | Required check | Observed | Evidence reference | Result |
|---|---|---|---|---|
| Today | Recent items, counts, actions render | | | PENDING |
| Inbox | Records load and one review action works | | | PENDING |
| Projects | Assigned projects and latest status render | | | PENDING |
| Pending | Pending item is visible; retry works | | | PENDING |
| Reports | Select records and render preview | | | PENDING |
| Search | Query narrows results and clear restores list | | | PENDING |
| Navigation | All five destinations are easy to tap | | | PENDING |
| Loading | Visible during a deliberately delayed request | | | PENDING |
| Empty | Clear, non-error message for an empty filter | | | PENDING |
| Error | Safe message for invalid auth or stopped backend | | | PENDING |

## Authentication and actions

- [ ] Missing/invalid token is rejected without exposing content.
- [ ] Valid token loads data; a page refresh requires re-entry because the token
  is memory-only.
- [ ] Retry preserves the same `capture_id`, raw content, and bounded retry count.
- [ ] Review/project assignment changes only approved operational fields.
- [ ] Report preview contains only selected fictional records and remains
  `sent=false`, `published=false`.

## PWA shell

1. In Safari, use **Add to Home Screen** if the device/browser offers it.
2. Launch from the icon and confirm the shell opens with the expected name/icon.
3. After one online load, disconnect and reopen only to verify shell behavior.
   Do not expect API capture data offline; API responses are not cached.
4. Reconnect and confirm authenticated data loads after token re-entry.

If installation is not offered, record `Not supported/not offered` with device
and browser versions; do not mark installability as passed.

## Result

Device Web/PWA acceptance remains `PENDING` until the user supplies evidence
for every applicable row. Automated asset/API tests do not replace this test.
