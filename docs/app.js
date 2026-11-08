(() => {
  "use strict";

  const TABLE = (window.SUPABASE_CONFIG && window.SUPABASE_CONFIG.table) || "job_postings";
  const STATIC_FEED = "./data/jobs.json";
  const APPLIED_KEY = "qa-auto-apply-applied-ids";

  const state = {
    jobs: [],
    filter: "todo",
    search: "",
    collapsed: new Set(),
    client: null,
    pendingIds: new Set(),
    source: "static",
  };

  const els = {
    board: document.getElementById("job-board"),
    loading: document.getElementById("loading-state"),
    empty: document.getElementById("empty-state"),
    emptyCopy: document.getElementById("empty-copy"),
    error: document.getElementById("error-state"),
    setup: document.getElementById("setup-banner"),
    status: document.getElementById("status-pill"),
    refresh: document.getElementById("refresh-btn"),
    search: document.getElementById("search-input"),
    countTodo: document.getElementById("count-todo"),
    countApplied: document.getElementById("count-applied"),
    tabs: Array.from(document.querySelectorAll(".filter-tab")),
  };

  function setStatus(text, kind) {
    els.status.textContent = text;
    els.status.classList.remove("is-ready", "is-error");
    if (kind === "ready") els.status.classList.add("is-ready");
    if (kind === "error") els.status.classList.add("is-error");
  }

  function hideTransient() {
    els.loading.classList.add("hidden");
    els.error.classList.add("hidden");
  }

  function showError(message) {
    hideTransient();
    els.empty.classList.add("hidden");
    els.board.innerHTML = "";
    els.error.classList.remove("hidden");
    els.error.textContent = message;
    setStatus("Error", "error");
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function readAppliedMap() {
    try {
      return JSON.parse(localStorage.getItem(APPLIED_KEY) || "{}") || {};
    } catch {
      return {};
    }
  }

  function writeAppliedMap(map) {
    localStorage.setItem(APPLIED_KEY, JSON.stringify(map));
  }

  function normalizeJob(row) {
    const id = String(row.id || row.url || crypto.randomUUID());
    const appliedMap = readAppliedMap();
    const fromStorage = Object.prototype.hasOwnProperty.call(appliedMap, id)
      ? Boolean(appliedMap[id])
      : null;
    return {
      id,
      title: row.title || row["Role"] || "Untitled role",
      url: row.url || row["Application URL"] || "#",
      description:
        row.description ||
        [row["Company Name"], row["Location"]].filter(Boolean).join(" · ") ||
        "",
      date: row.date || row.created_at || null,
      is_applied: fromStorage === null ? Boolean(row.is_applied) : fromStorage,
    };
  }

  function isPlaceholder(job) {
    const url = String(job.url || "").toLowerCase();
    const title = String(job.title || "").toLowerCase();
    if (url.includes("example.com")) return true;
    if (title.startsWith("no live junior")) return true;
    return false;
  }

  function dateKey(value) {
    if (!value) return "unknown";
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return String(value).slice(0, 10);
    return d.toISOString().slice(0, 10);
  }

  function formatDateLabel(key) {
    if (key === "unknown") return "Unknown date";
    const d = new Date(`${key}T00:00:00`);
    if (Number.isNaN(d.getTime())) return key;
    return d.toLocaleDateString(undefined, {
      weekday: "short",
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  }

  function filteredJobs() {
    const wantApplied = state.filter === "applied";
    const needle = state.search.trim().toLowerCase();
    return state.jobs.filter((job) => {
      if (Boolean(job.is_applied) !== wantApplied) return false;
      if (!needle) return true;
      const hay = `${job.title} ${job.description}`.toLowerCase();
      return hay.includes(needle);
    });
  }

  function groupByDate(jobs) {
    const map = new Map();
    for (const job of jobs) {
      const key = dateKey(job.date);
      if (!map.has(key)) map.set(key, []);
      map.get(key).push(job);
    }
    return Array.from(map.entries()).sort((a, b) => {
      if (a[0] === "unknown") return 1;
      if (b[0] === "unknown") return -1;
      return b[0].localeCompare(a[0]);
    });
  }

  function updateCounts() {
    els.countTodo.textContent = String(state.jobs.filter((j) => !j.is_applied).length);
    els.countApplied.textContent = String(state.jobs.filter((j) => j.is_applied).length);
  }

  function renderJobCard(job) {
    const busy = state.pendingIds.has(job.id);
    const applied = job.is_applied;
    const toggleLabel = applied ? "Mark to apply" : "Mark applied";
    const desc = job.description
      ? `<p class="job-desc mt-2">${escapeHtml(job.description)}</p>`
      : "";
    const safeUrl = escapeHtml(job.url);

    return `
      <article class="job-card" data-id="${escapeHtml(job.id)}">
        <div>
          <h3 class="job-title">${escapeHtml(job.title)}</h3>
          ${desc}
          <div class="mt-3 flex flex-wrap items-center gap-3">
            <a class="job-link" href="${safeUrl}" target="_blank" rel="noopener noreferrer">
              Open posting
              <span aria-hidden="true">↗</span>
            </a>
            <span class="text-xs text-ink-500">${escapeHtml(dateKey(job.date))}</span>
          </div>
        </div>
        <button
          type="button"
          class="apply-toggle ${applied ? "is-applied" : ""}"
          data-toggle-id="${escapeHtml(job.id)}"
          ${busy ? "disabled" : ""}
          aria-pressed="${applied ? "true" : "false"}"
        >
          ${busy ? "Saving…" : toggleLabel}
        </button>
      </article>
    `;
  }

  function render() {
    hideTransient();
    updateCounts();

    const jobs = filteredJobs();
    if (!jobs.length) {
      els.board.innerHTML = "";
      els.empty.classList.remove("hidden");
      els.emptyCopy.textContent =
        state.filter === "applied"
          ? "No applied jobs yet. Toggle a card in To Apply to move it here."
          : "No openings in the latest published feed. After the daily Action runs, docs/data/jobs.json updates and this page refreshes.";
      return;
    }

    els.empty.classList.add("hidden");
    const groups = groupByDate(jobs);
    els.board.innerHTML = groups
      .map(([key, items]) => {
        const collapsed = state.collapsed.has(key);
        const cards = items.map(renderJobCard).join("");
        return `
          <section class="date-section ${collapsed ? "is-collapsed" : ""}" data-date="${escapeHtml(key)}">
            <button type="button" class="date-toggle" data-collapse="${escapeHtml(key)}" aria-expanded="${collapsed ? "false" : "true"}">
              <span>
                <span class="block font-display text-lg font-semibold text-ink-950">${escapeHtml(formatDateLabel(key))}</span>
                <span class="mt-0.5 block text-xs font-medium text-ink-500">${items.length} opening${items.length === 1 ? "" : "s"}</span>
              </span>
              <svg class="chevron" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                <path fill-rule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 10.94l3.71-3.71a.75.75 0 111.06 1.06l-4.24 4.24a.75.75 0 01-1.06 0L5.21 8.29a.75.75 0 01.02-1.08z" clip-rule="evenodd" />
              </svg>
            </button>
            <div class="date-body">${cards}</div>
          </section>
        `;
      })
      .join("");
  }

  async function fetchStaticJobs() {
    const response = await fetch(`${STATIC_FEED}?t=${Date.now()}`, { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`Could not load ${STATIC_FEED} (${response.status})`);
    }
    const payload = await response.json();
    const rows = Array.isArray(payload.jobs) ? payload.jobs : [];
    return rows.map(normalizeJob).filter((job) => !isPlaceholder(job) && job.url && job.url !== "#");
  }

  async function fetchSupabaseJobs() {
    if (!state.client) return null;
    const result = await Promise.race([
      state.client
        .from(TABLE)
        .select("id, title, url, description, date, is_applied")
        .order("date", { ascending: false }),
      new Promise((_, reject) => setTimeout(() => reject(new Error("Supabase timeout")), 8000)),
    ]);
    if (result.error) throw new Error(result.error.message);
    return (result.data || []).map(normalizeJob).filter((job) => !isPlaceholder(job));
  }

  async function fetchJobs() {
    els.loading.classList.remove("hidden");
    els.empty.classList.add("hidden");
    els.error.classList.add("hidden");
    setStatus("Loading…");

    let staticJobs = [];
    let staticError = null;
    try {
      staticJobs = await fetchStaticJobs();
    } catch (err) {
      staticError = err;
    }

    let remoteJobs = null;
    try {
      remoteJobs = await fetchSupabaseJobs();
    } catch {
      remoteJobs = null;
    }

    // Prefer non-empty Supabase data; otherwise use the published GitHub Pages feed.
    if (remoteJobs && remoteJobs.length) {
      state.jobs = remoteJobs;
      state.source = "supabase";
    } else if (staticJobs.length) {
      state.jobs = staticJobs;
      state.source = "static";
    } else if (staticError && !state.client) {
      showError(String(staticError.message || staticError));
      return;
    } else {
      state.jobs = [];
      state.source = staticError ? "error" : "empty";
    }

    setStatus(`${state.jobs.length} jobs`, "ready");
    render();
  }

  async function toggleApplied(id) {
    const job = state.jobs.find((item) => String(item.id) === String(id));
    if (!job || state.pendingIds.has(job.id)) return;

    const next = !job.is_applied;
    state.pendingIds.add(job.id);
    render();

    // Always persist locally so the UI works without Supabase secrets.
    const appliedMap = readAppliedMap();
    appliedMap[job.id] = next;
    writeAppliedMap(appliedMap);
    job.is_applied = next;

    if (state.client && state.source === "supabase") {
      try {
        const { error } = await state.client
          .from(TABLE)
          .update({ is_applied: next })
          .eq("id", job.id);
        if (error) throw error;
      } catch (err) {
        setStatus("Saved locally", "ready");
        state.pendingIds.delete(job.id);
        render();
        return;
      }
    }

    state.pendingIds.delete(job.id);
    setStatus("Saved", "ready");
    render();
  }

  function bindEvents() {
    els.tabs.forEach((tab) => {
      tab.addEventListener("click", () => {
        const filter = tab.dataset.filter;
        state.filter = filter;
        els.tabs.forEach((btn) => {
          const active = btn.dataset.filter === filter;
          btn.classList.toggle("is-active", active);
          btn.setAttribute("aria-selected", active ? "true" : "false");
        });
        render();
      });
    });

    els.search.addEventListener("input", (event) => {
      state.search = event.target.value || "";
      render();
    });

    els.refresh.addEventListener("click", () => {
      fetchJobs();
    });

    els.board.addEventListener("click", (event) => {
      const collapseBtn = event.target.closest("[data-collapse]");
      if (collapseBtn) {
        const key = collapseBtn.getAttribute("data-collapse");
        if (state.collapsed.has(key)) state.collapsed.delete(key);
        else state.collapsed.add(key);
        render();
        return;
      }

      const toggleBtn = event.target.closest("[data-toggle-id]");
      if (toggleBtn) {
        toggleApplied(toggleBtn.getAttribute("data-toggle-id"));
      }
    });
  }

  function createClient() {
    const cfg = { ...(window.SUPABASE_CONFIG || {}) };
    cfg.url = String(cfg.url || "")
      .trim()
      .replace(/^https\/\/:/i, "https://")
      .replace(/^http\/\/:/i, "http://");
    window.SUPABASE_CONFIG = cfg;

    if (!cfg.url || !cfg.anonKey) return null;
    try {
      const parsed = new URL(cfg.url);
      if (parsed.protocol !== "https:" || !parsed.hostname.endsWith(".supabase.co")) {
        return null;
      }
    } catch {
      return null;
    }
    if (!window.supabase || typeof window.supabase.createClient !== "function") {
      return null;
    }
    try {
      return window.supabase.createClient(cfg.url, cfg.anonKey);
    } catch {
      return null;
    }
  }

  function init() {
    bindEvents();
    state.client = createClient();
    fetchJobs();
  }

  init();
})();
