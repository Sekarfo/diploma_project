import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { formatHours, formatPercent } from "../lib/format";

export function AnalyticsPage(): JSX.Element {
  const query = useQuery({
    queryKey: ["analytics"],
    queryFn: api.analytics.summary
  });

  if (!query.data) {
    return (
      <section className="screen is-active">
        <p className="mono-mute">Loading analytics...</p>
      </section>
    );
  }

  const analytics = query.data;

  return (
    <section className="screen is-active">
      <header className="screen-header">
        <div>
          <h1 className="screen-title">analytics</h1>
          <p className="screen-sub">ranking confidence, throughput, fairness over time</p>
        </div>
      </header>
      <hr className="screen-divider" />

      <div className="stat-row">
        <div className="stat">
          <div className="stat-label">Precision@10</div>
          <div className="stat-value">{formatPercent(analytics.precisionAt10)}</div>
          <div className="stat-foot">ranking quality</div>
        </div>
        <div className="stat">
          <div className="stat-label">Recall</div>
          <div className="stat-value">{formatPercent(analytics.recall)}</div>
          <div className="stat-foot">coverage</div>
        </div>
        <div className="stat">
          <div className="stat-label">Avg shortlist time</div>
          <div className="stat-value">{formatHours(analytics.avgShortlistHours)}</div>
          <div className="stat-foot">queue completion</div>
        </div>
        <div className="stat">
          <div className="stat-label">Fairness score</div>
          <div className="stat-value">{formatPercent(analytics.fairnessScore)}</div>
          <div className="stat-foot">demographic parity</div>
        </div>
      </div>

      <div style={{ height: 24 }} />

      <div className="two-col">
        <div className="panel">
          <div className="panel-header">
            <h2 className="panel-title">model performance over time</h2>
          </div>
          <div className="panel-body">
            <pre style={{ margin: 0, fontFamily: "var(--font-mono)", fontSize: 13, lineHeight: 1.55, color: "var(--ink)" }}>
              {analytics.performanceSeries.map((point) => {
                const barLen = Math.round(point.precision / 2.5);
                return `${point.label.padStart(6)} ${"█".repeat(barLen)}${" ".repeat(40 - barLen)} P${point.precision}% R${point.recall}%\n`;
              }).join("")}
            </pre>
          </div>
        </div>

        <div className="panel">
          <div className="panel-header">
            <h2 className="panel-title">hiring distribution</h2>
          </div>
          <div className="panel-body">
            {analytics.hiringDistribution.map((bucket) => {
              const filled = Math.min(10, Math.round(bucket.value / 3));
              return (
                <div key={bucket.bucket}>
                  <div className="shap-row">
                    <span>{bucket.bucket}</span>
                    <span className="num">{bucket.value}</span>
                  </div>
                  <div className="shap-bar">
                    <span style={{ color: "var(--ink)" }}>{"█".repeat(filled)}</span>
                    <span style={{ color: "var(--ash)" }}>{"─".repeat(10 - filled)}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}
