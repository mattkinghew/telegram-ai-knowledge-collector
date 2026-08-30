# Testing

```bash
PYTHON_BIN="$(command -v python3)"
"$PYTHON_BIN" --version
"$PYTHON_BIN" -m compileall -q src tests tools
PYTHONPATH=src "$PYTHON_BIN" -m unittest discover -s tests -v
PYTHONPATH=src "$PYTHON_BIN" -m business_knowledge_capture.cli --help
PYTHONPATH=src "$PYTHON_BIN" -m business_knowledge_capture.cli due --help
PYTHONPATH=src "$PYTHON_BIN" -m business_knowledge_capture.cli search --help
PYTHONPATH=src "$PYTHON_BIN" -m business_knowledge_capture.cli report --help
PYTHONPATH=src "$PYTHON_BIN" -m business_knowledge_capture.cli handoff --help
PYTHONPATH=src "$PYTHON_BIN" -m business_knowledge_capture.cli handoff validate --help
PYTHONPATH=src "$PYTHON_BIN" -m business_knowledge_capture.cli handoff preview --help
PYTHONPATH=src "$PYTHON_BIN" -m business_knowledge_capture.cli handoff import --help
```

P1.5 requires the explicit hybrid extra. Use an isolated environment:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[hybrid]"
PYTHONPYCACHEPREFIX=/tmp/p1-5-pycache \
  PYTHONPATH=src:. .venv/bin/python -m compileall -q src tests tools backend
PYTHONPATH=src:. .venv/bin/python -m unittest discover -s tests -v
node --test web/tests/lib.test.mjs
node --check web/app.js
node --check web/lib.mjs
node --check web/sw.js
```

Run only the new full-flow acceptance with:

```bash
PYTHONPATH=src:. .venv/bin/python -m unittest tests.test_p1_5_e2e -v
```

Run guarded Gemini adapter tests with:

```bash
PYTHONPATH=src:. .venv/bin/python -m unittest \
  tests.test_p1_5_gemini_provider -v
```

The article E2E uses a local HTML fixture and fake transport. The voice and
pending flows use fictional payloads, local SQLite, TestClient, and
MockProvider. Gemini tests use HTTPX MockTransport. None performs a live HTTP,
Gemini, iPhone, Vault, or Remotely Save
operation. Static Web tests prove routing helpers, bounded filters, report
selection, error copy, shell assets, security headers, and implementation
markers; they do not replace real browser/accessibility/device acceptance.

The minimum supported runtime is Python 3.9. GitHub Actions repeats compile, unit tests, and CLI help on Python 3.9, 3.10, 3.11, and 3.12. No API key is needed.

Temporary non-sensitive smoke test:

```bash
mkdir -p /tmp/bkc-vault/00_Inbox
mkdir -p /tmp/bkc-vault/10_Work/11_Projects
mkdir -p /tmp/bkc-vault/90_System

PYTHONPATH=src "$PYTHON_BIN" -m business_knowledge_capture.cli init --vault /tmp/bkc-vault
PYTHONPATH=src "$PYTHON_BIN" -m business_knowledge_capture.cli capture \
  --vault /tmp/bkc-vault \
  --text "AI PM onboarding example" \
  --title "Smoke test"
PYTHONPATH=src "$PYTHON_BIN" -m business_knowledge_capture.cli validate --vault /tmp/bkc-vault
```

Safety coverage includes duplicate project detection, Protected Paths merging, template conflicts, symlink blocking, Vault note scope, URL/redirect validation, metadata newline sanitization, and manual classification consistency.

The 2026-07-26 P0 acceptance ran 33 tests on local Python 3.9.6 and completed an isolated 11-input end-to-end flow plus a scoped real-Vault acceptance. GitHub-hosted matrix execution remains observable only after a future push or pull request.

P1A adds exact duplicate coverage for:

- direct-only flat Inbox scope, candidate limit, malformed candidates, protected paths, symlinks, and Vault-external files;
- identical text and file bytes, unavailable fingerprints, and non-matching content;
- conservative URL normalization and false-positive boundaries;
- unique, hash, URL, combined, count, capped relative-path, CLI warning, and manual-review metadata;
- P0 note review/report backward compatibility and an isolated end-to-end flow.

No network, API key, external AI, external upload, database, or semantic matching is required.

The 2026-07-26 P1A acceptance ran 67 tests on Python 3.9.6: 33 retained P0 tests and 34 P1A tests. The isolated and scoped real-Vault flows both passed. GitHub-hosted execution remains pending because the accepted task prohibits push and pull-request creation.

P1B adds metadata-only search coverage for:

- flat direct Inbox scope, candidate limit, protected-path and symlink controls, read-only hashes, and Vault-relative output;
- bounded H1/Metadata parsing, old P0/P1A notes, missing fields, invalid dates, malformed candidates, and capped diagnostics;
- same-field OR, different-field AND, all supported filters, inclusive ISO dates, zero results, and file-type exact equality;
- all six stable sort modes, missing-date ordering, relative-path tie-breaking, default/custom result limits, text output, and strict JSON allowlisting;
- Source Notes, Source URL, Local File, Content Hash, and absolute Vault path exclusion.

No full-text search, database, SQLite, background index, semantic search, embedding, RAG, network, or Vault write is required.

P1C adds coverage for strict capture/review date validation, atomic set/clear,
manual date review, three event types, deterministic status and sorting,
same-field OR/different-field AND filters, malformed-date diagnostics, strict
text/JSON output, search integration, direct-only scope, candidate limits, and
read-only candidate hashes.

All date-sensitive tests use an explicit reference date. The isolated E2E uses
an actual non-symlink temporary path because the runtime intentionally rejects
symlink ancestors.

The 2026-07-26 P1C acceptance ran 147 tests on Python 3.9.6: 124 retained
P0/P1A/P1B tests and 23 P1C tests. Isolated and scoped real-Vault date-review
flows both passed. GitHub-hosted execution remains pending because no push or
pull request is permitted.

P1D adds focused coverage for:

- stable deadline, resource-expiry, and reminder keys in text and strict JSON;
- selection syntax, direct-Inbox scope, traversal, protected-path, regular-file,
  symlink, missing-note, and absolute-path controls;
- current-date equality, stale/cleared events, full validation before write,
  duplicate handling, and the 50-selection limit;
- dynamic status and deterministic date/type/title/path sorting;
- metadata-only selected-note reads, relative source traceability, unchanged
  selected notes, and no automatic event inclusion;
- daily/weekly compatibility, atomic report creation, Python 3.9, and CLI help.

P1E adds 83 focused tests for exact-file safety, strict JSON parsing, schema and
source-type rules, timezone-aware timestamps, no-network URL import,
content-hidden preview, existing duplicate/date/capture integration, atomic
single-note creation, retained handoff files, manual handoff/transcript review,
protected paths, Python 3.9, search compatibility, and CLI parsing.

The retained baseline is 208 tests. With P1E the expected local total is 291.
GitHub-hosted matrix execution remains pending until a future approved push or
pull request.

P1.4 adds focused offline coverage for the two recommended daily entries:

- P1.3 voice reuse, structured and pending notifications, and exact transcript;
- deterministic article/social/video URL routing without a category question;
- shared/selected/clipboard text, image, and file reference boundaries;
- URL-only pending behavior without a false summary;
- raw save, pending save, summary, short article, and recommendation modes;
- strict suggestion validation, source/suggestion separation, and no data loss.

Run only this increment with:

```bash
PYTHONPATH=src "$PYTHON_BIN" -m unittest tests.test_two_entry_capture_p1_4 -v
```

P1.5 adds coverage for:

- strict request/provider contracts, stable UUIDs, validation and payload caps;
- SQLite pending/processing/processed/failed state, raw preservation, bounded
  manual retry, pagination, review, project allowlist and no-delete behavior;
- mock processing modes, Markdown evidence layers and safe provider errors;
- public URL/DNS/redirect SSRF rejection, time/redirect/byte/MIME/text limits,
  and conservative local-fixture HTML extraction;
- authenticated capture/status/list/retry/dashboard/project/report APIs,
  production fail-closed auth, CORS and security headers;
- Today, Inbox, Projects, Pending, Reports, search helpers, PWA shell-only cache,
  loading/empty/error copy and safe DOM/token handling;
- integrated voice, article, pending/failure and Inbox-data flows.
- guarded Gemini configuration, minimal prompts, four allowlisted modes,
  strict structured output, safe timeout/network/auth/quota/error mapping,
  oversized-response rejection, raw preservation, and bounded manual retry.

Do not record a final test count in this file until the final suite has been run
against the exact documented commit.
