import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { api } from "../api/client";
import { formatDate } from "../lib/format";

type EditState = Record<string, { decision: "Approve" | "Reject"; reason: string }>;

export function FeedbackTrainingPage(): JSX.Element {
  const queryClient = useQueryClient();
  const [drafts, setDrafts] = useState<EditState>({});

  const query = useQuery({
    queryKey: ["feedback"],
    queryFn: api.feedback.list
  });

  const editableRows = useMemo(() => query.data ?? [], [query.data]);

  const saveMutation = useMutation({
    mutationFn: (payload: { recordId: string; decision: "Approve" | "Reject"; reason: string }) =>
      api.feedback.update(payload.recordId, { decision: payload.decision, reason: payload.reason }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["feedback"] });
      queryClient.invalidateQueries({ queryKey: ["shortlists"] });
      queryClient.invalidateQueries({ queryKey: ["analytics"] });
    }
  });

  const retrainMutation = useMutation({
    mutationFn: (recordId: string) => api.feedback.sendToRetraining(recordId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["feedback"] })
  });

  return (
    <section className="screen is-active">
      <header className="screen-header">
        <div>
          <h1 className="screen-title">feedback &amp; training</h1>
          <p className="screen-sub">reviewer decisions feed back into the next ranker version</p>
        </div>
        <div className="row">
          <button type="button" className="btn btn-primary">⇡ trigger retraining</button>
        </div>
      </header>
      <hr className="screen-divider" />

      <div className="panel">
        <div className="panel-header">
          <h2 className="panel-title">labelled decisions</h2>
          <span className="mono-mute">{editableRows.length} records</span>
        </div>
        <table className="tbl">
          <thead>
            <tr>
              <th>Candidate</th>
              <th>Decision</th>
              <th>Reason</th>
              <th>Vacancy</th>
              <th>Model</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {editableRows.map((record) => {
              const draft = drafts[record.id] ?? { decision: record.decision, reason: record.reason };
              return (
                <tr key={record.id}>
                  <td>
                    <div className="pipeline-name">{record.candidate.fullName}</div>
                    <div className="muted">{formatDate(record.updatedAt)}</div>
                  </td>
                  <td>
                    <select
                      className="field"
                      style={{ width: 120 }}
                      value={draft.decision}
                      onChange={(e) =>
                        setDrafts((prev) => ({
                          ...prev,
                          [record.id]: { ...draft, decision: e.target.value as "Approve" | "Reject" }
                        }))
                      }
                    >
                      <option value="Approve">approve</option>
                      <option value="Reject">reject</option>
                    </select>
                  </td>
                  <td>
                    <input
                      className="field"
                      value={draft.reason}
                      onChange={(e) =>
                        setDrafts((prev) => ({
                          ...prev,
                          [record.id]: { ...draft, reason: e.target.value }
                        }))
                      }
                    />
                  </td>
                  <td>{record.vacancy.title}</td>
                  <td><code>{record.modelVersion}</code></td>
                  <td>
                    <div className="row">
                      <button
                        type="button"
                        className="btn btn-ghost btn-sm"
                        onClick={() =>
                          saveMutation.mutate({ recordId: record.id, decision: draft.decision, reason: draft.reason })
                        }
                      >
                        [edit labels]
                      </button>
                      <button
                        type="button"
                        className="btn btn-secondary btn-sm"
                        disabled={record.sentToRetraining}
                        onClick={() => retrainMutation.mutate(record.id)}
                      >
                        {record.sentToRetraining ? (
                          <span className="badge badge-warning">queued</span>
                        ) : (
                          "[send to retrain]"
                        )}
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
