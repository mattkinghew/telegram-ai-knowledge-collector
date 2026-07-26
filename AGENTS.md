# AGENTS.md

## Scope

This repository contains the existing Telegram / Make.com collector blueprint and the local Business Knowledge Capture & Reporting MVP.

## Mandatory workflow

1. Read `README.md`, `docs/CONTEXT_SUMMARY.md`, and relevant workflow/privacy docs before editing.
2. Inspect Git state and preserve user changes.
3. Implement only approved P0 scope before P1 or stretch goals.
4. Run compile, unit tests, and CLI smoke tests.
5. Update documentation and report known limitations.

## Safety

- Never request, create, or commit `.env`, API keys, passwords, tokens, or credentials.
- Never scan an entire Obsidian vault.
- Check protected paths before any file read, metadata access, hash, copy, move, rename, summary, or index operation.
- Never inspect `20_Areas/25_Self_Management`, `25_Self_Management`, `Private`, `Credentials`, `.env`, or `.obsidian`.
- Do not process private company files or upload company data to personal Google Drive.
- Do not auto-deploy, auto-push, auto-publish, or modify production.
- Do not add OCR, RAG, vector databases, chatbots, or agent frameworks to P0.

## Definition of Done

A feature is complete only when the full flow works, inputs are validated, errors are understandable, outputs are preserved, protected paths remain untouched, tests pass, and documentation supports handoff.
