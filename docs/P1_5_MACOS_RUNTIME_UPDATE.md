# P1.5 macOS Runtime Update

The development repository remains under `Documents`, but the persistent
LaunchAgent runs from the user-scoped Application Support runtime so macOS
protected-folder access is not required at service start.

## Install or update

Run these commands interactively from the repository:

```sh
cp ops/macos/install-p1-5-runtime.sh.example \
  "$HOME/Library/Application Support/business-knowledge-capture/install-p1-5-runtime.sh"
chmod 700 "$HOME/Library/Application Support/business-knowledge-capture/install-p1-5-runtime.sh"
"$HOME/Library/Application Support/business-knowledge-capture/install-p1-5-runtime.sh"

# Install the LaunchAgent template for the current account.
sed "s#REPLACE_WITH_ACCOUNT#$(id -un)#g" \
  ops/macos/com.business-knowledge-capture.p1-5.backend.plist.example \
  > "$HOME/Library/LaunchAgents/com.business-knowledge-capture.p1-5.backend.plist"
```

The installer creates `~/Library/Application Support/business-knowledge-capture/runtime`
with an isolated virtualenv, installs the package and pinned hybrid
dependencies, and copies only `backend/` and `web/`. It does not copy `.git`,
`.env`, `.venv`, `data/`, secrets, or Vault content.

## Restart and verify

```sh
/bin/launchctl kickstart -k "gui/$(id -u)/com.business-knowledge-capture.p1-5.backend"
curl -fsS http://127.0.0.1:8000/health
curl -fsS https://capture.lamlab.cc/health
```

Secrets continue to come only from the existing macOS Keychain services at
process start. The service binds to `127.0.0.1:8000`; Cloudflare remains the
public ingress.
