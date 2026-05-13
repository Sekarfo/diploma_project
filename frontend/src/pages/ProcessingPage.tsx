import { useQuery } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client";
import { ProgressTracker } from "../components/common/ProgressTracker";
import { useUiStore } from "../store/useUiStore";

export function ProcessingPage(): JSX.Element {
  const { jobId = "" } = useParams();
  const navigate = useNavigate();
  const setActiveProcessingJobId = useUiStore((state) => state.setActiveProcessingJobId);
  const setSelectedVacancyId = useUiStore((state) => state.setSelectedVacancyId);

  const query = useQuery({
    queryKey: ["processing", jobId],
    queryFn: () => api.processing.get(jobId),
    enabled: Boolean(jobId),
    refetchInterval: (value) => {
      const job = value.state.data;
      return job && !job.completed ? 1200 : false;
    }
  });

  const job = query.data;

  if (!job) {
    return <section className="screen is-active"><p className="mono-mute">Processing job not found.</p></section>;
  }

  const progress = Math.round(job.steps.reduce((acc, step) => acc + step.progress, 0) / job.steps.length);

  return (
    <section className="screen is-active">
      <header className="screen-header">
        <div>
          <h1 className="screen-title">processing</h1>
          <p className="screen-sub">queue depth: {job.queueDepth}</p>
        </div>
      </header>
      <hr className="screen-divider" />

      <ProgressTracker steps={job.steps} />

      <div style={{ height: 24 }} />

      <div className="panel">
        <div className="panel-header">
          <h2 className="panel-title">
            {job.completed ? "shortlist ready" : "background pipeline in progress"}
          </h2>
          <span className="mono-mute">{progress}% complete</span>
        </div>
        <div className="panel-body">
          <p className="muted">
            {job.completed
              ? "Parsing, search, scoring, and ranking are complete. Candidate shortlist is ready for review."
              : "This screen polls the job state to reflect async queue updates."}
          </p>
          {job.completed ? (
            <button
              type="button"
              className="btn btn-primary"
              style={{ marginTop: 16 }}
              onClick={() => {
                setActiveProcessingJobId(null);
                setSelectedVacancyId(job.vacancyId);
                navigate(`/shortlists?vacancy=${job.vacancyId}`);
              }}
            >
              open shortlist →
            </button>
          ) : null}
        </div>
      </div>
    </section>
  );
}
