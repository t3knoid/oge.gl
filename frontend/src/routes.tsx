import { Navigate, Route, Routes, useParams } from "react-router-dom";
import { AppShell } from "./AppShell";

function SearchRoute(): JSX.Element {
  return (
    <section aria-labelledby="search-heading" className="panel">
      <h2 id="search-heading">Search</h2>
      <p>
        This shell reserves space for filer name, description, trade type, transaction date, and amount filters.
      </p>
      <div className="state-grid" aria-label="State placeholders">
        <article className="state-card" aria-live="polite">
          <h3>Loading State Placeholder</h3>
          <p>Use this block when the transactions list request is pending.</p>
        </article>
        <article className="state-card">
          <h3>Empty State Placeholder</h3>
          <p>Use this block when query results are empty.</p>
        </article>
        <article className="state-card" role="alert">
          <h3>Error State Placeholder</h3>
          <p>Use this block for safe, user-facing API error summaries.</p>
        </article>
      </div>
    </section>
  );
}

function TransactionDetailRoute(): JSX.Element {
  const { transactionId } = useParams();

  return (
    <section aria-labelledby="transaction-heading" className="panel">
      <h2 id="transaction-heading">Transaction Detail</h2>
      <p>Transaction ID: {transactionId}</p>
      <div className="state-card">
        <h3>Source PDF Provenance Placeholder</h3>
        <p>This space is reserved for the backend-provided source PDF link.</p>
      </div>
    </section>
  );
}

function NotFoundRoute(): JSX.Element {
  return (
    <section aria-labelledby="not-found-heading" className="panel">
      <h2 id="not-found-heading">Page Not Found</h2>
      <p>The requested route does not exist in the frontend shell.</p>
    </section>
  );
}

export function AppRoutes(): JSX.Element {
  return (
    <Routes>
      <Route path="/" element={<AppShell />}>
        <Route index element={<SearchRoute />} />
        <Route path="transactions/:transactionId" element={<TransactionDetailRoute />} />
        <Route path="404" element={<NotFoundRoute />} />
        <Route path="*" element={<Navigate to="/404" replace />} />
      </Route>
    </Routes>
  );
}
