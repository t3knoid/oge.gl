import { useEffect, useMemo, useState } from "react";
import { Link, Navigate, Route, Routes, useParams } from "react-router-dom";
import { AppShell } from "./AppShell";
import { ApiClientError, getFilingById, getTransactionById, getTransactions } from "./api";
import type { FilingDetailResponse, TransactionDetailResponse, TransactionItem } from "./api";

function SearchRoute(): JSX.Element {
  const [items, setItems] = useState<TransactionItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isActive = true;

    void getTransactions({ page: 1, page_size: 5 }).then(
      (response) => {
        if (!isActive) {
          return;
        }
        setItems(response.items);
        setError(null);
      },
      (requestError: unknown) => {
        if (!isActive) {
          return;
        }

        if (requestError instanceof ApiClientError) {
          setError(requestError.message);
        } else {
          setError("Unable to load transactions.");
        }
      }
    ).finally(() => {
      if (isActive) {
        setIsLoading(false);
      }
    });

    return () => {
      isActive = false;
    };
  }, []);

  return (
    <section aria-labelledby="search-heading" className="panel">
      <h2 id="search-heading">Search</h2>
      <p>
        This shell reserves space for filer name, description, trade type, transaction date, and amount filters.
      </p>
      <div className="state-grid" aria-label="State placeholders">
        {isLoading ? (
          <article className="state-card" aria-live="polite">
            <h3>Loading</h3>
            <p>Loading transactions from the API.</p>
          </article>
        ) : null}

        {!isLoading && items.length === 0 && !error ? (
          <article className="state-card">
            <h3>Empty</h3>
            <p>No transactions were returned by the API.</p>
          </article>
        ) : null}

        {!isLoading && error ? (
          <article className="state-card" role="alert">
            <h3>Error</h3>
            <p>{error}</p>
          </article>
        ) : null}

        {!isLoading && !error && items.length > 0 ? (
          <article className="state-card">
            <h3>Loaded</h3>
            <p>Loaded {items.length} transactions from the centralized API client.</p>
            <ul>
              {items.slice(0, 3).map((item) => (
                <li key={item.id}>
                  <Link to={`/transactions/${item.id}`}>{item.filer_name}</Link>
                </li>
              ))}
            </ul>
          </article>
        ) : null}
      </div>
    </section>
  );
}

function TransactionDetailRoute(): JSX.Element {
  const { transactionId } = useParams();
  const [transaction, setTransaction] = useState<TransactionDetailResponse | null>(null);
  const [filing, setFiling] = useState<FilingDetailResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!transactionId) {
      setError("A transaction identifier is required.");
      setIsLoading(false);
      return;
    }

    let isActive = true;
    setIsLoading(true);
    setError(null);

    void getTransactionById(transactionId)
      .then(async (transactionResponse) => {
        if (!isActive) {
          return;
        }
        setTransaction(transactionResponse);
        try {
          const filingResponse = await getFilingById(transactionResponse.filing.id);
          if (isActive) {
            setFiling(filingResponse);
          }
        } catch {
          if (isActive) {
            // Keep transaction detail visible even when filing enrichment fails.
            setFiling(null);
          }
        }
      })
      .catch((requestError: unknown) => {
        if (!isActive) {
          return;
        }
        if (requestError instanceof ApiClientError) {
          setError(requestError.message);
        } else {
          setError("Unable to load transaction details.");
        }
      })
      .finally(() => {
        if (isActive) {
          setIsLoading(false);
        }
      });

    return () => {
      isActive = false;
    };
  }, [transactionId]);

  const sourcePdfUrl = useMemo(() => filing?.source_pdf_url ?? transaction?.filing.source_pdf_url ?? null, [filing, transaction]);

  return (
    <section aria-labelledby="transaction-heading" className="panel">
      <h2 id="transaction-heading">Transaction Detail</h2>

      {isLoading ? <p>Loading transaction details from the API.</p> : null}
      {!isLoading && error ? <p role="alert">{error}</p> : null}
      {!isLoading && !error ? <p>Transaction ID: {transactionId}</p> : null}

      {!isLoading && !error && transaction ? (
        <p>
          Description: <strong>{transaction.transaction.description}</strong>
        </p>
      ) : null}

      <div className="state-card">
        <h3>Source PDF Provenance</h3>
        {sourcePdfUrl ? (
          <p>
            <a href={sourcePdfUrl} target="_blank" rel="noreferrer">
              Open source PDF
            </a>
          </p>
        ) : (
          <p>Source PDF link is unavailable for this transaction.</p>
        )}
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
