# P1.5 Temporary HTTPS Device Acceptance

Status: `READY`; real iPhone evidence remains `PENDING`. This procedure exposes
the existing loopback FastAPI backend through one temporary Cloudflare Quick
Tunnel. It creates no Render service, persistent tunnel, DNS record, paid
resource, or production deployment.

Use fictional data only. Keep `AI_PROVIDER=mock` and `ENABLE_LIVE_AI=false`.
The backend never receives a Vault identifier or path and never writes to an
Obsidian Vault; only the existing iPhone Shortcut may create the local note.

## Acceptance boundary

```text
iPhone Shortcut or Safari
-> random temporary HTTPS origin
-> cloudflared outbound tunnel
-> FastAPI on 127.0.0.1:8000
-> token auth + explicit CORS
-> MockProvider + temporary SQLite
```

This can prove the Backend ON device and Web/PWA device flows. It cannot prove
staging deployment, restart persistence, persistent storage, backup/restore,
live Gemini, production availability, or production security.

Cloudflare documents Quick Tunnels as free, random `trycloudflare.com` URLs for
testing and development only. They have no uptime guarantee, accept public
Internet traffic, and stop when the local `cloudflared` process stops:

- <https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/trycloudflare/>
- <https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/downloads/>

## 1. Preflight

From the repository root, confirm the accepted branch and commit without
reading any `.env` file:

```bash
git branch --show-current
git rev-parse HEAD
command -v cloudflared
cloudflared --version
```

Expected branch: `feat/hybrid-capture-platform-p1-5`. For this acceptance, use
the already verified commit `d84e3ce5e7018ba98f9d13fd457af33ca889dbb6`
or a later explicitly recorded acceptance-only commit.

Use the verified hybrid virtual environment when it is still present:

```text
/private/tmp/p1-5-hybrid-final-venv/bin/python
```

If it is absent, create a local `.venv` and install the existing pinned hybrid
extra as documented in `README.md`. Do not add or upgrade dependencies.

## 2. Start the temporary HTTPS tunnel

In Terminal A:

```bash
cloudflared tunnel --url http://127.0.0.1:8000 --no-autoupdate
```

Copy only the generated origin, for example:

```text
https://random-words.trycloudflare.com
```

Do not add a path, query string, credential, or trailing slash. Keep Terminal A
open. The URL is public, so the API token remains mandatory even though the
backend is using MockProvider.

## 3. Create the private token and start FastAPI

Create one new high-entropy temporary password in the user's password manager.
It must be at least 16 characters, contain no whitespace, and remain outside
Git, notes, screenshots, terminal commands, URLs, logs, and this document.

In Terminal B, replace only the non-secret tunnel origin, then run the block.
Paste the token only at the hidden prompt:

```bash
cd /Users/mattgor/Documents/Codex/telegram-ai-knowledge-collector
export P1_5_TUNNEL_ORIGIN='https://random-words.trycloudflare.com'
P1_5_DEVICE_TMP="$(mktemp -d /private/tmp/p1-5-device-acceptance.XXXXXX)"
read -r -s 'P1_5_DEVICE_TOKEN?Temporary API token (hidden): '
echo
APP_ENV=production \
AI_PROVIDER=mock \
ENABLE_LIVE_AI=false \
AUTH_MODE=token \
API_AUTH_TOKEN="$P1_5_DEVICE_TOKEN" \
ALLOWED_ORIGINS="$P1_5_TUNNEL_ORIGIN" \
DATABASE_URL="sqlite:///$P1_5_DEVICE_TMP/p1_5_capture.sqlite3" \
/private/tmp/p1-5-hybrid-final-venv/bin/python -m uvicorn backend.app:app \
  --host 127.0.0.1 \
  --port 8000
```

Required CORS value is exactly the generated HTTPS origin:

```text
ALLOWED_ORIGINS=https://random-words.trycloudflare.com
```

Do not use `*`, an origin with `/app/`, or the local loopback origin. If the
tunnel is restarted, it generates a new origin; restart FastAPI with that new
exact CORS origin before further device testing.

## 4. Safe Mac pre-check

From another terminal, set only the public origin and confirm health:

```bash
export P1_5_TUNNEL_ORIGIN='https://random-words.trycloudflare.com'
curl --fail --silent --show-error "$P1_5_TUNNEL_ORIGIN/health"
```

Expected JSON:

```json
{"ok":true,"status":"healthy"}
```

Then confirm auth fails closed without sending a token:

```bash
curl --silent --output /dev/null --write-out '%{http_code}\n' \
  "$P1_5_TUNNEL_ORIGIN/api/v1/captures"
```

Expected HTTP status: `401`. Do not put the bearer token in a command line or
query string. The authenticated acceptance is performed from the configured
iPhone Shortcut and Web App below.

## 5. Replace the iPhone Shortcut endpoint

Apply these changes to both `語音閃念` and `收集內容` without deleting or
rewriting the existing P1.4 local fallback:

1. Set the private `BackendBaseURL` Text value to the exact temporary origin,
   with no trailing slash.
2. Set the private `ApiToken` Text value from the password manager. Do not save
   it in a note, URL, screenshot, or Shortcut result.
3. In **Get Contents of URL**, set the URL to
   `BackendBaseURL` + `/api/v1/capture`.
4. Keep method `POST` and request body `JSON`.
5. Add header `Authorization` with value `Bearer ` followed by `ApiToken`.
6. Keep `Content-Type: application/json` if the action does not set it
   automatically.
7. Accept backend Markdown only when HTTP is 200, `ok` is exactly true,
   `status` is exactly `processed`, and `result.markdown` is non-empty.
8. Every timeout, TLS/DNS error, 4xx/5xx, pending result, malformed JSON, or
   invalid success envelope must continue to the unchanged P1.4 local raw or
   pending builder. Do not add an automatic retry loop.

The request dictionaries remain exactly those in
`SHORTCUT_BUILD_SHEET_VOICE_FLASH_BACKEND.md` and
`SHORTCUT_BUILD_SHEET_CONTENT_CAPTURE_BACKEND.md`. Never send a Vault path,
Vault identifier, filesystem path, file bytes, credential, provider, model, or
provider parameter.

## 6. Backend ON iPhone test

Run these once each, in order. Record sanitized evidence in
`P1_5_BACKEND_ON_DEVICE_ACCEPTANCE.md`.

### A. Voice Flash

```text
今日完成 Project Alpha 嘅 CSV mapping，
下一步要測 invalid URL，
另外想到可以寫一篇 AI pricing short post。
```

Expected:

```text
HTTP 200
-> distinct capture_id
-> status = processed
-> non-empty Markdown
-> original transcript preserved by backend
-> exactly one local Obsidian note
-> Remotely Save observed by user
```

### B. Content Capture

Share this selected text directly; do not use external URL fetching:

```text
Project Lantern is a fictional school workshop pilot. The team tested one CSV
mapping with synthetic records. The pilot has not been deployed.
```

Choose `整理` and `summary`. Expect the same evidence fields as Test A with a
different `capture_id` and exactly one local note.

Do not record the token, full private payload, account identity, Vault path, or
private screenshot. Device observation remains user-reported evidence; local
HTTP checks cannot mark the note or Remotely Save fields as passed.

## 7. Web/PWA iPhone test

Before stopping the tunnel, open this exact URL in iPhone Safari:

```text
https://random-words.trycloudflare.com/app/
```

Paste the token only into the Web App password field. Verify Today, Inbox,
Projects, Pending, Reports, and Search using the fictional records. Confirm:

- readable without zoom and no horizontal overflow;
- missing or invalid token shows a safe error and exposes no capture data;
- valid token loads data;
- refresh requires token re-entry because the token is memory-only;
- pending manual retry remains bounded;
- report preview remains `sent=false` and `published=false`;
- Add to Home Screen only if Safari offers it; otherwise record `Not offered`.

Record the observations in `P1_5_WEB_PWA_DEVICE_ACCEPTANCE.md`. A temporary
Home Screen icon is not production PWA deployment evidence.

## 8. Backend OFF fallback test

Run this last so it does not interrupt Backend ON or Web/PWA evidence:

1. Press `Control-C` in Terminal A to stop only `cloudflared`.
2. Leave the FastAPI process running locally.
3. Run one Shortcut with this distinct fictional input:

```text
Project Alpha fictional offline drill: preserve this exact sentence.
```

Expected:

```text
temporary endpoint unreachable
-> unchanged P1.4 local fallback
-> raw/pending note
-> exact fictional content preserved
-> local Obsidian write
-> Remotely Save observed by user
-> no automatic retry loop
```

This new observation may supplement but must not overwrite the existing
`USER_REPORTED_DEVICE_PASS` evidence boundary.

## 9. Cleanup

1. Stop `cloudflared` and Uvicorn with `Control-C` in their terminals.
2. Remove the temporary endpoint and token from both Shortcuts or disable their
   Backend ON branch; confirm the P1.4 local fallback remains available.
3. Remove the temporary password-manager entry after evidence is recorded.
4. In Terminal B, clear the shell variables and delete only the validated
   temporary database directory:

```bash
unset P1_5_DEVICE_TOKEN
unset P1_5_TUNNEL_ORIGIN
case "$P1_5_DEVICE_TMP" in
  /private/tmp/p1-5-device-acceptance.*) rm -r -- "$P1_5_DEVICE_TMP" ;;
  *) echo 'Refusing to remove unexpected path.' ;;
esac
unset P1_5_DEVICE_TMP
```

5. Close the temporary Safari tab or Home Screen icon. Keep or remove fictional
   Obsidian notes only through normal user-controlled Vault review.

After cleanup, the random HTTPS origin must no longer reach the backend.
Persistence, restart, backup/restore, live Gemini, staging, and production all
remain pending.
