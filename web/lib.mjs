const PAGES = new Set(["today", "inbox", "projects", "pending", "reports"]);

export function pageFromHash(hash) {
  const value = String(hash || "").replace(/^#/, "").toLowerCase();
  return PAGES.has(value) ? value : "today";
}

export function buildListQuery(filters = {}) {
  const params = new URLSearchParams();
  const page = Number.isInteger(filters.page) && filters.page > 0 ? filters.page : 1;
  const pageSize = Number.isInteger(filters.page_size) && filters.page_size > 0
    ? Math.min(filters.page_size, 100)
    : 20;
  params.set("page", String(page));
  params.set("page_size", String(pageSize));
  for (const key of [
    "status",
    "capture_type",
    "source_type",
    "requested_processing",
    "project",
    "query",
    "created_from",
    "created_to",
  ]) {
    const value = filters[key];
    if (typeof value === "string" && value.trim()) params.set(key, value.trim());
  }
  return `?${params.toString()}`;
}

export function reportPayload(reportType, period, captureIds) {
  if (!["daily", "period"].includes(reportType)) throw new Error("Unsupported report type");
  if (typeof period !== "string" || !period.trim()) throw new Error("Period is required");
  if (!Array.isArray(captureIds) || captureIds.length < 1 || captureIds.length > 50) {
    throw new Error("Select 1–50 captures");
  }
  if (new Set(captureIds).size !== captureIds.length) throw new Error("Duplicate capture selection");
  return { report_type: reportType, period: period.trim(), capture_ids: captureIds };
}

export function userMessageForError(code) {
  const messages = {
    AI_UNAVAILABLE: "AI temporarily unavailable — capture was saved.",
    URL_FETCH_FAILED: "Article could not be extracted — original URL was preserved.",
    PAYLOAD_TOO_LARGE: "The request was too large — reduce it and try again.",
    AUTH_REQUIRED: "Enter a valid API token for this session.",
    INTERNAL_ERROR: "Processing failed — retry or keep the raw capture.",
  };
  return messages[code] || "The request could not be completed. Try again or keep the raw capture.";
}

export function element(tag, options = {}, children = []) {
  const item = document.createElement(tag);
  if (options.className) item.className = options.className;
  if (options.text !== undefined) item.textContent = String(options.text);
  for (const [name, value] of Object.entries(options.attributes || {})) {
    item.setAttribute(name, String(value));
  }
  for (const child of children) item.append(child);
  return item;
}

export function captureCard(record, actions = []) {
  const meta = element("div", { className: "meta" }, [
    element("span", { text: record.capture_type || "capture" }),
    element("span", { text: record.status || "unknown" }),
    element("span", { text: record.requested_processing || "raw_save" }),
  ]);
  const body = [
    element("h3", { text: record.title || "Captured item" }),
    meta,
    element("p", { className: "muted", text: record.source || record.source_type || "Local capture" }),
  ];
  if (record.assigned_project) body.push(element("p", { text: `Project: ${record.assigned_project}` }));
  if (record.error_message) body.push(element("p", { className: "error-copy", text: record.error_message }));
  if (actions.length) {
    const row = element("div", { className: "action-row" });
    for (const action of actions) {
      row.append(element("button", {
        className: action.secondary ? "button secondary" : "button",
        text: action.label,
        attributes: { type: "button", "data-action": action.name, "data-id": record.capture_id },
      }));
    }
    body.push(row);
  }
  return element("article", { className: "capture-card" }, body);
}
