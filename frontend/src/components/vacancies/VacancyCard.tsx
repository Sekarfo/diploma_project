import { Link } from "react-router-dom";
import type { Vacancy } from "../../types";
import { StatusIndicator } from "../common/StatusIndicator";
import { formatDateShort } from "../../lib/format";

interface Props {
  vacancy: Vacancy;
}

export function VacancyCard({ vacancy }: Props): JSX.Element {
  return (
    <div className="cand-card">
      <div className="cand-name">{vacancy.title}</div>
      <div className="cand-meta">
        {vacancy.candidatesFound} candidates · Created {formatDateShort(vacancy.createdAt)}
      </div>
      <div className="cand-skills">
        {vacancy.extractedSkills.slice(0, 4).map((skill) => (
          <span key={skill} className="cand-skill">{skill}</span>
        ))}
      </div>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: "auto" }}>
        <StatusIndicator status={vacancy.status} />
        <Link className="link-cli" to={`/vacancies/${vacancy.id}`}>open</Link>
      </div>
    </div>
  );
}
