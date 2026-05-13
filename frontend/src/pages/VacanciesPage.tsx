import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { formatDate } from "../lib/format";
import { StatusIndicator } from "../components/common/StatusIndicator";

export function VacanciesPage(): JSX.Element {
  const navigate = useNavigate();
  const query = useQuery({
    queryKey: ["vacancies"],
    queryFn: api.vacancies.list,
    refetchInterval: 2500
  });

  return (
    <section className="screen is-active">
      <header className="screen-header">
        <div>
          <h1 className="screen-title">vacancies</h1>
          <p className="screen-sub">vacancy specs the ranker is currently scoring against</p>
        </div>
        <div className="row">
          <button type="button" className="btn btn-primary" onClick={() => navigate("/vacancies/new")}>
            + create vacancy
          </button>
        </div>
      </header>
      <hr className="screen-divider" />

      <div className="panel">
        <table className="tbl">
          <thead>
            <tr>
              <th>Vacancy title</th>
              <th>Status</th>
              <th className="num">Candidates</th>
              <th>Created</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {(query.data ?? []).map((vacancy) => (
              <tr key={vacancy.id} style={{ cursor: "pointer" }} onClick={() => navigate(`/vacancies/${vacancy.id}`)}>
                <td>{vacancy.title}</td>
                <td><StatusIndicator status={vacancy.status} /></td>
                <td className="num">{vacancy.candidatesFound}</td>
                <td className="muted">{formatDate(vacancy.createdAt)}</td>
                <td><a className="link-cli" href="#">open</a></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div style={{ height: 24 }} />
      <p className="mono-mute">
        # {query.data?.length ?? 0} records · sorted by created desc · press{" "}
        <span className="kbd">N</span> to create
      </p>
    </section>
  );
}
