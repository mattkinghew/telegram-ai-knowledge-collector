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
KEYCHAIN_ACCOUNT="ob-editor"
CHECK_ONLY=false

if [[ "${1:-}" == "--check" ]]; then
  CHECK_ONLY=true
elif [[ $# -gt 0 ]]; then
  print -u2 "USAGE: $0 [--check]"
  exit 64
fi

cleanup() {
  unset API_AUTH_TOKEN GEMINI_API_KEY
}
trap cleanup EXIT

keychain_secret() {
  local service="$1"
  local value
  value="$(/usr/bin/security find-generic-password \
    -s "$service" \
    -a "$KEYCHAIN_ACCOUNT" \
    -w 2>/dev/null)" || {
    print -u2 "KEYCHAIN: FAIL (required item unavailable)"
    exit 78
  }
  [[ -n "$value" ]] || { print -u2 "KEYCHAIN: FAIL (required item empty)"; exit 78; }
  print -r -- "$value"
}

check_prerequisites() {
  [[ -f "$REPO_ROOT/pyproject.toml" ]] || { print -u2 "DEPLOY: FAIL (repository)"; exit 78; }
  [[ -d "$REPO_ROOT/backend" && -d "$REPO_ROOT/web" ]] || {
    print -u2 "DEPLOY: FAIL (source runtime directories missing)"
    exit 78
  }
  [[ -x "$RUNTIME_ROOT/venv/bin/python" ]] || {
    print -u2 "DEPLOY: FAIL (existing runtime Python missing)"
    exit 78
  }
  [[ -d "$APP_ROOT/backend" && -d "$APP_ROOT/web" ]] || {
    print -u2 "DEPLOY: FAIL (installed runtime directories missing)"
    exit 78
  }
  PYTHONPATH="$APP_ROOT" "$RUNTIME_ROOT/venv/bin/python" -c \
    'import backend.app, fastapi, uvicorn' >/dev/null 2>&1 || {
    print -u2 "DEPLOY: FAIL (runtime entry point unavailable)"
    exit 78
  }
  [[ -x "$WRAPPER" ]] || { print -u2 "DEPLOY: FAIL (runtime wrapper missing)"; exit 78; }
  [[ -f "$PLIST" ]] || { print -u2 "DEPLOY: FAIL (LaunchAgent plist missing)"; exit 78; }
  /usr/bin/plutil -lint "$PLIST" >/dev/null || {
    print -u2 "DEPLOY: FAIL (LaunchAgent plist invalid)"
    exit 78
  }
  /bin/launchctl print "gui/$(/usr/bin/id -u)/$LABEL" >/dev/null 2>&1 || {
    print -u2 "DEPLOY: FAIL (LaunchAgent is not loaded)"
    exit 78
  }
}

check_prerequisites

if $CHECK_ONLY; then
  print "PREFLIGHT: PASS"
  exit 0
fi

API_AUTH_TOKEN="$(keychain_secret API_AUTH_TOKEN)"
GEMINI_API_KEY="$(keychain_secret GEMINI_API_KEY)"
unset API_AUTH_TOKEN GEMINI_API_KEY
print "KEYCHAIN: PASS"

BACKUP_ROOT="$DATA_ROOT/backups/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_ROOT"
if [[ -d "$APP_ROOT/backend" ]]; then ditto "$APP_ROOT/backend" "$BACKUP_ROOT/backend"; fi
if [[ -d "$APP_ROOT/web" ]]; then ditto "$APP_ROOT/web" "$BACKUP_ROOT/web"; fi

ditto "$REPO_ROOT/backend" "$APP_ROOT/backend"
ditto "$REPO_ROOT/web" "$APP_ROOT/web"

if ! /bin/launchctl print "gui/$(/usr/bin/id -u)/$LABEL" >/dev/null 2>&1; then
  /bin/launchctl bootstrap "gui/$(/usr/bin/id -u)" "$PLIST"
fi
/bin/launchctl kickstart -k "gui/$(/usr/bin/id -u)/$LABEL"
print "RUNTIME: PASS"

health="$(/usr/bin/curl --fail --silent --show-error --max-time 10 https://capture.lamlab.cc/health)"
[[ "$health" == *'"status":"healthy"'* ]] || { print -u2 "HEALTH: FAIL"; exit 1; }
print "HEALTH: PASS"
