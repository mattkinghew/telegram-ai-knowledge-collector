import {
  buildListQuery,
  captureCard,
  element,
  pageFromHash,
  reportPayload,
  userMessageForError,
} from "/app/lib.mjs";

const UI_COPY = ["Loading", "Nothing to review", "Retry", "Keep raw", "Dismiss processing", "Assign project"];
const state = { token: "", page: pageFromHash(location.hash), records: [] };
const main = document.querySelector("#main-content");
const status = document.querySelector("#app-status");
const title = document.querySelector("#page-title");
const dialog = document.querySelector("#detail-dialog");
const detailContent = document.querySelector("#detail-content");

function setStatus(message) { status.textContent = message; }
function clearMain() { main.replaceChildren(); }
function showState(className, heading, message) {
  clearMain();
  main.append(element("section", { className }, [
    element("h2", { text: heading }),
    element("p", { text: message }),
  ]));
}

async function api(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  const response = await fetch(path, { ...options, headers });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(body.error?.message || "Request failed");
    error.code = body.error?.code || "INTERNAL_ERROR";
    throw error;
  }
  return body;
}

function section(name) {
  const wrapper = element("section");
  wrapper.append(element("div", { className: "section-header" }, [element("h2", { text: name })]));
  return wrapper;
}

function cards(records, actions = []) {
  const list = element("div", { className: "card-list" });
  if (!records.length) {
    list.append(element("div", { className: "empty-state", text: UI_COPY[1] }));
  } else {
    records.forEach((record) => list.append(captureCard(record, actions)));
  }
  return list;
}

async function renderToday() {
  const data = await api("/api/v1/dashboard/today");
  const page = section("Today overview");
  const summaries = element("div", { className: "summary-grid" });
  for (const [label, value] of [["Pending", data.pending_count], ["Failed", data.failed_count], ["Next actions", data.next_actions.length]]) {
    summaries.append(element("article", { className: "summary-card" }, [element("strong", { text: value }), element("span", { text: label })]));
  }
  page.append(summaries, element("h2", { text: "Recent captures" }), cards(data.recent_captures, [{ name: "open", label: "Open" }]));
  main.append(page);
}

function filterForm() {
  const form = element("form", { className: "filter-panel", attributes: { id: "inbox-filter" } });
  for (const [name, label, type] of [["query", "Title or source", "search"], ["project", "Project", "text"], ["created_from", "From date", "date"], ["created_to", "To date", "date"]]) {
    form.append(element("label", { className: "field" }, [element("span", { text: label }), element("input", { attributes: { name, type } })]));
  }
  form.append(element("button", { className: "button", text: "Search", attributes: { type: "submit" } }));
  return form;
}

async function renderInbox(filters = {}) {
  const data = await api(`/api/v1/captures${buildListQuery(filters)}`);
  state.records = data.data;
  const page = section("Inbox");
  page.append(filterForm(), cards(data.data, [
    { name: "open", label: "Open" },
    { name: "review", label: "Mark reviewed", secondary: true },
    { name: "assign", label: UI_COPY[5], secondary: true },
  ]));
  main.append(page);
}

async function renderProjects() {
  const data = await api("/api/v1/projects");
  const page = section("Projects");
  const list = element("div", { className: "card-list" });
  if (!data.data.length) list.append(element("div", { className: "empty-state", text: UI_COPY[1] }));
  for (const project of data.data) {
    list.append(element("article", { className: "capture-card" }, [
      element("h3", { text: project.project }),
      element("p", { text: project.latest_progress || "No progress recorded" }),
      element("p", { text: `Next: ${project.next_action || "Not recorded"}` }),
      element("p", { text: `Blocker: ${project.blocker || "None recorded"}` }),
    ]));
  }
  page.append(list); main.append(page);
}

async function renderPending() {
  const [pending, failed] = await Promise.all([
    api(`/api/v1/captures${buildListQuery({ status: "pending" })}`),
    api(`/api/v1/captures${buildListQuery({ status: "failed" })}`),
  ]);
  const page = section("Pending and failed");
  page.append(cards([...pending.data, ...failed.data], [
    { name: "retry", label: UI_COPY[2] },
    { name: "keep", label: UI_COPY[3], secondary: true },
    { name: "dismiss", label: UI_COPY[4], secondary: true },
  ]));
  main.append(page);
}

async function renderReports() {
  const data = await api(`/api/v1/captures${buildListQuery({ page_size: 50 })}`);
  const page = section("Reports");
  const form = element("form", { className: "report-panel", attributes: { id: "report-form" } });
  form.append(element("label", { className: "field" }, [element("span", { text: "Report type" }), element("select", { attributes: { name: "report_type" } }, [element("option", { text: "Daily", attributes: { value: "daily" } }), element("option", { text: "Period / project", attributes: { value: "period" } })])]));
  form.append(element("label", { className: "field" }, [element("span", { text: "Period" }), element("input", { attributes: { name: "period", required: "", maxlength: "100" } })]));
  const selections = element("div", { className: "selection-list" });
  data.data.forEach((record) => selections.append(element("label", { className: "selection-item" }, [element("input", { attributes: { type: "checkbox", name: "capture_id", value: record.capture_id } }), element("span", { text: record.title })])));
  form.append(selections, element("button", { className: "button", text: "Build report preview", attributes: { type: "submit" } }));
  page.append(form); main.append(page);
}

const loaders = { today: renderToday, inbox: renderInbox, projects: renderProjects, pending: renderPending, reports: renderReports };
async function loadPage() {
  state.page = pageFromHash(location.hash);
  title.textContent = state.page[0].toUpperCase() + state.page.slice(1);
  document.querySelectorAll("[data-route]").forEach((link) => link.setAttribute("aria-current", link.dataset.route === state.page ? "page" : "false"));
  showState("loading-state", UI_COPY[0], "Loading local operational data…");
  try { clearMain(); await loaders[state.page](); setStatus("Up to date"); }
  catch (error) { showState("error-state", "Could not load this page", userMessageForError(error.code)); setStatus("Action required"); }
}

async function openCapture(id) {
  const record = await api(`/api/v1/captures/${id}`);
  detailContent.textContent = record.markdown || record.raw_content || record.source || "No content available.";
  dialog.showModal();
}

main.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-action]");
  if (!button) return;
  const { action, id } = button.dataset;
  try {
    if (action === "open") await openCapture(id);
    if (action === "review") await api(`/api/v1/captures/${id}`, { method: "PATCH", body: JSON.stringify({ reviewed: true }) });
    if (action === "assign") {
      const record = state.records.find((item) => item.capture_id === id);
      const allowed = record?.allowed_projects || [];
      const project = window.prompt(`Choose one allowed project: ${allowed.join(", ")}`);
      if (project === null) return;
      if (!allowed.includes(project)) throw new Error("Project is outside this capture's allowlist.");
      await api(`/api/v1/captures/${id}`, { method: "PATCH", body: JSON.stringify({ assigned_project: project }) });
    }
    if (action === "retry") await api(`/api/v1/captures/${id}/retry`, { method: "POST" });
    if (action === "dismiss") await api(`/api/v1/captures/${id}/dismiss`, { method: "POST" });
    if (action === "keep") setStatus("Raw capture preserved. No data was deleted.");
    if (action !== "open" && action !== "keep") await loadPage();
  } catch (error) { setStatus(userMessageForError(error.code)); }
});

main.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.target;
  if (form.id === "inbox-filter") {
    const values = Object.fromEntries(new FormData(form).entries());
    clearMain(); await renderInbox(values); return;
  }
  if (form.id === "report-form") {
    const data = new FormData(form);
    try {
      const payload = reportPayload(data.get("report_type"), data.get("period"), data.getAll("capture_id"));
      const preview = await api("/api/v1/reports/preview", { method: "POST", body: JSON.stringify(payload) });
      detailContent.textContent = preview.markdown; dialog.showModal();
    } catch (error) { setStatus(error.message); }
  }
});

document.querySelector("#auth-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const input = document.querySelector("#api-token");
  state.token = input.value;
  input.value = "";
  setStatus("API token loaded for this session only.");
  loadPage();
});
document.querySelector("#close-dialog").addEventListener("click", () => dialog.close());
window.addEventListener("hashchange", loadPage);
if ("serviceWorker" in navigator) navigator.serviceWorker.register("/app/sw.js");
if (!location.hash) location.hash = "today"; else loadPage();
