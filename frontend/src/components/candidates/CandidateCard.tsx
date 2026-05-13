import { Link } from "react-router-dom";
import type { ShortlistCandidate } from "../../types";

interface Props {
  entry: ShortlistCandidate;
}

export function CandidateCard({ entry }: Props): JSX.Element {
  const topSkills =
    entry.topMatchingSkills.length > 0
      ? entry.topMatchingSkills
      : entry.candidate.skills.slice(0, 4);
  return (
    <div className="cand-card">
      <div className="cand-name">{entry.candidate.fullName}</div>
      <div className="cand-meta">
        {entry.candidate.headline} · {entry.candidate.experienceYears}y exp
      </div>
      <div className="cand-skills">
        {topSkills.map((skill) => (
          <span key={skill} className="cand-skill">{skill}</span>
        ))}
      </div>
      <div className="cand-actions">
        <Link className="link-cli" to={`/candidates/${entry.candidateId}`}>
          view profile
        </Link>
      </div>
    </div>
  );
}
