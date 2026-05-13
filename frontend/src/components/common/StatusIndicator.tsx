import type { VacancyStatus } from "../../types";

interface Props {
  status: VacancyStatus | "healthy" | "degraded" | "connected" | "token_expired" | "idle";
}

const statusClass: Record<string, string> = {
  NEW: "badge-info",
  PROCESSING: "badge-warning",
  READY: "badge-success",
  healthy: "badge-success",
  degraded: "badge-warning",
  connected: "badge-success",
  token_expired: "badge-warning",
  idle: "badge-info",
};

const statusLabel: Record<string, string> = {
  NEW: "new",
  PROCESSING: "processing",
  READY: "ready",
  healthy: "healthy",
  degraded: "degraded",
  connected: "connected",
  token_expired: "token expired",
  idle: "idle",
};

export function StatusIndicator({ status }: Props): JSX.Element {
  const cls = statusClass[status] ?? "";
  const label = statusLabel[status] ?? status.toLowerCase();
  return <span className={`badge ${cls}`}>{label}</span>;
}
