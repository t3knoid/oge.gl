import { apiBaseUrl } from "../config";
import type {
  FilingDetailResponse,
  IngestionJobListResponse,
  ManualIngestDefaultsResponse,
  IngestionRunAcceptedResponse,
  IngestionRunRequest,
  TransactionDetailResponse,
  TransactionListQuery,
  TransactionListResponse,
} from "./types";

const TRANSACTIONS_QUERY_ORDER: Array<keyof TransactionListQuery> = [
  "filer_name",
  "description",
  "trade_type",
  "transaction_date",
  "transaction_date_from",
  "transaction_date_to",
  "amount_text",
  "amount_min",
  "amount_max",
  "page",
  "page_size",
  "sort",
  "order",
];

export type ApiClientErrorKind = "network" | "http" | "invalid_response";

export class ApiClientError extends Error {
  readonly kind: ApiClientErrorKind;
  readonly status: number | null;

  constructor(message: string, kind: ApiClientErrorKind, status: number | null = null) {
    super(message);
    this.name = "ApiClientError";
    this.kind = kind;
    this.status = status;
  }
}

function toSafeHttpMessage(status: number): string {
  if (status === 404) {
    return "Requested resource was not found.";
  }
  if (status >= 500) {
    return "The service is unavailable. Please try again.";
  }
  if (status === 400 || status === 422) {
    return "The request is invalid. Please review your input and try again.";
  }
  return "Request failed. Please try again.";
}

export function serializeTransactionsQuery(query: TransactionListQuery = {}): string {
  const params = new URLSearchParams();

  for (const key of TRANSACTIONS_QUERY_ORDER) {
    const value = query[key];
    if (value === undefined || value === null || value === "") {
      continue;
    }
    params.set(key, String(value));
  }

  return params.toString();
}

async function parseJsonResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new ApiClientError(toSafeHttpMessage(response.status), "http", response.status);
  }

  try {
    return (await response.json()) as T;
  } catch {
    throw new ApiClientError("Received an invalid response from the service.", "invalid_response");
  }
}

async function safeFetch<T>(path: string, init?: RequestInit): Promise<T> {
  try {
    const response = await fetch(`${apiBaseUrl}${path}`, {
      ...init,
      headers: {
        Accept: "application/json",
        ...(init?.headers ?? {}),
      },
    });
    return await parseJsonResponse<T>(response);
  } catch (error) {
    if (error instanceof ApiClientError) {
      throw error;
    }
    throw new ApiClientError("Unable to connect to the service. Please check your connection and try again.", "network");
  }
}

export async function getTransactions(query: TransactionListQuery = {}): Promise<TransactionListResponse> {
  const serializedQuery = serializeTransactionsQuery(query);
  const suffix = serializedQuery.length > 0 ? `?${serializedQuery}` : "";
  return safeFetch<TransactionListResponse>(`/transactions${suffix}`);
}

export async function getTransactionById(transactionId: string): Promise<TransactionDetailResponse> {
  return safeFetch<TransactionDetailResponse>(`/transactions/${transactionId}`);
}

export async function getFilingById(filingId: string): Promise<FilingDetailResponse> {
  return safeFetch<FilingDetailResponse>(`/filings/${filingId}`);
}

export async function runIngestion(request: IngestionRunRequest): Promise<IngestionRunAcceptedResponse> {
  return safeFetch<IngestionRunAcceptedResponse>("/ingest/run", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });
}

export async function getIngestionJobs(): Promise<IngestionJobListResponse> {
  return safeFetch<IngestionJobListResponse>("/ingest/jobs");
}

export async function getManualIngestDefaults(): Promise<ManualIngestDefaultsResponse> {
  return safeFetch<ManualIngestDefaultsResponse>("/ingest/defaults");
}
