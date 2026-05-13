const AUTH_TOKEN_KEY = "hr_shortlist_auth_token";
const THEME_KEY = "hr_shortlist_theme";

const state = {
  authMode: "signin",
  page: "shortlist",
  shortlistMode: "existing",
  authToken: "",
  currentUser: null,
  jobs: [],
  historyRuns: [],
  vacancies: [],
};

const authScreenEl = document.getElementById("auth-screen");
const appShellEl = document.getElementById("app-shell");
const authStatusEl = document.getElementById("auth-status");
const appStatusEl = document.getElementById("app-status");

const authModeSignInBtn = document.getElementById("auth-mode-signin");
const authModeSignUpBtn = document.getElementById("auth-mode-signup");
const signinForm = document.getElementById("signin-form");
const signupForm = document.getElementById("signup-form");

const signoutBtn = document.getElementById("signout-btn");
const topbarUserNameEl = document.getElementById("topbar-user-name");

const pageButtons = {
  shortlist: document.getElementById("page-shortlist-btn"),
  profile: document.getElementById("page-profile-btn"),
  insights: document.getElementById("page-insights-btn"),
};

const pageSections = {
  shortlist: document.getElementById("page-shortlist"),
  profile: document.getElementById("page-profile"),
  insights: document.getElementById("page-insights"),
};

const modeExistingBtn = document.getElementById("mode-existing");
const modeCustomBtn = document.getElementById("mode-custom");
const existingForm = document.getElementById("existing-form");
const customForm = document.getElementById("custom-form");
const jobSearchInput = document.getElementById("job-search");
const jobOptionsEl = document.getElementById("job-options");

const vacancyTitleInput = document.getElementById("vacancy-title");
const vacancyDescriptionInput = document.getElementById("vacancy-description");
const vacancyYearsInput = document.getElementById("vacancy-years");
const vacancySkillsInput = document.getElementById("vacancy-skills");

const resultsMetaEl = document.getElementById("results-meta");
const resultsEl = document.getElementById("results");
const candidateTemplate = document.getElementById("candidate-template");

const profileUserNameEl = document.getElementById("profile-user-name");
const profileUserEmailEl = document.getElementById("profile-user-email");
const profileUserRoleEl = document.getElementById("profile-user-role");
const vacancyListEl = document.getElementById("vacancy-list");
const historyListEl = document.getElementById("history-list");
const vacanciesRefreshBtn = document.getElementById("vacancies-refresh");
const historyRefreshBtn = document.getElementById("history-refresh");

const globalExplainerMetaEl = document.getElementById("global-explainer-meta");
const globalShapListEl = document.getElementById("global-shap-list");
const featureGlossaryListEl = document.getElementById("feature-glossary-list");

const resumeModalEl = document.getElementById("resume-modal");
const resumeModalTextEl = document.getElementById("resume-modal-text");
const resumeModalTitleEl = document.getElementById("resume-modal-title");
const resumeModalCloseEl = document.getElementById("resume-modal-close");
const resumeModalBackdropEl = document.getElementById("resume-modal-backdrop");

const themeLightBtn = document.getElementById("theme-light-btn");
const themeDarkBtn = document.getElementById("theme-dark-btn");

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function fmt(value, digits = 3) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
  return Number(value).toFixed(digits);
}

function numOr(value, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function humanDate(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString();
}

function setTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  themeLightBtn.classList.toggle("is-active", theme === "light");
  themeDarkBtn.classList.toggle("is-active", theme === "dark");
  localStorage.setItem(THEME_KEY, theme);
}

function setAuthStatus(text, type = "") {
  authStatusEl.textContent = text || "";
  authStatusEl.className = `mini-muted auth-note ${type}`.trim();
}

function setAppStatus(text, type = "") {
  appStatusEl.textContent = text || "";
  appStatusEl.className = `app-msg ${type}`.trim();
}

function setAuthMode(mode) {
  state.authMode = mode;
  const isSignIn = mode === "signin";
  authModeSignInBtn.classList.toggle("is-active", isSignIn);
  authModeSignUpBtn.classList.toggle("is-active", !isSignIn);
  signinForm.classList.toggle("hidden", !isSignIn);
  signupForm.classList.toggle("hidden", isSignIn);
}

function setPage(pageKey) {
  state.page = pageKey;
  Object.entries(pageButtons).forEach(([key, button]) => {
    const isActive = key === pageKey;
    button.classList.toggle("is-active", isActive);
    const glyph = button.querySelector(".nav-glyph");
    if (glyph) glyph.textContent = isActive ? "[x]" : "[+]";
  });
  Object.entries(pageSections).forEach(([key, section]) => {
    section.classList.toggle("is-active", key === pageKey);
  });
}

function setShortlistMode(mode) {
  state.shortlistMode = mode;
  const isExisting = mode === "existing";
  modeExistingBtn.classList.toggle("is-active", isExisting);
  modeCustomBtn.classList.toggle("is-active", !isExisting);
  existingForm.classList.toggle("hidden", !isExisting);
  customForm.classList.toggle("hidden", isExisting);
}

function getAuthHeaders() {
  if (!state.authToken) return {};
  return { Authorization: `Bearer ${state.authToken}` };
}

function applyUserToUi() {
  const user = state.currentUser || {};
  topbarUserNameEl.textContent = user.full_name || user.email || "—";
  profileUserNameEl.textContent = user.full_name || "—";
  profileUserEmailEl.textContent = user.email || "—";
  profileUserRoleEl.textContent = user.role || "hr";
}

function applyAuthGate() {
  const isAuthenticated = Boolean(state.authToken && state.currentUser);
  authScreenEl.classList.toggle("hidden", isAuthenticated);
  appShellEl.classList.toggle("hidden", !isAuthenticated);

  if (isAuthenticated) {
    applyUserToUi();
    setAppStatus("Welcome! Start by creating a shortlist.", "ok");
  } else {
    setAuthStatus("Use your HR credentials to continue.", "");
    setAppStatus("");
  }
}

function clearSession() {
  state.authToken = "";
  state.currentUser = null;
  state.jobs = [];
  state.historyRuns = [];
  state.vacancies = [];
  localStorage.removeItem(AUTH_TOKEN_KEY);
  applyAuthGate();
}

function setSessionFromAuthResponse(payload) {
  state.authToken = String(payload.access_token || "").trim();
  state.currentUser = payload.user || null;
  if (state.authToken) {
    localStorage.setItem(AUTH_TOKEN_KEY, state.authToken);
  }
  applyAuthGate();
}

async function apiRequest(path, options = {}, { authRequired = false } = {}) {
  const headers = {
    ...(options.headers || {}),
    ...getAuthHeaders(),
  };

  const response = await fetch(path, { ...options, headers });
  const data = await response.json().catch(() => ({}));

  if (response.status === 401) {
    clearSession();
    if (authRequired) {
      throw new Error(data.detail || "Authentication required. Please sign in.");
    }
  }

  if (!response.ok) {
    throw new Error(data.detail || `Request failed (${response.status})`);
  }

  return data;
}

async function apiGet(path, options = {}) {
  return apiRequest(path, { method: "GET" }, options);
}

async function apiPost(path, payload, options = {}) {
  return apiRequest(
    path,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
    options
  );
}

function openResumeModal(resumeId, resumeText) {
  resumeModalTitleEl.textContent = `Resume ${resumeId}`;
  resumeModalTextEl.textContent = resumeText && resumeText.trim() ? resumeText : "Resume text is not available.";
  resumeModalEl.classList.remove("hidden");
}

function closeResumeModal() {
  resumeModalEl.classList.add("hidden");
}

function updateResultsMeta(payload, extra = "") {
  const vacancy = payload.job_title || payload.vacancy_title || payload.job_id || "custom vacancy";
  const shown = payload.total_candidates ?? payload.returned_count ?? "-";
  const evaluated = payload.retrieved_count ?? payload.num_candidates ?? "-";
  const parts = [
    `top ${shown} of ${evaluated} evaluated`,
    `vacancy: ${vacancy}`,
    extra,
  ].filter(Boolean);
  resultsMetaEl.textContent = parts.join(" · ");
}

function buildCandidateSummary(candidate) {
  const explanation = candidate.explanation || {};
  const matched = explanation.matched_skills || [];
  const missing = explanation.missing_skills || [];

  if (matched.length && missing.length) {
    return `Matched: ${matched.slice(0, 4).join(", ")}. Missing: ${missing.slice(0, 3).join(", ")}.`;
  }
  if (matched.length) {
    return `Strong skill alignment on: ${matched.slice(0, 5).join(", ")}.`;
  }
  if (explanation.experience_summary) {
    return explanation.experience_summary;
  }
  return "Review details and resume text for final HR decision.";
}

function renderCandidateDetails(candidate) {
  const explanation = candidate.explanation || {};
  const matched = (explanation.matched_skills || []).slice(0, 5);
  const missing = (explanation.missing_skills || []).slice(0, 4);
  const positives = (explanation.top_positive_factors || []).slice(0, 3).map((item) => item.label).filter(Boolean);

  const rows = [
    ["matched skills", matched.join(", ") || "not enough data"],
    ["missing skills", missing.join(", ") || "none highlighted"],
    ["experience fit", explanation.experience_summary || "review resume for full context"],
    ["why recommended", positives.join(", ") || "strong overall relevance"],
  ];

  return rows
    .map(
      ([key, val]) => `
      <div class="kv-row">
        <span class="kv-key">${escapeHtml(key)}</span>
        <span class="kv-val">${escapeHtml(val)}</span>
      </div>`
    )
    .join("");
}

function scoreToPercent(value) {
  const v = numOr(value, 0);
  return Math.max(0, Math.min(100, Math.round(v * 100)));
}

function matchTier(pct) {
  if (pct >= 75) return "strong";
  if (pct >= 50) return "good";
  return "weak";
}

function makeAsciiBar(pct, width = 16) {
  const filled = Math.round((pct / 100) * width);
  return "█".repeat(filled) + "─".repeat(width - filled);
}

function makeResumeSnippet(text, maxLen = 260) {
  const clean = String(text || "").replace(/\s+/g, " ").trim();
  if (!clean) return 'Resume text is not available — click "view resume" for the source record.';
  if (clean.length <= maxLen) return clean;
  return clean.slice(0, maxLen).trimEnd() + "…";
}

function renderCandidates(payload) {
  const candidates = payload.candidates || [];
  resultsEl.innerHTML = "";

  if (!candidates.length) {
    resultsEl.innerHTML =
      '<p class="mono-mute results-hint">No candidates matched this vacancy. Try a broader description or increase the candidate pool.</p>';
    return;
  }

  const fragment = document.createDocumentFragment();

  candidates.forEach((candidate) => {
    const node = candidateTemplate.content.cloneNode(true);
    const fusedScore = candidate.final_fusion_score ?? candidate.score;
    const pct = scoreToPercent(fusedScore);
    const tier = matchTier(pct);

    node.querySelector(".rank-pill").textContent = `#${candidate.final_rank}`;
    node.querySelector(".resume-id").textContent = `Candidate ${candidate.resume_id}`;

    const scoreEl = node.querySelector(".score-fused");
    scoreEl.textContent = `${pct}%`;
    if (tier === "strong") scoreEl.classList.add("badge-success");
    else if (tier === "good") scoreEl.classList.add("badge-warning");
    else scoreEl.classList.add("badge-danger");

    node.querySelector(".score-bar-ascii").textContent = makeAsciiBar(pct);

    node.querySelector(".candidate-summary").textContent = buildCandidateSummary(candidate);
    node.querySelector(".resume-snippet-box").textContent = makeResumeSnippet(candidate.resume_text);

    const detailsEl = node.querySelector(".details-grid");
    detailsEl.innerHTML = renderCandidateDetails(candidate);

    const resumeBtn = node.querySelector(".view-resume-btn");
    resumeBtn.addEventListener("click", () => {
      openResumeModal(candidate.resume_id, candidate.resume_text || "");
    });

    fragment.appendChild(node);
  });

  resultsEl.appendChild(fragment);
}

function mapHistoryDetailToCandidates(detail) {
  return (detail.candidates || []).map((candidate) => {
    const feature = candidate.feature_snapshot || {};
    return {
      final_rank: candidate.final_rank,
      resume_id: candidate.resume_id,
      resume_text: "",
      final_fusion_score: candidate.final_fusion_score ?? 0,
      retrieval_rank: candidate.retrieval_rank ?? 0,
      retrieval_score_norm: numOr(feature.retrieval_score_norm, 0),
      reranker_score_norm: numOr(feature.reranker_score_norm, 0),
      skill_overlap_count: numOr(feature.skill_overlap_count, 0),
      skill_overlap_ratio: numOr(feature.skill_overlap_ratio, 0),
      title_overlap_ratio: numOr(feature.title_overlap_ratio, 0),
      years_gap: numOr(feature.years_gap, 0),
      explanation: candidate.explanation || {},
    };
  });
}

async function loadHistoryRun(runId) {
  try {
    setAppStatus("Loading shortlist from history...", "ok");
    const detail = await apiGet(`/cabinet/history/${encodeURIComponent(runId)}`, { authRequired: true });
    const mapped = {
      job_id: detail.existing_job_id || detail.vacancy_title || "custom",
      top_k: detail.top_k,
      retrieved_count: detail.retrieved_count,
      total_candidates: detail.returned_count,
      candidates: mapHistoryDetailToCandidates(detail),
    };

    updateResultsMeta(mapped, "loaded from history");
    renderCandidates(mapped);
    setPage("shortlist");
    setAppStatus("History shortlist loaded.", "ok");
  } catch (error) {
    setAppStatus(error.message || "Failed to load history run.", "error");
  }
}

function renderHistoryList(runs) {
  historyListEl.innerHTML = "";

  if (!runs || !runs.length) {
    historyListEl.innerHTML = "<p class='mono-mute panel-empty'>No shortlist history yet.</p>";
    return;
  }

  const fragment = document.createDocumentFragment();
  runs.forEach((run) => {
    const item = document.createElement("div");
    item.className = "pipeline-row";

    const label = run.vacancy_title || (run.existing_job_id ? `${run.existing_job_id}` : "Custom vacancy");
    item.innerHTML = `
      <div>
        <div class="pipeline-name">${escapeHtml(label)}</div>
        <div class="pipeline-sub">${escapeHtml(humanDate(run.created_at))} · ${escapeHtml(String(run.returned_count))} candidates</div>
      </div>
      <button type="button" class="btn btn-ghost btn-sm open-history-btn">open</button>
    `;

    const button = item.querySelector(".open-history-btn");
    button.addEventListener("click", () => loadHistoryRun(run.run_id));
    fragment.appendChild(item);
  });

  historyListEl.appendChild(fragment);
}

function renderVacancyList(vacancies) {
  vacancyListEl.innerHTML = "";

  if (!vacancies || !vacancies.length) {
    vacancyListEl.innerHTML = "<p class='mono-mute panel-empty'>No custom vacancies yet.</p>";
    return;
  }

  const fragment = document.createDocumentFragment();
  vacancies.forEach((vacancy) => {
    const item = document.createElement("div");
    item.className = "pipeline-row";
    item.innerHTML = `
      <div>
        <div class="pipeline-name">${escapeHtml(vacancy.title || "Untitled vacancy")}</div>
        <div class="pipeline-sub">${escapeHtml(humanDate(vacancy.created_at))} · <span class="badge">${escapeHtml(vacancy.source || "manual")}</span></div>
      </div>
    `;
    fragment.appendChild(item);
  });

  vacancyListEl.appendChild(fragment);
}

function renderGlobalExplanation(payload) {
  const features = payload.top_features || [];
  const rows = features
    .slice(0, 12)
    .map((feature, index) => {
      const ratio = Math.max(0, Math.min(1, numOr(feature.mean_abs_shap, 0)));
      const filled = Math.round(ratio * 36);
      const bar = "█".repeat(filled) + "─".repeat(36 - filled);
      return `
        <div class="shap-item">
          <span class="shap-rank">#${index + 1}</span>
          <div class="shap-content">
            <div class="shap-feature-name">${escapeHtml(feature.label)}</div>
            <div class="shap-ascii-bar">${escapeHtml(bar)}</div>
            <div class="shap-meta">mean |SHAP| = ${fmt(feature.mean_abs_shap, 5)} · mean SHAP = ${fmt(feature.mean_shap, 5)}</div>
          </div>
        </div>
      `;
    })
    .join("");

  globalShapListEl.innerHTML = rows || "<p class='mono-mute'>No SHAP summary available yet.</p>";
  globalExplainerMetaEl.textContent = `based on ${payload.validation_rows ?? 0} validation rows`;

  const glossary = (payload.feature_glossary || [])
    .map(
      (item) => `
      <div class="pipeline-row">
        <div>
          <div class="pipeline-name">${escapeHtml(item.label)}</div>
          <div class="pipeline-sub">${escapeHtml(item.description)}</div>
        </div>
        <span class="badge ${item.used_in_model ? "badge-success" : ""}">${item.used_in_model ? "used" : "unused"}</span>
      </div>`
    )
    .join("");

  featureGlossaryListEl.innerHTML = glossary || "<p class='mono-mute panel-empty'>No glossary available.</p>";
}

async function loadJobs() {
  const data = await apiGet("/jobs", { authRequired: true });
  state.jobs = data.jobs || [];
  jobOptionsEl.innerHTML = "";

  state.jobs.forEach((job) => {
    const option = document.createElement("option");
    option.value = `${job.job_title} — ${job.job_id}`;
    jobOptionsEl.appendChild(option);
  });
}

function resolveSelectedJobId() {
  const raw = (jobSearchInput.value || "").trim();
  if (!raw) return "";
  const dashSplit = raw.split("—").map((s) => s.trim());
  const tail = dashSplit[dashSplit.length - 1];
  if (state.jobs.some((j) => j.job_id === tail)) return tail;
  const byTitle = state.jobs.find((j) => j.job_title.toLowerCase() === raw.toLowerCase());
  return byTitle ? byTitle.job_id : "";
}

async function loadVacancies() {
  const data = await apiGet("/cabinet/vacancies?limit=200", { authRequired: true });
  state.vacancies = data.vacancies || [];
  renderVacancyList(state.vacancies);
}

async function loadHistory() {
  const data = await apiGet("/cabinet/history?limit=100", { authRequired: true });
  state.historyRuns = data.runs || [];
  renderHistoryList(state.historyRuns);
}

async function loadGlobalExplanation() {
  globalExplainerMetaEl.textContent = "loading SHAP summary...";
  globalShapListEl.innerHTML = "<p class='mono-mute'>Loading...</p>";
  featureGlossaryListEl.innerHTML = "";

  try {
    const data = await apiGet("/stats/explanations/global", { authRequired: true });
    renderGlobalExplanation(data);
  } catch (error) {
    globalExplainerMetaEl.textContent = "SHAP summary unavailable";
    globalShapListEl.innerHTML = "<p class='mono-mute'>SHAP artifacts are not available yet.</p>";
    featureGlossaryListEl.innerHTML = "";
  }
}

async function refreshMe() {
  if (!state.authToken) return;
  try {
    const me = await apiGet("/auth/me", { authRequired: true });
    state.currentUser = me;
  } catch (_) {
    clearSession();
  }
}

async function loadAppData() {
  try {
    setAppStatus("Loading workspace data...", "ok");
    await Promise.all([loadJobs(), loadGlobalExplanation(), loadVacancies(), loadHistory()]);
    setAppStatus("Workspace ready.", "ok");
  } catch (error) {
    setAppStatus(error.message || "Failed to load workspace data.", "error");
  }
}

existingForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const jobId = resolveSelectedJobId();
  if (!jobId) {
    setAppStatus("Please pick a vacancy from the suggestions list first.", "error");
    return;
  }
  try {
    setAppStatus("Searching candidates and re-ranking with the ML model…", "ok");
    const payload = {
      job_id: jobId,
      top_k: Number(document.getElementById("existing-topk").value || 20),
      num_candidates: Number(document.getElementById("existing-num-candidates").value || 100),
    };

    const data = await apiPost("/shortlist", payload, { authRequired: true });
    updateResultsMeta(data);
    renderCandidates(data);
    await Promise.all([loadHistory(), loadVacancies()]);
    setAppStatus("Shortlist ready. Open candidate cards for details.", "ok");
  } catch (error) {
    setAppStatus(error.message || "Failed to build shortlist.", "error");
  }
});

customForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    setAppStatus("Searching candidates and re-ranking with the ML model…", "ok");

    const rawSkills = vacancySkillsInput.value || "";
    const parsedSkills = rawSkills
      .split(",")
      .map((item) => item.trim().toLowerCase())
      .filter(Boolean);

    const yearsRaw = vacancyYearsInput.value;
    const payload = {
      vacancy_title: vacancyTitleInput.value.trim(),
      vacancy_description: vacancyDescriptionInput.value.trim(),
      top_k: Number(document.getElementById("custom-topk").value || 20),
      num_candidates: Number(document.getElementById("custom-num-candidates").value || 100),
      job_skills_norm: parsedSkills.length ? parsedSkills : null,
      job_years_required: yearsRaw ? Number(yearsRaw) : null,
    };

    const data = await apiPost("/shortlist/vacancy", payload, { authRequired: true });
    const extra = data.proxy_job_id ? `proxy: ${data.proxy_job_id}` : "";
    updateResultsMeta(data, extra);
    renderCandidates(data);
    await Promise.all([loadHistory(), loadVacancies()]);
    setAppStatus("Custom vacancy shortlist generated and saved.", "ok");
  } catch (error) {
    setAppStatus(error.message || "Failed to build shortlist.", "error");
  }
});

signinForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    setAuthStatus("Signing in…", "ok");
    const payload = {
      email: document.getElementById("signin-email").value.trim(),
      password: document.getElementById("signin-password").value,
    };
    const data = await apiPost("/auth/signin", payload);
    setSessionFromAuthResponse(data);
    await loadAppData();
    setPage("shortlist");
  } catch (error) {
    setAuthStatus(error.message || "Sign in failed.", "error");
  }
});

signupForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    setAuthStatus("Creating account…", "ok");
    const payload = {
      full_name: document.getElementById("signup-fullname").value.trim(),
      email: document.getElementById("signup-email").value.trim(),
      password: document.getElementById("signup-password").value,
    };
    const data = await apiPost("/auth/signup", payload);
    setSessionFromAuthResponse(data);
    await loadAppData();
    setPage("shortlist");
  } catch (error) {
    setAuthStatus(error.message || "Sign up failed.", "error");
  }
});

signoutBtn.addEventListener("click", async () => {
  try {
    if (state.authToken) {
      await apiPost("/auth/signout", {}, { authRequired: true });
    }
  } catch (_) {
    // local signout continues regardless
  } finally {
    clearSession();
    setAuthMode("signin");
  }
});

historyRefreshBtn.addEventListener("click", async () => {
  try {
    setAppStatus("Refreshing shortlist history…", "ok");
    await loadHistory();
    setAppStatus("Shortlist history updated.", "ok");
  } catch (error) {
    setAppStatus(error.message || "Failed to refresh history.", "error");
  }
});

vacanciesRefreshBtn.addEventListener("click", async () => {
  try {
    setAppStatus("Refreshing vacancy list…", "ok");
    await loadVacancies();
    setAppStatus("Vacancy list updated.", "ok");
  } catch (error) {
    setAppStatus(error.message || "Failed to refresh vacancies.", "error");
  }
});

pageButtons.shortlist.addEventListener("click", () => setPage("shortlist"));
pageButtons.profile.addEventListener("click", () => setPage("profile"));
pageButtons.insights.addEventListener("click", () => setPage("insights"));

modeExistingBtn.addEventListener("click", () => setShortlistMode("existing"));
modeCustomBtn.addEventListener("click", () => setShortlistMode("custom"));

authModeSignInBtn.addEventListener("click", () => setAuthMode("signin"));
authModeSignUpBtn.addEventListener("click", () => setAuthMode("signup"));

themeLightBtn.addEventListener("click", () => setTheme("light"));
themeDarkBtn.addEventListener("click", () => setTheme("dark"));

resumeModalCloseEl.addEventListener("click", closeResumeModal);
resumeModalBackdropEl.addEventListener("click", closeResumeModal);
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") closeResumeModal();
});

async function boot() {
  const savedTheme = localStorage.getItem(THEME_KEY) || "dark";
  setTheme(savedTheme);

  setAuthMode("signin");
  setPage("shortlist");
  setShortlistMode("existing");

  const savedToken = localStorage.getItem(AUTH_TOKEN_KEY);
  if (savedToken) {
    state.authToken = savedToken;
    await refreshMe();
  }

  applyAuthGate();

  if (state.authToken && state.currentUser) {
    await loadAppData();
  }
}

boot();
