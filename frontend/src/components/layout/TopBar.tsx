import { useNavigate } from "react-router-dom";
import { signoutUser } from "../../api/realServer";
import { useAuthStore } from "../../store/useAuthStore";

export function TopBar(): JSX.Element {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const clearAuth = useAuthStore((s) => s.clearAuth);

  async function handleSignout(): Promise<void> {
    await signoutUser();
    clearAuth();
    navigate("/login", { replace: true });
  }

  const displayName = user?.full_name?.split(" ")[0]?.toLowerCase() ?? "guest";
  const role = user?.role ?? "hr";

  return (
    <div className="statusbar">
      <div className="status-cell">
        <span className="status-dot" />
        <span className="status-value">selects. · live</span>
      </div>
      <div className="status-cell">
        <span className="status-label">model:</span>
        <span className="status-value">lgbm-ranker</span>
      </div>
      <div className="status-spacer" />
      <button type="button" className="icon-btn" onClick={handleSignout}>
        <span>{displayName}</span>
        <span className="status-label">@{role} · sign out</span>
      </button>
    </div>
  );
}
