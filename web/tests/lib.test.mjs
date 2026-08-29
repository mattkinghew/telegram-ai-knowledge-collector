import test from "node:test";
import assert from "node:assert/strict";

import {
  buildListQuery,
  pageFromHash,
  reportPayload,
  userMessageForError,
} from "../lib.mjs";

test("pageFromHash allows only the five primary pages", () => {
  assert.equal(pageFromHash("#pending"), "pending");
  assert.equal(pageFromHash("#unknown"), "today");
});

test("buildListQuery includes only bounded supported filters", () => {
  assert.equal(
    buildListQuery({ status: "pending", query: "fictional evidence", page: 2 }),
    "?page=2&page_size=20&status=pending&query=fictional+evidence",
  );
  assert.equal(buildListQuery({ page: -1, unexpected: "x" }), "?page=1&page_size=20");
});

test("reportPayload requires human-selected unique records", () => {
  assert.deepEqual(reportPayload("daily", "2026-08-30", ["a", "b"]), {
    report_type: "daily",
    period: "2026-08-30",
    capture_ids: ["a", "b"],
  });
  assert.throws(() => reportPayload("daily", "2026-08-30", []));
  assert.throws(() => reportPayload("period", "2026-08", ["a", "a"]));
});

test("errors map to actionable capture-safe language", () => {
  assert.equal(
    userMessageForError("AI_UNAVAILABLE"),
    "AI temporarily unavailable — capture was saved.",
  );
  assert.equal(
    userMessageForError("URL_FETCH_FAILED"),
    "Article could not be extracted — original URL was preserved.",
  );
  assert.equal(
    userMessageForError("INTERNAL_ERROR"),
    "Processing failed — retry or keep the raw capture.",
  );
});
