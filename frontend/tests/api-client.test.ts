import { describe, expect, it, vi } from "vitest";

import {
  ApiClientError,
  getFilingById,
  getIngestionJobs,
  getManualIngestDefaults,
  getTransactionById,
  getTransactions,
  runIngestion,
  serializeTransactionsQuery,
} from "../src/api";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("transactions query serialization", () => {
  it("serializes filters and pagination in deterministic order", () => {
    const query = serializeTransactionsQuery({
      description: "Apple",
      filer_name: "Jane",
      amount_max: 15000,
      amount_min: 1001,
      page: 2,
      page_size: 25,
      sort: "transaction_date",
      order: "desc",
    });

    expect(query).toBe(
      "filer_name=Jane&description=Apple&amount_min=1001&amount_max=15000&page=2&page_size=25&sort=transaction_date&order=desc"
    );
  });
});

describe("frontend api client", () => {
  it("fetches transactions list", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        jsonResponse({
          items: [],
          page: 1,
          page_size: 50,
          total: 0,
          has_more: false,
          sort: "transaction_date",
          order: "desc",
        })
      )
    );

    const response = await getTransactions({ filer_name: "Jane", page: 1, page_size: 50 });

    expect(response.total).toBe(0);
    const call = vi.mocked(fetch).mock.calls[0]?.[0];
    expect(String(call)).toContain("/transactions?filer_name=Jane&page=1&page_size=50");
  });

  it("fetches transaction detail", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        jsonResponse({
          id: "txn-1",
          filing: {
            id: "filing-1",
            external_id: null,
            filer_name: "Jane Doe",
            filer_title: null,
            agency: null,
            filing_date: null,
            report_period_start: null,
            report_period_end: null,
            source_page_url: "https://example.com/page",
            source_pdf_url: "https://example.com/pdf",
            ingest_status: "completed",
            transaction_count: 1,
          },
          transaction: {
            row_number: 1,
            description: "Apple",
            issuer_name: null,
            trade_type: "purchase",
            trade_type_raw: null,
            transaction_date: null,
            transaction_date_raw: null,
            amount_text: null,
            amount_min: null,
            amount_max: null,
            raw_text: "raw",
            confidence_score: null,
          },
        })
      )
    );

    const response = await getTransactionById("txn-1");
    expect(response.id).toBe("txn-1");
  });

  it("fetches filing detail", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        jsonResponse({
          id: "filing-1",
          external_id: null,
          filer_name: "Jane Doe",
          filer_title: null,
          agency: null,
          filing_date: null,
          report_period_start: null,
          report_period_end: null,
          source_page_url: "https://example.com/page",
          source_pdf_url: "https://example.com/pdf",
          ingest_status: "completed",
          transaction_count: 1,
        })
      )
    );

    const response = await getFilingById("filing-1");
    expect(response.id).toBe("filing-1");
    expect(response.source_pdf_url).toBe("https://example.com/pdf");
  });

  it("submits an ingestion run through the centralized client", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
        expect(init?.method).toBe("POST");
        expect(init?.body).toBe(JSON.stringify({ mode: "incremental", limit: 1 }));
        return jsonResponse({
          job_id: "job-123",
          status: "queued",
          accepted_at: "2026-07-15T12:00:00Z",
        }, 202);
      })
    );

    const response = await runIngestion({ mode: "incremental", limit: 1 });

    expect(response.job_id).toBe("job-123");
    expect(String(vi.mocked(fetch).mock.calls[0]?.[0])).toContain("/ingest/run");
  });

  it("fetches ingestion jobs through the centralized client", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        jsonResponse({
          items: [
            {
              id: "job-123",
              job_type: "incremental_ingest",
              status: "queued",
              requested_at: "2026-07-15T12:00:00Z",
              started_at: null,
              finished_at: null,
              discovered_count: 0,
              downloaded_count: 0,
              ingested_count: 0,
              warning_count: 0,
              error_count: 0,
            },
          ],
        })
      )
    );

    const response = await getIngestionJobs();

    expect(response.items[0]?.id).toBe("job-123");
    expect(String(vi.mocked(fetch).mock.calls[0]?.[0])).toContain("/ingest/jobs");
  });

  it("fetches backend-owned manual ingest defaults through the centralized client", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        jsonResponse({
          mode: "incremental",
          limit: 1,
          max_limit: 25,
        })
      )
    );

    const response = await getManualIngestDefaults();

    expect(response).toEqual({ mode: "incremental", limit: 1, max_limit: 25 });
    expect(String(vi.mocked(fetch).mock.calls[0]?.[0])).toContain("/ingest/defaults");
  });

  it("maps non-2xx responses to safe typed errors", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse({ detail: "hidden" }, 404)));

    await expect(getTransactionById("missing")).rejects.toMatchObject({
      name: "ApiClientError",
      kind: "http",
      status: 404,
      message: "Requested resource was not found.",
    });
  });

  it("maps network failures to safe typed errors", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => Promise.reject(new Error("socket down"))));

    await expect(getTransactions()).rejects.toMatchObject({
      name: "ApiClientError",
      kind: "network",
      status: null,
      message: "Unable to connect to the service. Please check your connection and try again.",
    });
  });

  it("maps invalid json to a safe typed error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response("not-json", {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      )
    );

    await expect(getTransactions()).rejects.toMatchObject({
      name: "ApiClientError",
      kind: "invalid_response",
      status: null,
      message: "Received an invalid response from the service.",
    });
  });

  it("exposes ApiClientError as Error subclass", () => {
    const err = new ApiClientError("message", "http", 500);
    expect(err).toBeInstanceOf(Error);
    expect(err.kind).toBe("http");
    expect(err.status).toBe(500);
  });
});
