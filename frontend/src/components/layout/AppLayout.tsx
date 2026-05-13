import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";

export function AppLayout(): JSX.Element {
  return (
    <div className="app">
      <Sidebar />
      <main className="main">
        <TopBar />
        <Outlet />
      </main>
    </div>
  );
}

