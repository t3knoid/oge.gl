import { useEffect, useMemo, useState } from "react";
import type { ChangeEvent, FormEvent } from "react";
import { Link, Navigate, Route, Routes, useParams, useSearchParams } from "react-router-dom";
import { AppShell } from "./AppShell";
import { ApiClientError, getFilingById, getTransactionById, getTransactions } from "./api";
import type { FilingDetailResponse, SortField, SortOrder, TransactionDetailResponse, TransactionItem, TransactionListQuery } from "./api";

const DEFAULT_PAGE_SIZE = 5;
const DEFAULT_SORT: SortField = "transaction_date";
const DEFAULT_ORDER: SortOrder = "desc";

interface SearchFilterFormState {
  filer_name: string;
  description: string;
  trade_type: string;
  transaction_date: string;
  transaction_date_from: string;
  transaction_date_to: string;
  amount_text: string;
  amount_min: string;
  amount_max: string;
  page_size: string;
  sort: SortField;
  order: SortOrder;
}

function parsePositiveInteger(value: string | null, fallback: number): number {
  if (!value) {
    return fallback;
  }

  const parsed = Number.parseInt(value, 10);
  if (Number.isNaN(parsed) || parsed < 1) {
    return fallback;
  }

  return parsed;
}

function toFormState(searchParams: URLSearchParams): SearchFilterFormState {
  const sort = searchParams.get("sort");
  const order = searchParams.get("order");

  return {
    filer_name: searchParams.get("filer_name") ?? "",
    description: searchParams.get("description") ?? "",
    trade_type: searchParams.get("trade_type") ?? "",
    transaction_date: searchParams.get("transaction_date") ?? "",
    transaction_date_from: searchParams.get("transaction_date_from") ?? "",
    transaction_date_to: searchParams.get("transaction_date_to") ?? "",
    amount_text: searchParams.get("amount_text") ?? "",
    amount_min: searchParams.get("amount_min") ?? "",
    amount_max: searchParams.get("amount_max") ?? "",
    page_size: String(parsePositiveInteger(searchParams.get("page_size"), DEFAULT_PAGE_SIZE)),
    sort: sort === "filing_date" || sort === "filer_name" || sort === "description" || sort === "amount_min"
      ? sort
      : DEFAULT_SORT,
    order: order === "asc" ? "asc" : DEFAULT_ORDER,
  };
}

function toTransactionsQuery(searchParams: URLSearchParams): TransactionListQuery {
  const formState = toFormState(searchParams);
  const page = parsePositiveInteger(searchParams.get("page"), 1);
  const amountMin = formState.amount_min.length > 0 ? Number.parseInt(formState.amount_min, 10) : undefined;
  const amountMax = formState.amount_max.length > 0 ? Number.parseInt(formState.amount_max, 10) : undefined;

  return {
    filer_name: formState.filer_name || undefined,
    description: formState.description || undefined,
    trade_type: formState.trade_type || undefined,
    transaction_date: formState.transaction_date || undefined,
    transaction_date_from: formState.transaction_date_from || undefined,
    transaction_date_to: formState.transaction_date_to || undefined,
    amount_text: formState.amount_text || undefined,
    amount_min: Number.isNaN(amountMin) ? undefined : amountMin,
    amount_max: Number.isNaN(amountMax) ? undefined : amountMax,
    page,
    page_size: parsePositiveInteger(formState.page_size, DEFAULT_PAGE_SIZE),
    sort: formState.sort,
    order: formState.order,
  };
}

function toSearchParams(state: SearchFilterFormState, page = 1): URLSearchParams {
  const params = new URLSearchParams();

  if (state.filer_name.trim().length > 0) {
    params.set("filer_name", state.filer_name.trim());
  }
  if (state.description.trim().length > 0) {
    params.set("description", state.description.trim());
  }
  if (state.trade_type.trim().length > 0) {
    params.set("trade_type", state.trade_type.trim());
  }
  if (state.transaction_date.trim().length > 0) {
    params.set("transaction_date", state.transaction_date.trim());
  }
  if (state.transaction_date_from.trim().length > 0) {
    params.set("transaction_date_from", state.transaction_date_from.trim());
  }
  if (state.transaction_date_to.trim().length > 0) {
    params.set("transaction_date_to", state.transaction_date_to.trim());
  }
  if (state.amount_text.trim().length > 0) {
    params.set("amount_text", state.amount_text.trim());
  }
  if (state.amount_min.trim().length > 0) {
    params.set("amount_min", state.amount_min.trim());
  }
  if (state.amount_max.trim().length > 0) {
    params.set("amount_max", state.amount_max.trim());
  }

  params.set("page", String(page));
  params.set("page_size", String(parsePositiveInteger(state.page_size, DEFAULT_PAGE_SIZE)));
  params.set("sort", state.sort);
  params.set("order", state.order);

  return params;
}

function createDefaultSearchParams(): URLSearchParams {
  const defaults = toFormState(new URLSearchParams());
  return toSearchParams(defaults, 1);
}

function toPagedSearchParams(searchParams: URLSearchParams, page: number): URLSearchParams {
  const params = new URLSearchParams(searchParams);
  params.set("page", String(page));
  return params;
}

function SearchRoute(): JSX.Element {
  const [searchParams, setSearchParams] = useSearchParams();
  const [filters, setFilters] = useState<SearchFilterFormState>(() => toFormState(searchParams));
  const [items, setItems] = useState<TransactionItem[]>([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [sort, setSort] = useState<string>(DEFAULT_SORT);
  const [order, setOrder] = useState<string>(DEFAULT_ORDER);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const query = useMemo(() => toTransactionsQuery(searchParams), [searchParams]);

  useEffect(() => {
    setFilters(toFormState(searchParams));
  }, [searchParams]);

  useEffect(() => {
    let isActive = true;

    void getTransactions(query).then(
      (response) => {
        if (!isActive) {
          return;
        }
        setItems(response.items);
        setPage(response.page);
        setTotal(response.total);
        setHasMore(response.has_more);
        setSort(response.sort);
        setOrder(response.order);
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
  }, [query]);

  const onFilterChange = (event: ChangeEvent<HTMLInputElement | HTMLSelectElement>): void => {
    const { name, value } = event.target;
    setFilters((current) => ({
      ...current,
      [name]: value,
    }));
  };

  const onApplyFilters = (event: FormEvent<HTMLFormElement>): void => {
    event.preventDefault();
    setSearchParams(toSearchParams(filters, 1));
  };

  const onResetFilters = (): void => {
    const defaults = toFormState(new URLSearchParams());
    setFilters(defaults);
    setSearchParams(createDefaultSearchParams());
  };

  const onPageChange = (nextPage: number): void => {
    if (nextPage < 1) {
      return;
    }
    setSearchParams(toPagedSearchParams(searchParams, nextPage));
  };

  return (
    <section aria-labelledby="search-heading" className="panel">
      <h2 id="search-heading">Search</h2>
      <form className="filters-form" onSubmit={onApplyFilters}>
        <div className="filters-grid">
          <label>
            Filer name
            <input name="filer_name" type="text" value={filters.filer_name} onChange={onFilterChange} />
          </label>

          <label>
            Description
            <input name="description" type="text" value={filters.description} onChange={onFilterChange} />
          </label>

          <label>
            Trade type
            <select name="trade_type" value={filters.trade_type} onChange={onFilterChange}>
              <option value="">Any</option>
              <option value="purchase">Purchase</option>
              <option value="sale">Sale</option>
              <option value="exchange">Exchange</option>
              <option value="unsolicited">Unsolicited</option>
              <option value="solicited">Solicited</option>
              <option value="other">Other</option>
            </select>
          </label>

          <label>
            Transaction date
            <input name="transaction_date" type="date" value={filters.transaction_date} onChange={onFilterChange} />
          </label>

          <label>
            Date from
            <input
              name="transaction_date_from"
              type="date"
              value={filters.transaction_date_from}
              onChange={onFilterChange}
            />
          </label>

          <label>
            Date to
            <input name="transaction_date_to" type="date" value={filters.transaction_date_to} onChange={onFilterChange} />
          </label>

          <label>
            Amount text
            <input name="amount_text" type="text" value={filters.amount_text} onChange={onFilterChange} />
          </label>

          <label>
            Amount min
            <input name="amount_min" type="number" min={0} value={filters.amount_min} onChange={onFilterChange} />
          </label>

          <label>
            Amount max
            <input name="amount_max" type="number" min={0} value={filters.amount_max} onChange={onFilterChange} />
          </label>

          <label>
            Page size
            <select name="page_size" value={filters.page_size} onChange={onFilterChange}>
              <option value="5">5</option>
              <option value="10">10</option>
              <option value="25">25</option>
              <option value="50">50</option>
            </select>
          </label>

          <label>
            Sort by
            <select name="sort" value={filters.sort} onChange={onFilterChange}>
              <option value="transaction_date">Transaction date</option>
              <option value="filing_date">Filing date</option>
              <option value="filer_name">Filer name</option>
              <option value="description">Description</option>
              <option value="amount_min">Amount min</option>
            </select>
          </label>

          <label>
            Order
            <select name="order" value={filters.order} onChange={onFilterChange}>
              <option value="desc">Descending</option>
              <option value="asc">Ascending</option>
            </select>
          </label>
        </div>

        <div className="filters-actions">
          <button type="submit">Apply filters</button>
          <button type="button" onClick={onResetFilters}>
            Reset filters
          </button>
        </div>
      </form>

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
            <p>No transactions matched the active filters.</p>
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
            <p>
              Loaded {items.length} of {total} transactions from the centralized API client.
            </p>
            <p>
              Page {page} sorted by {sort} ({order}).
            </p>
            <ul>
              {items.slice(0, 3).map((item) => (
                <li key={item.id}>
                  <Link to={`/transactions/${item.id}`}>{item.filer_name}</Link>
                </li>
              ))}
            </ul>
            <div className="pagination-actions" aria-label="Pagination controls">
              <button type="button" disabled={page <= 1 || isLoading} onClick={() => onPageChange(page - 1)}>
                Previous page
              </button>
              <button type="button" disabled={!hasMore || isLoading} onClick={() => onPageChange(page + 1)}>
                Next page
              </button>
            </div>
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
