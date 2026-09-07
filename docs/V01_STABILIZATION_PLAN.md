# OB Editor V0.1 — Stabilization Plan

## P0 required for daily use

- Make capture responses deterministic around exactly four processing states:
  `pending`, `processing`, `processed`, and `failed`.
- Persist raw input before any AI or URL processing and preserve it on every
  failure path. The existing SQLite boundary already satisfies this; add
  regression coverage rather than a migration.
- Normalize single-capture POST, GET, and background-processing responses to a
  canonical envelope. Processed responses include `result`; non-processed
  responses omit it; failed responses include a bounded nested `error`.
- Convert AI, malformed-AI, extraction, and timeout failures to `failed`.
  Keep `pending` for accepted work not yet started and `processing` for work in
  progress.
- Remove `PROCESSING_QUEUED` from the client-visible contract. Queueing is
  represented by `pending` only.
- Add fake-provider API tests for valid input, validation failure, all state
  transitions, AI failure, malformed output, timeout, unknown ID, and raw
  recovery.

## P1 useful

- Add an explicit operator-facing stale-processing recovery command or
  scheduled reconciliation for rows left `processing` after a process crash.
- Add idempotency support for Shortcut retries after ambiguous network
  failures, once the client contract is agreed.
- Add structured request correlation metadata without logging raw content or
  credentials.

## Later

- Durable background execution or a managed queue, only if daily volume and
  recovery needs justify the operational cost.
- Shortcut changes for idempotency and a simplified success/failure branch.
- Production deployment and real-device acceptance.

No P0 item requires RAG, agents, a vector database, new cloud infrastructure,
accounts, or a major database migration.
