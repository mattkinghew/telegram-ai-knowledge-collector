# Mobile Capture UX Decision Log

## Status

Offline design decisions for P0.9. Most evidence remains
`DEVICE_TEST_PENDING`; none is a claim about actual iPhone behavior.

## Decisions

### One Shortcut, not many

- **Decision:** Use one Shortcut named `收集靈感到 Obsidian`.
- **Reason:** One entry point reduces choice and keeps source routing inside one
  reviewed flow.
- **Tradeoff:** The Shortcut is longer and needs clear internal branches.
- **Evidence status:** `DEVICE_TEST_PENDING`.
- **Revisit trigger:** Device testing shows routing is unreliable or normal
  capture requires excessive taps.

### No required title

- **Decision:** Use timestamp filenames and `# Quick Capture` during capture.
- **Reason:** A useful title often becomes clear only during later review.
- **Tradeoff:** Inbox scanning is less descriptive before processing.
- **Evidence status:** `DEVICE_TEST_PENDING`.
- **Revisit trigger:** The 7-day pilot finds note recognition unacceptably slow.

### Three-question model

- **Decision:** Standardize user reflection as Insight, Context, and Action.
- **Reason:** It records meaning and reuse intent without classification work.
- **Tradeoff:** Two required answers add friction compared with raw dumping.
- **Evidence status:** `DEVICE_TEST_PENDING`.
- **Revisit trigger:** Median capture time or abandonment exceeds the pilot
  threshold chosen by the user.

### Question 3 is optional

- **Decision:** Action may be blank.
- **Reason:** Not every useful capture has a justified next action immediately.
- **Tradeoff:** Some notes require later action review.
- **Evidence status:** `DEVICE_TEST_PENDING`.
- **Revisit trigger:** Blank Actions strongly correlate with non-reuse.

### No mandatory category

- **Decision:** Do not classify during normal capture.
- **Reason:** Classification is a processing task, not a prerequisite to saving.
- **Tradeoff:** Inbox review retains manual organization work.
- **Evidence status:** `DEVICE_TEST_PENDING`.
- **Revisit trigger:** Later processing cannot reliably distinguish note intent.

### No mandatory tags

- **Decision:** Generate no tag array during capture.
- **Reason:** Tags create taxonomy decisions and do not prove reuse.
- **Tradeoff:** Tag-based browsing is unavailable until later processing.
- **Evidence status:** `DEVICE_TEST_PENDING`.
- **Revisit trigger:** A stable, small taxonomy is proven useful in the pilot.

### No mandatory deadline

- **Decision:** Do not ask for a deadline in the primary flow.
- **Reason:** Most knowledge captures are not scheduled tasks.
- **Tradeoff:** Time-sensitive items need later review or the existing desktop
  date workflow.
- **Evidence status:** `DEVICE_TEST_PENDING`.
- **Revisit trigger:** Users repeatedly lose time-sensitive actions.

### No mandatory AI

- **Decision:** Quick Save works without Make.com or Gemini.
- **Reason:** Provider availability and sharing permission must not control
  capture reliability.
- **Tradeoff:** Quick Save contains only user-entered structure.
- **Evidence status:** `DESIGN_ASSUMPTION`; offline rendering is confirmed, but
  device behavior remains pending.
- **Revisit trigger:** None for reliability; only the enrichment UX may change.

### Quick Save always available

- **Decision:** Offer Quick Save before AI and after every AI failure.
- **Reason:** No enrichment error may cause data loss.
- **Tradeoff:** The UI must preserve state across multiple branches.
- **Evidence status:** `DEVICE_TEST_PENDING`.
- **Revisit trigger:** Device tests expose state loss or duplicate writes.

### AI is enrichment, not capture

- **Decision:** Gemini proposes evidence support, missed points, applications,
  outputs, verification needs, and one next action.
- **Reason:** Generic summaries add less reuse value and can blur source facts.
- **Tradeoff:** The structured output is narrower than free-form prose.
- **Evidence status:** `PILOT_TEST_PENDING`.
- **Revisit trigger:** AI suggestions have low acceptance or high correction.

### No OCR in the current stage

- **Decision:** Images require a user description and optional safe filename.
- **Reason:** OCR adds provider, accuracy, permission, and attachment complexity.
- **Tradeoff:** Visible text is not extracted automatically.
- **Evidence status:** `DESIGN_ASSUMPTION`.
- **Revisit trigger:** Image reuse is materially blocked during the pilot.

### No PDF parsing in the current stage

- **Decision:** Files are references with user descriptions only.
- **Reason:** Parsing and upload are outside the safe device-independent scope.
- **Tradeoff:** File contents cannot support enrichment claims.
- **Evidence status:** `DESIGN_ASSUMPTION`.
- **Revisit trigger:** Approved file handling and privacy requirements exist.

### No Mac dependency for primary capture

- **Decision:** The primary flow ends in Obsidian Mobile; the desktop CLI is an
  optional integrity and reporting toolkit.
- **Reason:** Mobile capture should work at the moment of insight.
- **Tradeoff:** Desktop safeguards are not automatically applied before save.
- **Evidence status:** `DEVICE_TEST_PENDING`.
- **Revisit trigger:** Direct mobile note creation proves unreliable or unsafe.
