import { Link, NavLink, Outlet } from "react-router-dom";
import { apiBaseUrl } from "./config";

export function AppShell(): JSX.Element {
  return (
    <div className="app-shell">
      <header className="site-header">
        <div>
          <h1>oge.gl</h1>
          <p className="subtitle">Office of Government Ethics transaction search</p>
        </div>
        <nav aria-label="Primary navigation" className="nav-links">
          <NavLink to="/" end>
            Search
          </NavLink>
          <NavLink to="/transactions/example">Transaction Detail</NavLink>
        </nav>
      </header>

      <main id="main-content" className="main-content">
        <Outlet />
      </main>

      <footer className="site-footer">
        <p>
          API base URL: <code>{apiBaseUrl}</code>
        </p>
        <p>
          Frontend routes consume backend APIs only. See <Link to="/">search filters</Link> for entry point.
        </p>
      </footer>
    </div>
  );
}
