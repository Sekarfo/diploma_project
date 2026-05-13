import { NavLink } from "react-router-dom";

const pipelineNav = [
  { label: "Dashboard", to: "/", end: true },
  { label: "Vacancies", to: "/vacancies" },
  { label: "Candidates", to: "/candidates" },
  { label: "Shortlists", to: "/shortlists" },
];

const modelNav = [
  { label: "Analytics", to: "/analytics" },
  { label: "Feedback & Training", to: "/feedback-training" },
  { label: "Integrations", to: "/integrations" },
  { label: "Settings", to: "/settings" },
];

function NavItem({ label, to, end }: { label: string; to: string; end?: boolean }): JSX.Element {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) => `nav-item${isActive ? " is-active" : ""}`}
    >
      {({ isActive }) => (
        <>
          <span className="nav-glyph">{isActive ? "[x]" : "[+]"}</span>
          <span>{label}</span>
          <span className="nav-count" />
        </>
      )}
    </NavLink>
  );
}

export function Sidebar(): JSX.Element {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-mark">selects.</div>
        <div className="brand-sub">screening console · v1.4</div>
      </div>

      <div className="nav-section-label">Pipeline</div>
      <nav className="nav">
        {pipelineNav.map((item) => (
          <NavItem key={item.to} {...item} />
        ))}
      </nav>

      <div className="nav-section-label">Model</div>
      <nav className="nav">
        {modelNav.map((item) => (
          <NavItem key={item.to} {...item} />
        ))}
      </nav>

      <div className="flow-scope">
        <div className="flow-scope-label">Flow scope</div>
        <div className="flow-scope-body">
          vacancy → processing<br />
          → shortlist → feedback
        </div>
      </div>
    </aside>
  );
}
