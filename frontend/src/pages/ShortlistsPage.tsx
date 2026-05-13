import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import { ExplanationPanel } from "../components/common/ExplanationPanel";
import { CandidateCard } from "../components/candidates/CandidateCard";
import { useUiStore } from "../store/useUiStore";

function scoreBar(score: number): { on: number; off: number } {
  const filled = Math.round((score / 100) * 10);
  return { on: filled, off: 10 - filled };
}

export function ShortlistsPage(): JSX.Element {
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const vacancyIdFromUrl = searchParams.get("vacancy");
  const selectedVacancyId = useUiStore((state) => state.selectedVacancyId);
  const setSelectedVacancyId = useUiStore((state) => state.setSelectedVacancyId);
  const minScoreThreshold = useUiStore((state) => state.minScoreThreshold);
  const setMinScoreThreshold = useUiStore((state) => state.setMinScoreThreshold);

  const vacancyQuery = useQuery({
    queryKey: ["vacancies"],
    queryFn: api.vacancies.list,
    refetchInterval: 2200
  });

  const shortlistQuery = useQuery({
    queryKey: ["shortlists", selectedVacancyId, minScoreThreshold],
    queryFn: () => api.shortlists.list(selectedVacancyId, minScoreThreshold),
    enabled: Boolean(selectedVacancyId)
  });

  useEffect(() => {
    if (vacancyIdFromUrl) {
      setSelectedVacancyId(vacancyIdFromUrl);
      return;
    }
    if (!selectedVacancyId) {
      const readyVacancy = vacancyQuery.data?.find((v) => v.status === "READY");
      if (readyVacancy) {
        setSelectedVacancyId(readyVacancy.id);
        setSearchParams({ vacancy: readyVacancy.id }, { replace: true });
      }
    }
  }, [vacancyIdFromUrl, selectedVacancyId, setSearchParams, setSelectedVacancyId, vacancyQuery.data]);

  const decisionMutation = useMutation({
    mutationFn: (payload: { candidateId: string; decision: "approved" | "rejected" }) =>
      api.shortlists.setDecision(selectedVacancyId ?? "", payload.candidateId, payload.decision),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["shortlists"] });
      queryClient.invalidateQueries({ queryKey: ["feedback"] });
      queryClient.invalidateQueries({ queryKey: ["analytics"] });
    }
  });

  const selectedVacancy = vacancyQuery.data?.find((v) => v.id === selectedVacancyId);

  return (
    <section className="screen is-active">
      <header className="screen-header">
        <div>
          <h1 className="screen-title">shortlists</h1>
          <p className="screen-sub">ranker output — top fits per vacancy with SHAP explanation</p>
        </div>
        <div className="row">
          <label className="field-inline mono-mute">
            vacancy:&nbsp;
            <select
              className="field"
              style={{ width: 220 }}
              value={selectedVacancyId ?? ""}
              onChange={(e) => {
                const value = e.target.value || null;
                setSelectedVacancyId(value);
                if (value) setSearchParams({ vacancy: value }, { replace: true });
              }}
            >
              {(vacancyQuery.data ?? []).map((v) => (
                <option key={v.id} value={v.id}>{v.title}</option>
              ))}
            </select>
          </label>
          <div className="slider-row">
            <span className="mono-mute">min score</span>
            <input
              type="range"
              className="slider"
              min={40}
              max={95}
              value={minScoreThreshold}
              onChange={(e) => setMinScoreThreshold(Number(e.target.value))}
            />
            <span className="num" style={{ minWidth: 36 }}>{minScoreThreshold}%</span>
          </div>
        </div>
      </header>
      <hr className="screen-divider" />

      <div className="panel">
        <div className="panel-header">
          <h2 className="panel-title">ranking · {selectedVacancy?.title ?? "—"}</h2>
          <span className="mono-mute">{shortlistQuery.data?.length ?? 0} candidates above threshold</span>
        </div>
        <table className="tbl">
          <thead>
            <tr>
              <th>Candidate</th>
              <th className="num">Match</th>
              <th className="num">Skills</th>
              <th>Experience</th>
              <th>Explanation</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {(shortlistQuery.data ?? []).map((entry) => {
              const { on, off } = scoreBar(entry.matchScore);
              return (
                <tr key={`${entry.vacancyId}-${entry.candidateId}`}>
                  <td>{entry.candidate.fullName}</td>
                  <td>
                    <div className="score">
                      <span className="score-bar">
                        <span className="on">{"█".repeat(on)}</span>
                        {off > 0 && <span className="off">{"─".repeat(off)}</span>}
                      </span>
                      <span className="num">{entry.matchScore.toFixed(1)}%</span>
                    </div>
                  </td>
                  <td className="num">{entry.skillsMatch.toFixed(1)}%</td>
                  <td>{entry.candidate.experienceYears}y</td>
                  <td className="muted">{entry.explanation}</td>
                  <td>
                    <div className="row">
                      <button
                        type="button"
                        className="btn btn-ghost btn-sm"
                        onClick={() => decisionMutation.mutate({ candidateId: entry.candidateId, decision: "approved" })}
                      >
                        [approve]
                      </button>
                      <button
                        type="button"
                        className="btn btn-danger btn-sm"
                        onClick={() => decisionMutation.mutate({ candidateId: entry.candidateId, decision: "rejected" })}
                      >
                        [reject]
                      </button>
                      <Link className="link-cli" to={`/candidates/${entry.candidateId}`}>view</Link>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div style={{ height: 32 }} />

      <div className="card-grid" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))" }}>
        {(shortlistQuery.data ?? []).slice(0, 4).map((entry) => (
          <div key={`${entry.vacancyId}-${entry.candidateId}`} className="stack-16">
            <CandidateCard entry={entry} />
            <ExplanationPanel
              title="shap-based factors"
              summary={entry.explanation}
              factors={entry.explanationFactors}
            />
          </div>
        ))}
      </div>
    </section>
  );
}
