# P1.5 Cloudflare Named Tunnel Acceptance

Status: `READY_FOR_OPERATOR_SETUP`; no tunnel, DNS record, or credential is
stored in this repository. Replace every `<...>` placeholder locally only.

The repository also contains a safe macOS LaunchAgent template under
`ops/macos/`. It is intentionally not installed by Codex: production startup
requires two operator-created Keychain items and fails closed when either is
missing.

This runbook connects the iPhone Shortcut to the existing FastAPI process:

```text
iPhone Shortcut
-> https://<capture-hostname>
-> Cloudflare remotely-managed Named Tunnel
-> http://127.0.0.1:8000
-> FastAPI capture API
-> Gemini provider (only when explicitly enabled)
```

Use fictional data only. Never put a Cloudflare tunnel token, API auth token,
Gemini key, Vault path, or Remotely Save credential in Git, a URL, a Shortcut
payload, a screenshot, or a log.

## Preconditions

An operator must have:

1. A Cloudflare account that is signed in to the Dashboard.
2. A domain managed by that Cloudflare account.
3. One selected hostname, for example `capture.example.com`.
4. `cloudflared` installed on the Mac.
5. A local FastAPI process bound to `127.0.0.1:8000`.

The repository cannot create the tunnel without the account and domain. Do not
substitute `capture.yourdomain.com` for a real hostname.

## Create the remotely-managed tunnel

In Cloudflare Dashboard, create one remotely-managed tunnel and add a published
application route:

```text
Hostname: <capture-hostname>
Service:  http://127.0.0.1:8000
```

Copy the one-time connector command shown by Cloudflare into a local terminal.
Do not commit the token contained in that command. Start the connector using
the Dashboard-provided token, or use the Dashboard-generated `cloudflared`
configuration. The tunnel must have one catch-all rejection route after the
local service route.

Confirm the connector is connected before testing the public hostname:

```bash
cloudflared tunnel list
cloudflared tunnel info <tunnel-name-or-id>
```

If the command requests an origin certificate or token, stop and obtain it from
Cloudflare Dashboard; do not create or print a replacement credential here.

## Start FastAPI with explicit boundaries

Create a temporary database outside the repository. Generate the token locally
and enter it into the Shortcut through the device's secure credential flow; do
not paste it into this document or a shell history entry.

```bash
cd /Users/mattgor/Documents/Codex/telegram-ai-knowledge-collector
P1_5_TUNNEL_TMP="$(mktemp -d /private/tmp/p1-5-named-tunnel.XXXXXX)"
read -r -s 'P1_5_API_TOKEN?Temporary API token (hidden): '
echo
APP_ENV=production \
AUTH_MODE=token \
API_AUTH_TOKEN="$P1_5_API_TOKEN" \
ALLOWED_ORIGINS="https://<capture-hostname>" \
DATABASE_URL="sqlite:///$P1_5_TUNNEL_TMP/capture.sqlite3" \
AI_PROVIDER=mock \
ENABLE_LIVE_AI=false \
python3 -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

The first acceptance must use `AI_PROVIDER=mock`. Only after the mock device
flow passes may an operator intentionally restart the process with:

```text
APP_ENV=production
AUTH_MODE=token
AI_PROVIDER=gemini
ENABLE_LIVE_AI=true
GEMINI_MODEL=gemini-3.6-flash
GEMINI_API_KEY=<runtime secret only>
ALLOWED_ORIGINS=https://<capture-hostname>
```

The Gemini key must exist only in runtime secret configuration. The backend
rejects missing, malformed, or non-allowlisted live configuration.

## Public smoke checks

Use the hostname only; never put the token in a URL or command-line argument.

```bash
export P1_5_CAPTURE_ORIGIN='https://<capture-hostname>'
curl --fail --silent --show-error "$P1_5_CAPTURE_ORIGIN/health"

curl --silent --output /dev/null --write-out '%{http_code}\n' \
  "$P1_5_CAPTURE_ORIGIN/api/v1/captures"
```

Expected results are health HTTP 200 and unauthenticated API HTTP 401. Then run
one fictional authenticated capture from the iPhone Shortcut, preserving the
existing bounded polling contract: POST once, poll the capture status endpoint,
stop on `processed` or `failed`, and use manual retry only.

The explicit CORS origin must be exactly `https://<capture-hostname>`; do not
use `*`, a path such as `/app/`, or a trailing slash.

## Persistent macOS backend (optional operator setup)

Copy the two `ops/macos/*.example` files without the `.example` suffix, replace
`REPLACE_WITH_ACCOUNT` with the local macOS account path, and keep the copied
files outside Git. Store the two runtime secrets in Keychain; their values must
never be put in the plist, shell history, repository, or logs:

```text
service: com.business-knowledge-capture.p1-5.api-auth-token
service: com.business-knowledge-capture.p1-5.gemini-api-key
account: <macOS account name>
```

Use **Keychain Access** to create these items in the `login` keychain: choose
`New Password Item`, use the service string above as the item name, use the
macOS account name as `Account`, and enter the secret only in the password
field. Do this once for each item. Do not use a `security ... -w <secret>`
command copied from a shell history, and do not paste either value into chat.
The wrapper performs a non-printing lookup by service/account and exits
fail-closed if either item is absent or empty.

The wrapper sets `APP_ENV=production`, `AUTH_MODE=token`,
`AI_PROVIDER=gemini`, `ENABLE_LIVE_AI=true`,
`GEMINI_MODEL=gemini-3.6-flash`, and the explicit origin
`https://capture.lamlab.cc`. It binds only to `127.0.0.1:8000` and stores the
SQLite file under the user's Application Support directory. If either Keychain
item is absent, the wrapper exits before starting Uvicorn; it does not fall
back to development auth or MockProvider.

Validate the template before loading it:

```bash
plutil -lint "$HOME/Library/LaunchAgents/com.business-knowledge-capture.p1-5.backend.plist"
chmod 700 "$HOME/Library/Application Support/business-knowledge-capture/run-p1-5-backend.sh"
launchctl bootstrap "gui/$(id -u)" \
  "$HOME/Library/LaunchAgents/com.business-knowledge-capture.p1-5.backend.plist"
```

This acceptance cannot claim persistent-runtime or authenticated Gemini pass
until the operator performs that local setup and runs the fictional POST/poll
flow. No Vault or Remotely Save access is required by the service.

## iPhone and cleanup boundary

Set the Shortcut backend base URL to `https://<capture-hostname>` and keep the
Bearer token out of note content and Shortcut results. Use fictional input only.
The local Obsidian write and Remotely Save observation remain user-side evidence
and must not be inferred from an HTTP response.

When acceptance ends, stop FastAPI and `cloudflared`, remove only the validated
temporary database directory, and remove the temporary token from the device.
Do not delete Cloudflare resources unless the operator explicitly requests it.
