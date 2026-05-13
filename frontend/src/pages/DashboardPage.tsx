import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { formatHours, formatPercent } from "../lib/format";
import { StatusIndicator } from "../components/common/StatusIndicator";
import { VacancyCard } from "../components/vacancies/VacancyCard";
import type { DashboardSummary } from "../types";

function StatCard(props: { label: string; value: string; foot: string }): JSX.Element {
  return (
    <div className="stat">
      <div className="stat-label">{props.label}</div>
      <div className="stat-value">{props.value}</div>
      <div className="stat-foot">{props.foot}</div>
    </div>
  );
}

export function DashboardPage(): JSX.Element {
  const query = useQuery({
    queryKey: ["dashboard", "summary"],
    queryFn: api.dashboard.summary,
    refetchInterval: (data) => {
      const current = data.state.data as DashboardSummary | undefined;
      return current?.pipeline.some((item) => item.status === "PROCESSING") ? 2200 : false;
    }
  });

  if (query.isLoading) {
    return <section className="screen is-active"><p className="mono-mute">Loading dashboard...</p></section>;
  }

  if (!query.data) {
    return <section className="screen is-active"><p className="mono-mute">Unable to load dashboard.</p></section>;
  }

  const summary = query.data;

  return (
    <section className="screen is-active">
      <header className="screen-header">
        <div>
          <h1 className="screen-title">dashboard</h1>
          <p className="screen-sub">man selects.(1) — overview of the active screening pipeline</p>
        </div>
        <div className="row">
          <Link className="btn btn-primary" to="/vacancies/new">+ create vacancy</Link>
        </div>
      </header>
      <hr className="screen-divider" />

      <div className="manpage">
        <span className="mp-cmd">NAME</span>
        <span className="mp-sep">—</span>
        <span>selects.</span>
        <span className="mp-sep">·</span>
        <span className="mp-desc">rank candidates against vacancy specifications using LSP-style resume parsing</span>
      </div>

      <div className="stat-row">
        <StatCard label="Total vacancies" value={summary.totalVacancies.toString()} foot="active pipeline inputs" />
        <StatCard label="Resumes processed" value={summary.resumesProcessed.toString()} foot="parsed and scored in queue" />
        <StatCard label="Avg matching score" value={formatPercent(summary.avgMatchingScore)} foot="top-ranked candidate fit" />
        <StatCard label="Time-to-shortlist" value={formatHours(summary.avgShortlistHours)} foot="average queue completion" />
      </div>

      <div style={{ height: 24 }} />

      <div className="two-col">
        <div className="panel">
          <div className="panel-header">
            <h2 className="panel-title">pipeline status</h2>
            <Link className="link-cli" to="/vacancies/new">+ create</Link>
          </div>
          <div className="panel-body flush">
            {summary.pipeline.map((item) => (
              <div key={item.vacancyId} className="pipeline-row">
                <div className="pipeline-name">{item.vacancyTitle}</div>
                <StatusIndicator status={item.status} />
                <div className="pipeline-bar-wrap">
                  <div className="ascii-bar">
                    <span className="filled">{"█".repeat(Math.round(item.progress / 2.5))}</span>
                    <span className="empty">{"─".repeat(40 - Math.round(item.progress / 2.5))}</span>
                  </div>
                  <span>{item.progress}%</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="panel">
          <div className="panel-header">
            <h2 className="panel-title">model insights</h2>
            <span className="mono-mute">ranker-v1.4</span>
          </div>
          <div className="panel-body">
            <div className="kv-row">
              <span className="kv-key">Model accuracy</span>
              <span className="kv-val is-success">{formatPercent(summary.insights.modelAccuracy)}</span>
            </div>
            <div className="kv-row">
              <span className="kv-key">Fairness alerts</span>
              <span className="kv-val is-warning">{summary.insights.fairnessAlerts} open</span>
            </div>
            <div className="kv-row">
              <span className="kv-key">System load</span>
              <span className="kv-val">{summary.insights.systemLoad}%</span>
            </div>
            <p style={{ marginTop: 16, fontSize: 13, color: "var(--mute)" }}>
              Live monitoring focuses on ranking confidence, fairness checks, and queue pressure.{" "}
              <Link className="link-cli" to="/analytics">open monitor</Link>
            </p>
          </div>
        </div>
      </div>

      <div style={{ height: 32 }} />

      <div className="two-col">
        <div className="panel">
          <div className="panel-header">
            <h2 className="panel-title">recent vacancies</h2>
            <Link className="link-cli" to="/vacancies">view all</Link>
          </div>
          <div className="card-grid">
            {summary.recentVacancies.map((vacancy) => (
              <VacancyCard key={vacancy.id} vacancy={vacancy} />
            ))}
          </div>
        </div>

        <div className="panel">
          <div className="panel-header">
            <h2 className="panel-title">recent shortlists</h2>
            <Link className="link-cli" to="/shortlists">open</Link>
          </div>
          <div className="panel-body flush">
            {summary.recentShortlists.map((entry) => (
              <div
                key={`${entry.vacancyId}-${entry.candidateId}`}
                className="pipeline-row"
                style={{ gridTemplateColumns: "1fr auto auto", gap: 12 }}
              >
                <div>
                  <div className="pipeline-name">{entry.candidate.fullName}</div>
                  <div className="mono-mute">{entry.vacancy.title}</div>
                </div>
                <div className="num" style={{ fontWeight: 500 }}>{entry.matchScore.toFixed(1)}%</div>
                <Link className="btn btn-ghost btn-sm" to={`/candidates/${entry.candidateId}`}>[view]</Link>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
