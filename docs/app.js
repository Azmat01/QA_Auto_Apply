(() => {
  "use strict";

  const TABLE = (window.SUPABASE_CONFIG && window.SUPABASE_CONFIG.table) || "job_postings";

  const state = {
    jobs: [],
    filter: "todo",
    search: "",
    collapsed: new Set(),
    client: null,
    pendingIds: new Set(),
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

  function showSetupBanner(message) {
    els.setup.classList.remove("hidden");
    els.setup.innerHTML = message;
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

  function normalizeJob(row) {
    return {
      id: row.id,
      title: row.title || "Untitled role",
      url: row.url || "#",
      description: row.description || "",
      date: row.date || row.created_at || null,
      is_applied: Boolean(row.is_applied),
    };
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
    const todo = state.jobs.filter((j) => !j.is_applied).length;
    const applied = state.jobs.filter((j) => j.is_applied).length;
    els.countTodo.textContent = String(todo);
    els.countApplied.textContent = String(applied);
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
          : "No junior QA / Manual Tester openings with real apply links right now. The daily script will add Greenhouse/Lever URLs when matches are found.";
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

  async function fetchJobs() {
    if (!state.client) return;
    els.loading.classList.remove("hidden");
    els.empty.classList.add("hidden");
    els.error.classList.add("hidden");
    setStatus("Loading…");

    const { data, error } = await state.client
      .from(TABLE)
      .select("id, title, url, description, date, is_applied")
      .order("date", { ascending: false });

    if (error) {
      showError(`Could not load jobs: ${error.message}`);
      return;
    }

    state.jobs = (data || [])
      .map(normalizeJob)
      .filter((job) => {
        const url = String(job.url || "").toLowerCase();
        const title = String(job.title || "").toLowerCase();
        if (url.includes("example.com")) return false;
        if (title.startsWith("no live junior")) return false;
        return true;
      });
    setStatus(`${state.jobs.length} jobs`, "ready");
    render();
  }

  async function toggleApplied(id) {
    const job = state.jobs.find((item) => String(item.id) === String(id));
    if (!job || !state.client || state.pendingIds.has(job.id)) return;

    const next = !job.is_applied;
    state.pendingIds.add(job.id);
    render();

    const { data, error } = await state.client
      .from(TABLE)
      .update({ is_applied: next })
      .eq("id", job.id)
      .select("id, title, url, description, date, is_applied")
      .single();

    state.pendingIds.delete(job.id);

    if (error) {
      setStatus("Update failed", "error");
      render();
      showError(`Could not update applied status: ${error.message}`);
      return;
    }

    const updated = normalizeJob(data);
    state.jobs = state.jobs.map((item) =>
      String(item.id) === String(updated.id) ? updated : item
    );
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

  function normalizeSupabaseUrl(url) {
    let value = String(url || "").trim();
    // Common typo that broke the live dashboard: https//:host → https://host
    value = value.replace(/^https\/\/:/i, "https://").replace(/^http\/\/:/i, "http://");
    return value;
  }

  function isValidSupabaseUrl(url) {
    try {
      const parsed = new URL(url);
      return parsed.protocol === "https:" && parsed.hostname.endsWith(".supabase.co");
    } catch {
      return false;
    }
  }

  function createClient() {
    const cfg = { ...(window.SUPABASE_CONFIG || {}) };
    cfg.url = normalizeSupabaseUrl(cfg.url);
    window.SUPABASE_CONFIG = cfg;
    if (!cfg.url || !cfg.anonKey) {
      showSetupBanner(
        `<strong>Connect Supabase.</strong> Set <code>url</code> and <code>anonKey</code> in
        <code>docs/config.js</code> (see <code>config.example.js</code>), then run
        <code>supabase/schema.sql</code> in the Supabase SQL editor.`
      );
      hideTransient();
      els.empty.classList.remove("hidden");
      els.emptyCopy.textContent = "Add your Supabase project credentials to load postings.";
      setStatus("Setup needed", "error");
      return null;
    }

    if (!isValidSupabaseUrl(cfg.url)) {
      showError(
        `Invalid Supabase URL in config.js: "${cfg.url}". Expected https://YOUR_PROJECT.supabase.co`
      );
      return null;
    }

    if (!window.supabase || typeof window.supabase.createClient !== "function") {
      showError("Supabase JS SDK failed to load. Check your network or CDN.");
      return null;
    }

    try {
      return window.supabase.createClient(cfg.url, cfg.anonKey);
    } catch (err) {
      showError(`Could not create Supabase client: ${err?.message || err}`);
      return null;
    }
  }

  function init() {
    try {
      bindEvents();
      state.client = createClient();
      if (!state.client) return;
      setStatus("Connected", "ready");
      fetchJobs();
    } catch (err) {
      showError(`Dashboard failed to start: ${err?.message || err}`);
    }
  }

  init();
})();
