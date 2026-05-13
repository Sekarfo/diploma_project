import { useQuery } from "@tanstack/react-query";
import { api } from "../../api/client";

export function TopBar(): JSX.Element {
  const { data } = useQuery({
    queryKey: ["dashboard", "summary", "topbar"],
    queryFn: api.dashboard.summary,
    refetchInterval: 3000,
  });

  const processingCount =
    data?.pipeline.filter((item) => item.status === "PROCESSING").length ?? 0;
  const queueState = processingCount > 0 ? "queue: processing" : "queue: healthy";

  return (
    <div className="statusbar">
      <div className="status-cell">
        <span className="status-dot" />
        <span className="status-value">{queueState}</span>
      </div>
      <div className="status-cell">
        <span className="status-label">model:</span>
        <span className="status-value">lgbm-ranker</span>
      </div>
      <div className="status-cell">
        <span className="status-label">alerts:</span>
        <span className="status-value">{processingCount}</span>
      </div>
      <div className="status-spacer" />
      <button type="button" className="icon-btn">
        <span>hr</span>
        <span className="status-label">@selects.</span>
      </button>
    </div>
  );
}
