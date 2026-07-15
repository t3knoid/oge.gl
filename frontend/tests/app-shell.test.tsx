import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AppRoutes } from "../src/routes";

const mockTransactionId = "example";

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);

      if (url.includes("/transactions?") || url.endsWith("/transactions")) {
        return new Response(
          JSON.stringify({
            items: [
              {
                id: mockTransactionId,
                filing_id: "22222222-2222-2222-2222-222222222222",
                filer_name: "Jane Doe",
                filer_title: null,
                agency: null,
                description: "Apple Inc.",
                issuer_name: null,
                trade_type: "purchase",
                trade_type_raw: null,
                transaction_date: "2026-06-01",
                transaction_date_raw: null,
                amount_text: "$1,001 - $15,000",
                amount_min: 1001,
                amount_max: 15000,
                filing_date: "2026-06-05",
                source_pdf_url: "https://example.com/source.pdf",
              },
            ],
            page: 1,
            page_size: 5,
            total: 1,
            has_more: false,
            sort: "transaction_date",
            order: "desc",
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        );
      }

      if (url.includes(`/transactions/${mockTransactionId}`)) {
        return new Response(
          JSON.stringify({
            id: mockTransactionId,
            filing: {
              id: "22222222-2222-2222-2222-222222222222",
              external_id: null,
              filer_name: "Jane Doe",
              filer_title: null,
              agency: null,
              filing_date: "2026-06-05",
              report_period_start: null,
              report_period_end: null,
              source_page_url: "https://example.com/page",
              source_pdf_url: "https://example.com/source.pdf",
              ingest_status: "completed",
              transaction_count: 1,
            },
            transaction: {
              row_number: 1,
              description: "Apple Inc.",
              issuer_name: null,
              trade_type: "purchase",
              trade_type_raw: null,
              transaction_date: "2026-06-01",
              transaction_date_raw: null,
              amount_text: "$1,001 - $15,000",
              amount_min: 1001,
              amount_max: 15000,
              raw_text: "row",
              confidence_score: null,
            },
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        );
      }

      if (url.includes("/filings/22222222-2222-2222-2222-222222222222")) {
        return new Response(
          JSON.stringify({
            id: "22222222-2222-2222-2222-222222222222",
            external_id: null,
            filer_name: "Jane Doe",
            filer_title: null,
            agency: null,
            filing_date: "2026-06-05",
            report_period_start: null,
            report_period_end: null,
            source_page_url: "https://example.com/page",
            source_pdf_url: "https://example.com/source.pdf",
            ingest_status: "completed",
            transaction_count: 1,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        );
      }

      return new Response(JSON.stringify({ detail: "Not found" }), {
        status: 404,
        headers: { "Content-Type": "application/json" },
      });
    })
  );
});

describe("frontend shell routing", () => {
  it("renders the search shell route", () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <AppRoutes />
      </MemoryRouter>
    );

    expect(screen.getByRole("heading", { level: 2, name: "Search" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 3, name: "Loading" })).toBeInTheDocument();
  });

  it("navigates to the transaction detail route", async () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <AppRoutes />
      </MemoryRouter>
    );

    fireEvent.click(screen.getByRole("link", { name: "Transaction Detail" }));

    expect(screen.getByRole("heading", { level: 2, name: "Transaction Detail" })).toBeInTheDocument();
    expect(await screen.findByText(/Transaction ID: example/i)).toBeInTheDocument();
    expect(screen.getByText(/Source PDF Provenance/i)).toBeInTheDocument();
  });

  it("keeps transaction detail visible when filing enrichment fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);

        if (url.includes(`/transactions/${mockTransactionId}`)) {
          return new Response(
            JSON.stringify({
              id: mockTransactionId,
              filing: {
                id: "22222222-2222-2222-2222-222222222222",
                external_id: null,
                filer_name: "Jane Doe",
                filer_title: null,
                agency: null,
                filing_date: "2026-06-05",
                report_period_start: null,
                report_period_end: null,
                source_page_url: "https://example.com/page",
                source_pdf_url: "https://example.com/fallback-source.pdf",
                ingest_status: "completed",
                transaction_count: 1,
              },
              transaction: {
                row_number: 1,
                description: "Apple Inc.",
                issuer_name: null,
                trade_type: "purchase",
                trade_type_raw: null,
                transaction_date: "2026-06-01",
                transaction_date_raw: null,
                amount_text: "$1,001 - $15,000",
                amount_min: 1001,
                amount_max: 15000,
                raw_text: "row",
                confidence_score: null,
              },
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          );
        }

        if (url.includes("/filings/22222222-2222-2222-2222-222222222222")) {
          return new Response(JSON.stringify({ detail: "Not found" }), {
            status: 404,
            headers: { "Content-Type": "application/json" },
          });
        }

        return new Response(
          JSON.stringify({
            items: [],
            page: 1,
            page_size: 5,
            total: 0,
            has_more: false,
            sort: "transaction_date",
            order: "desc",
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        );
      })
    );

    render(
      <MemoryRouter initialEntries={[`/transactions/${mockTransactionId}`]}>
        <AppRoutes />
      </MemoryRouter>
    );

    expect(await screen.findByText(/Transaction ID: example/i)).toBeInTheDocument();
    expect(screen.getByText(/Description:/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Open source PDF/i })).toHaveAttribute(
      "href",
      "https://example.com/fallback-source.pdf"
    );
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
