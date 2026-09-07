# OB Editor V0.1 Manual Secure Deployment

This handoff is for the repository owner to run in a normal macOS Terminal.
Codex cannot access the macOS login Keychain in its sandbox. Do not paste
secret values into chat, files, Git, or command output.

## 1. Prerequisites

```sh
cd /Users/mattgor/Documents/Codex/telegram-ai-knowledge-collector
security find-generic-password -a ob-editor -s API_AUTH_TOKEN -w >/dev/null
security find-generic-password -a ob-editor -s GEMINI_API_KEY -w >/dev/null
```

Both commands must exit successfully. The existing production URL is
`https://capture.lamlab.cc`; this procedure does not create another deployment
or change either secret.

## 2. Git checkpoint

Inspect first, then stage only the intended V0.1 files. Do not use `git add .`,
reset, clean, force push, or history rewrite.

```sh
git status --short
git add -- .gitignore backend/routes/captures.py backend/services/capture.py \
  ops/macos/run-p1-5-backend.sh.example \
  scripts/deploy_ob_editor_v01.sh scripts/smoke_ob_editor_v01.sh \
  tests/test_ob_editor_v01_capture_contract.py tests/fixtures/ob_editor_v01 \
  tests/test_p1_5_backend_services.py tests/test_p1_5_capture_api.py \
  tests/test_p1_5_e2e.py tests/test_p1_5_gemini_provider.py \
  tests/test_p1_5_operations_api.py tests/test_p1_5_process_restart.py \
  docs/API_CONTRACT.md docs/CURRENT_STATE.md docs/DEPLOYMENT.md \
  docs/IPHONE_ACCEPTANCE_TEST.md docs/MANUAL_SECURE_DEPLOY.md \
  docs/ONLINE_V01_VALIDATION.md docs/SHORTCUT_COMPATIBILITY.md \
  docs/TEST_PLAN.md docs/V01_STABILIZATION_PLAN.md
git diff --cached --stat
git diff --cached --check
git commit -m "feat: stabilize ob editor v0.1 capture workflow"
git rev-parse HEAD
git status --short
```

If Git reports `.git/index.lock` blocked by the execution environment, stop and
run these commands in the normal macOS Terminal. Do not delete the lock or use
an unsafe workaround.

## 3. Local tests

Recreate the environment only from the existing dependency definitions if `.venv`
is absent:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[hybrid]"
PYTHONPYCACHEPREFIX=/private/tmp/ob-editor-v01-pycache \
PYTHONPATH=src:. .venv/bin/python -m unittest \
  tests.test_ob_editor_v01_capture_contract tests.test_p1_5_capture_api \
  tests.test_p1_5_backend_services tests.test_p1_5_e2e
```

No automated command makes a paid or live Gemini call.

## 4. Deployment

After the checkpoint and passing local tests, run the manual helper from the
repository:

```sh
./scripts/deploy_ob_editor_v01.sh
```

It retrieves both Keychain items without printing them, backs up the installed
`backend/` and `web/`, uses the existing LaunchAgent, preserves the SQLite
database outside the repository, restarts the same service, and checks health.

## 5. Online smoke test

```sh
./scripts/smoke_ob_editor_v01.sh
```

The script uses only fictional text. It checks health, anonymous HTTP 401,
authenticated POST/GET, canonical `id` plus legacy `capture_id`, allowed
statuses, processed `result` or failed `error`, raw recovery, and unknown-ID
HTTP 404. It does not inject production failures and does not modify the
iPhone Shortcut.

## 6. Expected PASS

Expected safe summaries include `KEYCHAIN: PASS`, `HEALTH: PASS`,
`AUTH_GUARD: PASS`, `POST_CAPTURE: PASS`, `GET_CAPTURE: PASS`,
`RAW_RECOVERY: PASS`, and `UNKNOWN_CAPTURE: PASS`. A processed run also emits
`RESULT: PASS`; a failed run must emit `FAILED_ERROR: PASS`.

The current HTTP 500 response for processing/domain failures is intentionally
unchanged. Resolve its iOS compatibility during real-device acceptance.

## 7. Troubleshooting

- Keychain failure: stop; confirm the two item names and account in the login
  Keychain without exposing their values.
- Health failure: inspect the existing LaunchAgent with `launchctl print` and
  its documented stderr log; do not create a second service.
- A capture remains `pending`: the existing process-local `BackgroundTasks`
  limitation may have stranded it; raw input remains available via GET and the
  bounded retry endpoint.
- Never add a public debug or failure-injection endpoint for this test.

## 8. Rollback

The deployment helper creates a timestamped backup under:
`~/Library/Application Support/business-knowledge-capture/backups/`.

Restore only the backed-up runtime directories, then restart the same
LaunchAgent:

```sh
DATA_ROOT="$HOME/Library/Application Support/business-knowledge-capture"
LABEL="com.business-knowledge-capture.p1-5.backend"
/bin/launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
ditto "$DATA_ROOT/backups/<timestamp>/backend" "$DATA_ROOT/runtime/app/backend"
ditto "$DATA_ROOT/backups/<timestamp>/web" "$DATA_ROOT/runtime/app/web"
/bin/launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/$LABEL.plist"
/bin/launchctl kickstart -k "gui/$(id -u)/$LABEL"
curl --fail --silent https://capture.lamlab.cc/health >/dev/null
```

Replace `<timestamp>` with the verified backup directory. Rollback does not
delete or overwrite the SQLite capture database; preserve capture data and
repeat the fictional smoke test after recovery.
