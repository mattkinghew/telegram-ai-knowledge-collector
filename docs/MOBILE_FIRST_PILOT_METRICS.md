# Mobile-first 7-day Pilot Metrics

## Status

Measurement plan only. No pilot has run and no metric value is claimed.

Use fictional or personal non-sensitive notes unless the user has explicit
permission and an approved service/data policy. Store no Vault identifier,
credential, private path, or raw confidential content in the metric log.

## Pilot Unit

- **Period:** seven consecutive user-selected days.
- **Eligible capture:** a note the user intentionally attempts to save through
  the V3 Shortcut.
- **Reuse window:** the pilot period, with a final review at the end of day 7.
- **AI-eligible capture:** a capture where the user explicitly selects AI and
  is permitted to send the content to the configured services.

Record timestamps only as needed for duration and collision analysis. Link to
approved evidence using a public-safe or local identifier; do not copy private
note content into the metrics sheet.

## Primary Metrics

### Median capture time

```text
start = user launches Shortcut or invokes Share Sheet action
end   = user directly confirms the note exists in Obsidian
metric = median(end - start) for successful captures
```

Record failed and abandoned attempts separately rather than excluding them
silently.

### Percentage of captured notes later reused

```text
notes with at least one confirmed reuse during the pilot
÷ successfully captured notes
```

Reuse means the note contributes to a task, decision, project input, content,
or progress update. Opening or syncing the note alone is not reuse.

### Conversion by output

For each confirmed outcome, report the percentage of successful captures later
converted into:

```text
task
decision
project input
content
progress update
```

One note may contribute to more than one outcome. State that percentages may
therefore sum to more than 100%.

### AI suggestion acceptance rate

```text
AI attempts where at least one suggestion was explicitly accepted
÷ valid AI responses shown to the user
```

Do not count failure fallback or responses rejected by schema validation.

### AI correction rate

```text
accepted AI responses edited before save
÷ accepted AI responses
```

Record only whether correction occurred, not private corrected text.

### Wrong project suggestion rate

```text
valid AI responses whose related_project was rejected or corrected
÷ valid AI responses that suggested a project
```

A null suggestion is not wrong. A project outside `AllowedProjects` is a
contract failure and should be recorded separately.

### Capture abandonment rate

```text
attempts stopped before an Obsidian note is confirmed
÷ all eligible capture attempts
```

Record the last visible stage and a short public-safe reason when known.

### Remotely Save conflict rate

```text
successfully captured notes producing an unexplained conflict or duplicate
÷ successfully captured notes synchronized during the pilot
```

Record missing sync separately from conflict copies.

## Minimal Daily Record

| Field | Allowed value |
|---|---|
| Pilot capture ID | fictional/local identifier |
| Input type | typed, voice, clipboard, URL, selected text, image, file |
| Start/end | local timestamps or duration |
| Result | saved, abandoned, failed |
| Output reuse | none, task, decision, project, content, progress |
| AI | not used, accepted, corrected, rejected, failed |
| Project suggestion | none, accepted, corrected, contract failure |
| Sync | confirmed, pending, missing, conflict |
| Unexpected taps | integer and brief reason |
| Format/data loss | none or public-safe description |

## Review Questions

At day 7, use the metrics to answer:

1. Is the median successful capture time acceptable to the user?
2. Which step causes abandonment or unexpected taps?
3. Do captures become useful work products?
4. Does AI enrichment improve reuse enough to justify its friction and privacy
   boundary?
5. Are project suggestions reliable enough to retain?
6. Does Remotely Save introduce a material conflict risk?

Choose thresholds after baseline observations; do not invent success targets in
advance or reinterpret missing data as success.

## Metrics Not Used as Primary Success Measures

Do not optimize mainly for:

```text
number of notes
number of AI summaries
number of tags
```

These counts measure activity, not whether captured knowledge is reused.
