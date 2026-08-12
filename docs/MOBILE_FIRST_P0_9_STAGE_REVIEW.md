# Mobile-first P0.9 Stage Review

## Result

The device-independent contract and reference implementation are complete and
validated offline on 2026-08-13 with Python 3.9.6.

```text
IMPLEMENTATION CONTRACT COMPLETE
OFFLINE VALIDATION COMPLETE

DEVICE ACCEPTANCE PENDING
AI SERVICE ACCEPTANCE PENDING
```

This review does not claim that an iPhone Shortcut, Obsidian URI, Remotely
Save, Make.com scenario, or Gemini integration works on a real service.

## Architecture Preserved

### Primary mobile flow

```text
iPhone Shortcut
→ Capture
→ Insight / Context / Action
→ optional Knowledge Enrichment
→ Preview
→ Obsidian Mobile
→ direct 00_Inbox note
→ user-configured Remotely Save
```

### Secondary desktop role

The existing CLI remains the verified toolkit for integrity checks, exact
duplicate audit, bounded metadata search, date review, controlled handoff,
progress reports, and export. No existing CLI module or behavior was changed.

### JSON fallback

The existing schema-version-1 JSON handoff remains available for explicit
desktop validation, preview, and import. It was not removed or modified.

### AI role

Gemini is specified as a Knowledge Enrichment Assistant. It returns bounded,
unconfirmed suggestions rather than generic prose and never owns capture
reliability.

## Completed Without Device

- Canonical mobile contract with Raw Content, Source, Insight, Context, Action,
  Output Goal, Project, and separate AI Suggestions.
- Simplified mobile note template with optional Project and Action, no required
  title, and no Quick Save AI section.
- Dependency-free reference Markdown renderer.
- Dependency-free Obsidian URI builder with independent percent encoding.
- Timestamp filename and explicit same-second collision suffix reference.
- Twenty fictional golden mobile-capture fixtures.
- Offline renderer, validation, Unicode, multiline, URL, URI, and privacy tests.
- One-Shortcut V3 implementation specification.
- Source-specific URL, selected text, voice, clipboard, image, and file rules.
- UX decision log and staged device acceptance pack.
- Seven-day pilot measurement plan.
- Version-2 Knowledge Enrichment prompt.
- Strict version-2 request and response schemas while V1 remains unchanged.
- Twelve fictional enrichment contract fixtures.
- Dependency-free deterministic non-AI simulator and failure modes.
- Implementation-oriented five-module Make.com map.
- Common AI failure contract and Quick Save fallback.
- Mobile capture privacy model.

## Offline Validation Evidence

| Check | Result |
|---|---|
| Existing test baseline | 291 retained tests |
| New contract tests | 21 tests |
| Total discovered and executed | 312 tests; passing command exit status |
| Compile | `src`, `tests`, and `tools` compiled successfully |
| Desktop CLI smoke | `business_knowledge_capture.cli --help` passed |
| Reference tool smoke | both development tool `--help` commands passed |
| JSON syntax | every tracked/repository JSON file parsed with `json.tool` |
| Focused capture tests | 11 passed |
| Focused enrichment tests | 10 passed |
| Diff whitespace | `git diff --check` passed |
| Network or service call | none |
| Real Vault access | none |

`jsonschema` was not available in the local environment. No package was
installed and no production or development dependency was changed. Custom
standard-library validation and schema-structure tests cover required fields,
unknown fields, bounds, enums, URL rules, local-path rejection, project
allowlisting, success envelopes, and failure codes. Full draft-2020-12 semantic
schema validation remains pending in an approved development environment.

## Still Requires a Real Device

- Actual creation of `BKC Mobile Test`.
- Actual Obsidian URI opening.
- Actual direct `00_Inbox` write.
- Actual Traditional Chinese and Markdown rendering in Obsidian Mobile.
- Actual Remotely Save synchronization and conflict behavior.
- Actual full V3 Shortcut construction.
- Actual typed, clipboard, and Dictate Text behavior.
- Actual Share Sheet URL, selected text, image, and file behavior.
- Actual iOS permission prompts, cancellation, and state preservation.
- Actual URI size limits with long content.

## Still Requires External-service Acceptance

- Actual Make.com webhook and five-module scenario.
- Current Make.com mapping and error-handler behavior.
- Approved Make.com account, region, history, and retention settings.
- Approved Gemini connection and current provider data-use settings.
- Actual structured output and timeout behavior.
- Actual invalid-response fallback in the Shortcut.
- Confirmation that no credential or raw private data appears in service logs.

## Claim Boundary

Allowed wording:

```text
IMPLEMENTATION CONTRACT COMPLETE
OFFLINE VALIDATION COMPLETE
DEVICE ACCEPTANCE PENDING
AI SERVICE ACCEPTANCE PENDING
```

Do not use:

```text
mobile feature complete
production ready
iPhone verified
Gemini integration complete
```

The public README remains unchanged until real-device acceptance supports a
product-claim update.

## Risks and Open Questions

1. `obsidian://new` behavior and practical URI length limits are not proven on
   the user's iPhone/Obsidian versions. The 50,000-character contract bound is
   an input-safety bound, not a device acceptance claim.
2. Seconds-level timestamp filenames can collide. The contract supports an
   explicit suffix, but the real Shortcut collision UX must be observed.
3. Dictate Text privacy and availability depend on current device settings and
   provider behavior.
4. Remotely Save conflicts, duplicate creation, and remote retention require
   direct inspection.
5. Make.com and Gemini field mapping, structured output, timeout, logging, and
   retention controls are specified but not configured or tested.
6. Draft-2020-12 semantic schema validation is pending because `jsonschema`
   was unavailable and adding a dependency was outside the approved scope.

## Manual Gates

### Gate A — Architecture

Build and run only the four-action fixed-Markdown `BKC Mobile Test`; confirm
one direct-Inbox note, intact Chinese/Markdown, and one Remotely Save copy.

### Gate B — Full Shortcut

After Gate A passes, build V3 and test typed, voice, and clipboard Quick Save.

### Gate C — Share Sheet

Test public-safe URL, selected text, image reference, and file reference inputs.

### Gate D — AI Enrichment

After privacy approval and scenario construction, test success, unavailable,
timeout, invalid JSON, schema mismatch, and fallback Quick Save.

## Recommended Next Manual Action

Build `BKC Mobile Test` on the iPhone, insert the real Vault identifier only on
the device, and run the fixed Markdown architecture test once.
