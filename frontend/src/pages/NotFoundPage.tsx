import { Link } from "react-router-dom";

export function NotFoundPage(): JSX.Element {
  return (
    <section className="screen is-active">
      <header className="screen-header">
        <div>
          <h1 className="screen-title">404</h1>
          <p className="screen-sub">page not found</p>
        </div>
      </header>
      <hr className="screen-divider" />
      <Link className="link-cli" to="/">← return to dashboard</Link>
    </section>
  );
}

