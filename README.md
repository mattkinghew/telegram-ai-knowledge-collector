# Telegram AI Knowledge Collector

An AI-powered personal signal intelligence pipeline that turns noisy Telegram messages into structured, searchable knowledge notes.

## Problem

Social media feeds are noisy. Algorithms often miss high-signal job posts, AI product updates, cybersecurity news, and practical learning resources.

This project helps me collect, summarize, classify, and review useful information from Telegram for career transition and personal knowledge management.

## Features

- Capture Telegram messages automatically
- Summarize content with Gemini
- Extract action items, job opportunities, and technical keywords
- Store structured notes in Google Sheets
- Prepare content for Notion / Obsidian review

## Architecture

Telegram Bot → Make.com Webhook → Gemini API → Google Sheets

## Data Schema

| Field | Description |
|---|---|
| created_at | Collection timestamp |
| source_text | Original Telegram message |
| source_url | Extracted URL if available |
| title | AI-generated title |
| summary | 3-5 bullet summary |
| tags | Knowledge tags |
| action_items | Suggested next actions |
| job_signal | Whether it contains job/course/opportunity signal |
| relevance_score | 1-5 usefulness score |
| status | processed / failed / skipped |

## Security Notes

- No API keys are committed
- Personal account IDs are replaced with placeholders
- Blueprint is provided as a reusable template

## Roadmap

- Add deduplication
- Add error handling and retry flow
- Add weekly digest
- Add semantic search / RAG
