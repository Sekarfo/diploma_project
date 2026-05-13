import type { AnalyticsSummary, DashboardSummary, ProcessingJob, ShortlistCandidate, Vacancy } from "../types";
import { apiFetch } from "./httpClient";

// ─── Backend response types ───────────────────────────────────────────────────

interface BackendAuth {
  access_token: string;
  token_type: string;
  expires_at: string;
  user: { id: string; email: string; full_name: string; role: string; is_active: boolean };
}

interface BackendShapFactor {
  feature: string;
  label: string;
  impact: number;
  raw_value: string;
  description: string;
}

interface BackendExplanation {
  matched_skills: string[];
  missing_skills: string[];
  experience_summary: string;
  title_summary: string;
  top_positive_factors: BackendShapFactor[];
  top_negative_factors: BackendShapFactor[];
}

interface BackendFreshCandidate {
  final_rank: number;
  resume_id: string;
  resume_text: string;
  model_score: number;
  score: number;
  skill_overlap_ratio: number;
  resume_years_experience: number;
  job_years_required: number;
  years_gap: number;
  explanation: BackendExplanation;
}

interface BackendShortlistResponse {
  job_id: string;
  job_title: string;
  total_candidates: number;
  retrieved_count: number;
  top_k: number;
  candidates: BackendFreshCandidate[];
  proxy_job_id?: string;
}

interface BackendHistoryRun {
  run_id: string;
  created_at: string;
  status: string;
  returned_count: number;
  retrieved_count: number;
  vacancy_title: string;
  vacancy_description_preview: string;
  error_message: string | null;
}

interface BackendHistoryCandidate {
  final_rank: number;
  resume_id: string;
  final_fusion_score: number;
  model_score: number;
  retrieval_rank: number;
  feature_snapshot: Record<string, number>;
  explanation: BackendExplanation | null;
}

interface BackendHistoryDetail {
  run_id: string;
  created_at: string;
  status: string;
  vacancy_title: string;
  vacancy_description: string;
  returned_count: number;
  retrieved_count: number;
  candidates: BackendHistoryCandidate[];
}

interface BackendStats {
  total_jobs: number;
  total_resumes: number;
}

interface BackendRuntimeStats {
  uptime_seconds: number;
  total_requests: number;
  total_errors: number;
  error_rate: number;
  latency_ms_p50: number | null;
  latency_ms_p95: number | null;
}

interface BackendGlobalExplanation {
  top_features: Array<{ feature: string; label: string; mean_abs_shap: number; mean_shap: number }>;
}

// ─── Adapters ─────────────────────────────────────────────────────────────────

function makeVacancy(id: string, title: string): Vacancy {
  return {
    id,
    title,
    description: "",
    extractedSkills: [],
    weights: { skills: 0.65, experience: 0.35 },
    status: "READY",
    candidatesFound: 0,
    createdAt: new Date().toISOString(),
  };
}

function adaptFreshCandidate(c: BackendFreshCandidate, jobId: string, jobTitle: string): ShortlistCandidate {
  const matchScore = Math.round(c.score * 100 * 10) / 10;
  const skillsMatch = Math.round((c.skill_overlap_ratio ?? 0) * 100 * 10) / 10;
  const yearsGap = Math.abs(c.years_gap ?? 0);
  const jobYrs = Math.max(c.job_years_required ?? 1, 1);
  const expScore = Math.max(0, Math.min(100, Math.round((1 - yearsGap / jobYrs) * 100)));
  const exp = c.explanation;

  return {
    vacancyId: jobId,
    candidateId: c.resume_id,
    matchScore,
    skillsMatch,
    experienceScore: expScore,
    topMatchingSkills: (exp?.matched_skills ?? []).slice(0, 3),
    explanation: exp?.experience_summary || exp?.title_summary || "",
    explanationFactors: (exp?.top_positive_factors ?? []).slice(0, 5).map((f) => ({
      factor: f.label,
      impact: f.impact,
    })),
    decision: "pending",
    candidate: {
      id: c.resume_id,
      fullName: c.resume_id,
      headline: exp?.title_summary || `${Math.round(c.resume_years_experience ?? 0)}y experience`,
      location: "",
      experienceYears: Math.round(c.resume_years_experience ?? 0),
      skills: [...(exp?.matched_skills ?? []), ...(exp?.missing_skills ?? [])].slice(0, 8),
      resumePreview: c.resume_text?.slice(0, 400) ?? "",
    },
    vacancy: makeVacancy(jobId, jobTitle),
  };
}

function adaptHistoryCandidate(
  c: BackendHistoryCandidate,
  runId: string,
  vacancyTitle: string
): ShortlistCandidate {
  const exp = c.explanation;
  const fs = c.feature_snapshot ?? {};
  const matchScore = Math.round((c.final_fusion_score ?? c.model_score) * 100 * 10) / 10;
  const skillsMatch = Math.round((fs.skill_overlap_ratio ?? 0) * 100 * 10) / 10;
  const yearsGap = Math.abs(fs.years_gap ?? 0);
  const jobYrs = Math.max(fs.job_years_required ?? 1, 1);
  const expScore = Math.max(0, Math.min(100, Math.round((1 - yearsGap / jobYrs) * 100)));

  return {
    vacancyId: runId,
    candidateId: c.resume_id,
    matchScore,
    skillsMatch,
    experienceScore: expScore,
    topMatchingSkills: (exp?.matched_skills ?? []).slice(0, 3),
    explanation: exp?.experience_summary || exp?.title_summary || "",
    explanationFactors: (exp?.top_positive_factors ?? []).slice(0, 5).map((f) => ({
      factor: f.label,
      impact: f.impact,
    })),
    decision: "pending",
    candidate: {
      id: c.resume_id,
      fullName: c.resume_id,
      headline: exp?.title_summary || `Rank #${c.final_rank}`,
      location: "",
      experienceYears: Math.round(fs.resume_years_experience ?? 0),
      skills: [...(exp?.matched_skills ?? []), ...(exp?.missing_skills ?? [])].slice(0, 8),
      resumePreview: exp?.experience_summary ?? "",
    },
    vacancy: makeVacancy(runId, vacancyTitle),
  };
}

// ─── Auth ─────────────────────────────────────────────────────────────────────

export async function loginUser(email: string, password: string): Promise<BackendAuth> {
  return apiFetch<BackendAuth>("/auth/signin", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function signupUser(
  email: string,
  password: string,
  full_name: string
): Promise<BackendAuth> {
  return apiFetch<BackendAuth>("/auth/signup", {
    method: "POST",
    body: JSON.stringify({ email, password, full_name }),
  });
}

export async function signoutUser(): Promise<void> {
  await apiFetch<{ status: string }>("/auth/signout", { method: "POST" }).catch(() => {});
}

// ─── Vacancies ────────────────────────────────────────────────────────────────

export async function listVacancies(): Promise<Vacancy[]> {
  const data = await apiFetch<{ runs: BackendHistoryRun[] }>("/cabinet/history?limit=50");
  return data.runs
    .filter((r) => r.status === "success")
    .map((r) => ({
      id: r.run_id,
      title: r.vacancy_title || "Custom Vacancy",
      description: r.vacancy_description_preview || "",
      extractedSkills: [],
      weights: { skills: 0.65, experience: 0.35 },
      status: "READY" as const,
      candidatesFound: r.returned_count ?? 0,
      createdAt: r.created_at,
      shortlistReadyAt: r.created_at,
    }));
}

export async function createVacancy(payload: {
  title: string;
  description: string;
}): Promise<{ vacancy: Vacancy; processingJob: ProcessingJob }> {
  const data = await apiFetch<BackendShortlistResponse>("/shortlist/vacancy", {
    method: "POST",
    body: JSON.stringify({
      vacancy_title: payload.title,
      vacancy_description: payload.description,
      top_k: 20,
      num_candidates: 100,
    }),
  });

  const vacancy: Vacancy = {
    id: data.proxy_job_id ?? data.job_id,
    title: data.job_title,
    description: payload.description,
    extractedSkills: [],
    weights: { skills: 0.65, experience: 0.35 },
    status: "READY",
    candidatesFound: data.total_candidates,
    createdAt: new Date().toISOString(),
    shortlistReadyAt: new Date().toISOString(),
  };

  const processingJob: ProcessingJob = {
    id: "noop",
    vacancyId: vacancy.id,
    queueDepth: 0,
    startedAt: Date.now(),
    completed: true,
    steps: [
      { key: "parsing", label: "Parsing job description", status: "done", progress: 100 },
      { key: "searching", label: "Searching candidates", status: "done", progress: 100 },
      { key: "scoring", label: "Scoring (ML)", status: "done", progress: 100 },
      { key: "ranking", label: "Ranking", status: "done", progress: 100 },
    ],
  };

  return { vacancy, processingJob };
}

// ─── Shortlists ───────────────────────────────────────────────────────────────

export async function listShortlistCandidates(
  runId: string | null,
  minScore: number
): Promise<ShortlistCandidate[]> {
  if (!runId) return [];
  const data = await apiFetch<BackendHistoryDetail>(`/cabinet/history/${runId}`);
  return data.candidates
    .map((c) => adaptHistoryCandidate(c, runId, data.vacancy_title))
    .filter((c) => c.matchScore >= minScore);
}

// ─── Dashboard ────────────────────────────────────────────────────────────────

export async function getDashboardSummary(): Promise<DashboardSummary> {
  const [stats, runtime, history] = await Promise.all([
    apiFetch<BackendStats>("/stats"),
    apiFetch<BackendRuntimeStats>("/stats/runtime"),
    apiFetch<{ runs: BackendHistoryRun[] }>("/cabinet/history?limit=5"),
  ]);

  const pipeline = history.runs.slice(0, 5).map((r) => ({
    vacancyId: r.run_id,
    vacancyTitle: r.vacancy_title || "Custom Vacancy",
    status: "READY" as const,
    progress: 100,
  }));

  return {
    totalVacancies: history.runs.length,
    resumesProcessed: stats.total_resumes,
    avgMatchingScore: 0,
    avgShortlistHours: 0,
    pipeline,
    insights: {
      modelAccuracy: 92.4,
      fairnessAlerts: 1,
      systemLoad: Math.round((runtime.error_rate ?? 0) * 100),
    },
    recentVacancies: pipeline.map((p) => makeVacancy(p.vacancyId, p.vacancyTitle)),
    recentShortlists: [],
  };
}

// ─── Analytics ────────────────────────────────────────────────────────────────

export async function getAnalyticsSummary(): Promise<AnalyticsSummary> {
  const [, globalExp] = await Promise.all([
    apiFetch<BackendStats>("/stats"),
    apiFetch<BackendGlobalExplanation>("/stats/explanations/global").catch(() => null),
  ]);

  const topFeatures = globalExp?.top_features ?? [];

  return {
    precisionAt10: 0,
    recall: 0,
    avgShortlistHours: 0,
    fairnessScore: 93.1,
    performanceSeries: [
      { label: "Nov", precision: 80, recall: 54 },
      { label: "Dec", precision: 82, recall: 57 },
      { label: "Jan", precision: 84, recall: 58 },
      { label: "Feb", precision: 86, recall: 60 },
      { label: "Mar", precision: 88, recall: 61 },
    ],
    hiringDistribution: topFeatures.slice(0, 3).map((f) => ({
      bucket: f.label,
      value: Math.round(f.mean_abs_shap * 100),
    })),
  };
}
