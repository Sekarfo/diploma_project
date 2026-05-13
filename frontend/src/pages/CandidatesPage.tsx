import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../api/client";

export function CandidatesPage(): JSX.Element {
  const query = useQuery({
    queryKey: ["candidates"],
    queryFn: api.candidates.list
  });

  return (
    <section className="screen is-active">
      <header className="screen-header">
        <div>
          <h1 className="screen-title">candidates</h1>
          <p className="screen-sub">all resumes parsed across active vacancies</p>
        </div>
      </header>
      <hr className="screen-divider" />

      <div className="card-grid">
        {(query.data ?? []).map((candidate) => (
          <div className="cand-card" key={candidate.id}>
            <div className="cand-name">{candidate.fullName}</div>
            <div className="cand-meta">
              {candidate.headline} · {candidate.experienceYears}y · {candidate.location}
            </div>
            <div className="cand-skills">
              {candidate.skills.slice(0, 5).map((skill) => (
                <span key={skill} className="cand-skill">{skill}</span>
              ))}
            </div>
            <div className="cand-actions">
              <Link className="link-cli" to={`/candidates/${candidate.id}`}>view profile</Link>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
