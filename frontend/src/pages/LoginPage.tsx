import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { loginUser, signupUser } from "../api/realServer";
import { useAuthStore } from "../store/useAuthStore";

export function LoginPage(): JSX.Element {
  const navigate = useNavigate();
  const setAuth = useAuthStore((s) => s.setAuth);

  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: FormEvent<HTMLFormElement>): Promise<void> {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const result =
        mode === "signin"
          ? await loginUser(email, password)
          : await signupUser(email, password, fullName);
      setAuth(result.access_token, result.user);
      navigate("/", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "var(--canvas)",
      }}
    >
      <div className="panel" style={{ width: 380 }}>
        <div className="panel-header">
          <h2 className="panel-title">selects.</h2>
          <span className="mono-mute">{mode === "signin" ? "sign in" : "create account"}</span>
        </div>
        <div className="panel-body stack-16">
          <form onSubmit={onSubmit} className="stack-16">
            {mode === "signup" && (
              <label style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                <span className="mono-mute">full name</span>
                <input
                  className="field"
                  type="text"
                  placeholder="Aliya Kenzhebek"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  required
                />
              </label>
            )}
            <label style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <span className="mono-mute">email</span>
              <input
                className="field"
                type="email"
                placeholder="you@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </label>
            <label style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <span className="mono-mute">password</span>
              <input
                className="field"
                type="password"
                placeholder="········"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
              />
            </label>
            {error && <p className="mono-mute" style={{ color: "var(--danger, #c0392b)" }}>{error}</p>}
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? "..." : mode === "signin" ? "→ sign in" : "→ create account"}
            </button>
          </form>
          <hr className="screen-divider" />
          <button
            type="button"
            className="link-cli"
            onClick={() => { setMode(mode === "signin" ? "signup" : "signin"); setError(null); }}
          >
            {mode === "signin" ? "no account? sign up →" : "← back to sign in"}
          </button>
        </div>
      </div>
    </div>
  );
}
