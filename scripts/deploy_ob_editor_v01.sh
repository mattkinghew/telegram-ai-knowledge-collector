#!/bin/zsh

# Manual operator-run deployment for the existing OB Editor LaunchAgent.
# Secrets are read only into process memory and are never printed or persisted.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DATA_ROOT="$HOME/Library/Application Support/business-knowledge-capture"
RUNTIME_ROOT="$DATA_ROOT/runtime"
APP_ROOT="$RUNTIME_ROOT/app"
WRAPPER="$DATA_ROOT/run-p1-5-backend.sh"
PLIST="$HOME/Library/LaunchAgents/com.business-knowledge-capture.p1-5.backend.plist"
LABEL="com.business-knowledge-capture.p1-5.backend"
ACCOUNT="ob-editor"

cleanup() {
  unset API_AUTH_TOKEN GEMINI_API_KEY
}
trap cleanup EXIT

keychain_secret() {
  local service="$1"
  local value
  value="$(/usr/bin/security find-generic-password -a "$ACCOUNT" -s "$service" -w 2>/dev/null)" || {
    print -u2 "KEYCHAIN: FAIL ($service unavailable)"
    exit 78
  }
  [[ -n "$value" ]] || { print -u2 "KEYCHAIN: FAIL ($service empty)"; exit 78; }
  print -r -- "$value"
}

[[ -f "$REPO_ROOT/pyproject.toml" ]] || { print -u2 "DEPLOY: FAIL (repository)"; exit 78; }
[[ -x "$DATA_ROOT/install-p1-5-runtime.sh" ]] || { print -u2 "DEPLOY: FAIL (existing installer missing)"; exit 78; }

API_AUTH_TOKEN="$(keychain_secret API_AUTH_TOKEN)"
GEMINI_API_KEY="$(keychain_secret GEMINI_API_KEY)"
unset API_AUTH_TOKEN GEMINI_API_KEY
print "KEYCHAIN: PASS"

BACKUP_ROOT="$DATA_ROOT/backups/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_ROOT"
if [[ -d "$APP_ROOT/backend" ]]; then ditto "$APP_ROOT/backend" "$BACKUP_ROOT/backend"; fi
if [[ -d "$APP_ROOT/web" ]]; then ditto "$APP_ROOT/web" "$BACKUP_ROOT/web"; fi

"$DATA_ROOT/install-p1-5-runtime.sh"
mkdir -p "$HOME/Library/LaunchAgents"
ditto "$REPO_ROOT/ops/macos/run-p1-5-backend.sh.example" "$WRAPPER"
chmod 700 "$WRAPPER"

sed -e "s#/Users/REPLACE_WITH_ACCOUNT#${HOME}#g" \
  "$REPO_ROOT/ops/macos/com.business-knowledge-capture.p1-5.backend.plist.example" > "$PLIST"
chmod 600 "$PLIST"
/usr/bin/plutil -lint "$PLIST" >/dev/null

if ! /bin/launchctl print "gui/$(/usr/bin/id -u)/$LABEL" >/dev/null 2>&1; then
  /bin/launchctl bootstrap "gui/$(/usr/bin/id -u)" "$PLIST"
fi
/bin/launchctl kickstart -k "gui/$(/usr/bin/id -u)/$LABEL"
print "RUNTIME: PASS"

health="$(/usr/bin/curl --fail --silent --show-error --max-time 10 https://capture.lamlab.cc/health)"
[[ "$health" == *'"status":"healthy"'* ]] || { print -u2 "HEALTH: FAIL"; exit 1; }
print "HEALTH: PASS"
