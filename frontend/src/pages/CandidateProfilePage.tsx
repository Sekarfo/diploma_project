import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { ExplanationPanel } from "../components/common/ExplanationPanel";
import { ScoreBadge } from "../components/common/ScoreBadge";
import { api } from "../api/client";

export function CandidateProfilePage(): JSX.Element {
  const { candidateId = "" } = useParams();
  const query = useQuery({
    queryKey: ["candidate", candidateId],
    queryFn: () => api.candidates.getProfile(candidateId),
    enabled: Boolean(candidateId)
  });

  if (!query.data?.candidate) {
    return <section className="screen is-active"><p className="mono-mute">Candidate not found.</p></section>;
  }

  const { candidate, evaluations } = query.data;
  const topEvaluation = evaluations[0];

  return (
    <section className="screen is-active">
      <header className="screen-header">
        <div>
          <h1 className="screen-title">{candidate.fullName.toLowerCase()}</h1>
          <p className="screen-sub">
            {candidate.headline} · {candidate.experienceYears}y · {candidate.location}
          </p>
        </div>
        {topEvaluation ? <ScoreBadge score={topEvaluation.matchScore} /> : null}
      </header>
      <hr className="screen-divider" />

      <div className="two-col">
        <div className="panel">
          <div className="panel-header">
            <h2 className="panel-title">resume preview</h2>
          </div>
          <div className="panel-body">
            <p className="muted">{candidate.resumePreview}</p>
            <div style={{ height: 16 }} />
            <div className="kv-row">
              <span className="kv-key">Headline</span>
              <span className="kv-val">{candidate.headline}</span>
            </div>
            <div className="kv-row">
              <span className="kv-key">Experience</span>
              <span className="kv-val">{candidate.experienceYears} years</span>
            </div>
            <div className="kv-row">
              <span className="kv-key">Location</span>
              <span className="kv-val">{candidate.location}</span>
            </div>
            <div className="kv-row">
              <span className="kv-key">Skills</span>
              <span className="kv-val mono-mute">{candidate.skills.join(" · ")}</span>
            </div>
          </div>
        </div>

        <div className="panel">
          <div className="panel-header">
            <h2 className="panel-title">score breakdown</h2>
          </div>
          <div className="panel-body">
            {evaluations.length === 0 ? (
              <p className="mono-mute">No shortlist scores yet for this candidate.</p>
            ) : (
              evaluations.map((evaluation) => (
                <div key={`${evaluation.vacancyId}-${evaluation.candidateId}`} className="kv-row">
                  <div>
                    <div style={{ fontWeight: 500 }}>{evaluation.vacancy.title}</div>
                    <div className="mono-mute">
                      skills {evaluation.skillsMatch.toFixed(0)}% · exp {evaluation.experienceScore.toFixed(0)}%
                    </div>
                  </div>
                  <ScoreBadge score={evaluation.matchScore} />
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {topEvaluation ? (
        <div style={{ marginTop: 24 }}>
          <ExplanationPanel
            title="shap-based factors"
            summary={topEvaluation.explanation}
            factors={topEvaluation.explanationFactors}
          />
        </div>
      ) : null}
    </section>
  );
}
