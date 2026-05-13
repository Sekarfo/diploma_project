import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api } from "../api/client";
import { useUiStore } from "../store/useUiStore";

export function SettingsPage(): JSX.Element {
  const queryClient = useQueryClient();
  const setMinScoreThreshold = useUiStore((state) => state.setMinScoreThreshold);
  const setModelVersion = useUiStore((state) => state.setModelVersion);

  const query = useQuery({
    queryKey: ["settings"],
    queryFn: api.settings.get
  });

  const [modelVersion, updateModelVersion] = useState("ranker-v1.4");
  const [minScoreThreshold, updateMinScoreThreshold] = useState(65);
  const [piiMaskingEnabled, setPiiMaskingEnabled] = useState(true);
  const [auditLoggingEnabled, setAuditLoggingEnabled] = useState(true);

  useEffect(() => {
    if (!query.data) return;
    updateModelVersion(query.data.modelVersion);
    updateMinScoreThreshold(query.data.minScoreThreshold);
    setPiiMaskingEnabled(query.data.piiMaskingEnabled);
    setAuditLoggingEnabled(query.data.auditLoggingEnabled);
  }, [query.data]);

  const mutation = useMutation({
    mutationFn: () =>
      api.settings.update({ modelVersion, minScoreThreshold, piiMaskingEnabled, auditLoggingEnabled }),
    onSuccess: (settings) => {
      setMinScoreThreshold(settings.minScoreThreshold);
      setModelVersion(settings.modelVersion);
      queryClient.invalidateQueries({ queryKey: ["shortlists"] });
      queryClient.invalidateQueries({ queryKey: ["settings"] });
    }
  });

  return (
    <section className="screen is-active">
      <header className="screen-header">
        <div>
          <h1 className="screen-title">settings</h1>
          <p className="screen-sub">scopes, privacy posture, model thresholds</p>
        </div>
        <button type="button" className="btn btn-primary" onClick={() => mutation.mutate()}>
          {mutation.isPending ? "saving..." : "save settings"}
        </button>
      </header>
      <hr className="screen-divider" />

      <div className="panel">
        <div className="panel-header">
          <h2 className="panel-title">user roles</h2>
          <span className="mono-mute">3 roles defined</span>
        </div>
        <table className="tbl">
          <thead>
            <tr>
              <th>Role</th>
              <th>Scope</th>
              <th className="num">Members</th>
            </tr>
          </thead>
          <tbody>
            <tr><td>Recruiter</td><td className="muted">Review shortlist, approve/reject, submit feedback.</td><td className="num">12</td></tr>
            <tr><td>ML Engineer</td><td className="muted">Inspect explanations, monitor metrics, trigger retraining pipeline.</td><td className="num">4</td></tr>
            <tr><td>Admin</td><td className="muted">Manage integrations, threshold settings, and model versions.</td><td className="num">2</td></tr>
          </tbody>
        </table>
      </div>

      <div style={{ height: 24 }} />

      <div className="two-col">
        <div className="panel">
          <div className="panel-header">
            <h2 className="panel-title">data privacy</h2>
          </div>
          <div className="panel-body stack-16">
            <label
              className={`check${piiMaskingEnabled ? " is-on" : ""}`}
              onClick={() => setPiiMaskingEnabled((v) => !v)}
            >
              <span className="box">{piiMaskingEnabled ? "[x]" : "[ ]"}</span>
              <span>Enable PII masking on resume previews</span>
            </label>
            <label
              className={`check${auditLoggingEnabled ? " is-on" : ""}`}
              onClick={() => setAuditLoggingEnabled((v) => !v)}
            >
              <span className="box">{auditLoggingEnabled ? "[x]" : "[ ]"}</span>
              <span>Enable audit logging for reviewer actions</span>
            </label>
          </div>
        </div>

        <div className="panel">
          <div className="panel-header">
            <h2 className="panel-title">model + thresholds</h2>
          </div>
          <div className="panel-body stack-16">
            <label style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <span className="mono-mute">model version selection</span>
              <select
                className="field"
                value={modelVersion}
                onChange={(e) => updateModelVersion(e.target.value)}
              >
                <option value="ranker-v1.4">ranker-v1.4 (production)</option>
                <option value="ranker-v1.3">ranker-v1.3</option>
                <option value="baseline-v1.0">baseline-v1.0</option>
              </select>
            </label>
            <div>
              <div className="row-between" style={{ marginBottom: 8 }}>
                <span className="mono-mute">threshold · min score</span>
                <span className="num" style={{ fontWeight: 500 }}>{minScoreThreshold}%</span>
              </div>
              <input
                type="range"
                className="slider"
                min={40}
                max={95}
                value={minScoreThreshold}
                style={{ width: "100%" }}
                onChange={(e) => updateMinScoreThreshold(Number(e.target.value))}
              />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
