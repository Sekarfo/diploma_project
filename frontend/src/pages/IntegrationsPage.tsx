import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { StatusIndicator } from "../components/common/StatusIndicator";
import { formatDate } from "../lib/format";

export function IntegrationsPage(): JSX.Element {
  const query = useQuery({
    queryKey: ["integrations"],
    queryFn: api.integrations.list
  });

  return (
    <section className="screen is-active">
      <header className="screen-header">
        <div>
          <h1 className="screen-title">integrations</h1>
          <p className="screen-sub">where vacancy specs come in, where shortlists go out</p>
        </div>
        <button type="button" className="btn btn-primary">+ connect source</button>
      </header>
      <hr className="screen-divider" />

      <div className="panel">
        <table className="tbl">
          <thead>
            <tr>
              <th>Source</th>
              <th>Description</th>
              <th>Status</th>
              <th>Last sync</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {(query.data ?? []).map((integration) => (
              <tr key={integration.key}>
                <td>{integration.title}</td>
                <td className="muted">{integration.description}</td>
                <td><StatusIndicator status={integration.status} /></td>
                <td className="muted">{formatDate(integration.lastSync)}</td>
                <td>
                  <a className="link-cli" href="#">configure</a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
