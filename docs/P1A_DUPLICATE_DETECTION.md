# P1A Exact Duplicate Detection

## Purpose

P1A warns when a new capture exactly matches an existing flat Inbox note. It is decision support for manual review, not an automatic resolution workflow.

Exact duplicate detection is deterministic equality. Semantic or fuzzy duplicate detection tries to infer similar meaning despite different content; that is outside P1A.

## Match signals

### Content hash

The feature compares complete SHA-256 values already produced by capture:

- trimmed text capture encoded as UTF-8;
- complete file bytes when the existing 20 MB hashing safety limit permits;
- the existing raw URL hash behavior.

Partial hashes and semantic comparisons are not used. A source without a comparable hash or HTTP/HTTPS URL receives `check_unavailable`.

### Conservative URL normalization

For HTTP/HTTPS only, normalization:

- lower-cases scheme and IDNA hostname;
- removes HTTP port 80 and HTTPS port 443;
- removes the fragment;
- changes an empty path to `/`.

It preserves:

- path case;
- a non-empty trailing slash;
- query parameters, order, and values;
- percent-encoded text;
- the HTTP/HTTPS distinction.

It does not remove tracking parameters, sort queries, follow redirects, infer canonical URLs, or call an external service.

## Scope and limits

Only direct `00_Inbox/*.md` candidates are listed. Before opening metadata, every candidate must be a regular Markdown file inside the selected Vault, outside Protected Paths, and free of symlink files or ancestors.

The reader stops at the end of `## Metadata`. It does not use Source Notes, One-line Summary, Key Points, Relevance, Suggested Actions, or other body sections.

- Maximum direct candidates: 5,000
- Maximum recorded match paths: 5
- Match paths: stable, sorted, Vault-relative

Malformed or unsafe candidates are skipped with a local diagnostic. More than 5,000 candidates makes the check unavailable instead of building an index.

## Metadata

Each new note records:

```text
- Duplicate Status: unique | exact_duplicate_suggested | check_unavailable
- Duplicate Match Type: none | content_hash | normalized_url | content_hash_and_url | unavailable
- Duplicate Of: comma-separated Vault-relative paths, up to five
- Duplicate Match Count: integer
```

Existing P0 notes do not require migration. Missing hash, URL, duplicate fields, or duplicate checkbox remains backward compatible.

## Manual review

```bash
bkc review \
  --vault "/absolute/path/to/Vault" \
  --note "/absolute/path/to/Vault/00_Inbox/NOTE.md" \
  --mark duplicate
```

This checks `Duplicate status reviewed`. It does not confirm a canonical note or delete, merge, or move content.

## Runtime and privacy

Python 3.9 or newer is supported. No API key, external AI, external upload, crawler, database, embedding, RAG, or vector store is used.

## Known limitations

- Exact matching intentionally misses semantically similar or reformatted content.
- Conservative URL handling intentionally treats query reordering, path case, trailing slashes, and HTTP/HTTPS as different.
- Files above the existing hashing limit may be unavailable for hash comparison.
- Only current flat Inbox metadata participates; other Vault folders are not searched.
