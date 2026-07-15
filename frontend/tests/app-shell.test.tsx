import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AppRoutes } from "../src/routes";

const mockTransactionId = "example";
const filingId = "22222222-2222-2222-2222-222222222222";

function buildTransactionsResponse(url: string): Response {
  const parsed = new URL(url, "http://localhost");
  const filerName = parsed.searchParams.get("filer_name");
  const page = Number.parseInt(parsed.searchParams.get("page") ?? "1", 10);
  const pageSize = Number.parseInt(parsed.searchParams.get("page_size") ?? "5", 10);
  const sort = parsed.searchParams.get("sort") ?? "transaction_date";
  const order = parsed.searchParams.get("order") ?? "desc";

  if (filerName === "empty") {
    return new Response(
      JSON.stringify({
        items: [],
        page,
        page_size: pageSize,
        total: 0,
        has_more: false,
        sort,
        order,
      }),
      { status: 200, headers: { "Content-Type": "application/json" } }
    );
  }

  const id = page === 2 ? "example-page-2" : mockTransactionId;
  return new Response(
    JSON.stringify({
      items: [
        {
          id,
          filing_id: filingId,
          filer_name: filerName ?? "Jane Doe",
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
      page,
      page_size: pageSize,
      total: 2,
      has_more: page < 2,
      sort,
      order,
    }),
    { status: 200, headers: { "Content-Type": "application/json" } }
  );
}

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);

      if (url.includes("/transactions?") || url.endsWith("/transactions")) {
        return buildTransactionsResponse(url);
      }

      if (url.includes(`/transactions/${mockTransactionId}`)) {
        return new Response(
          JSON.stringify({
            id: mockTransactionId,
            filing: {
              id: filingId,
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
  it("renders search controls for required filter fields", () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <AppRoutes />
      </MemoryRouter>
    );

    expect(screen.getByRole("heading", { level: 2, name: "Search" })).toBeInTheDocument();
    expect(screen.getByLabelText(/Filer name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Description/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Trade type/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Transaction date/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Date from/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Date to/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Amount text/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Amount min/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Amount max/i)).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 3, name: "Loading" })).toBeInTheDocument();
  });

  it("maps combined filters to backend query parameters through the centralized client", async () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <AppRoutes />
      </MemoryRouter>
    );

    fireEvent.change(screen.getByLabelText(/Filer name/i), { target: { value: "Jordan" } });
    fireEvent.change(screen.getByLabelText(/Description/i), { target: { value: "Apple" } });
    fireEvent.change(screen.getByLabelText(/Trade type/i), { target: { value: "sale" } });
    fireEvent.change(screen.getByLabelText(/Transaction date/i), { target: { value: "2026-06-01" } });
    fireEvent.change(screen.getByLabelText(/Date from/i), { target: { value: "2026-05-01" } });
    fireEvent.change(screen.getByLabelText(/Date to/i), { target: { value: "2026-06-30" } });
    fireEvent.change(screen.getByLabelText(/Amount text/i), { target: { value: "$1,001 - $15,000" } });
    fireEvent.change(screen.getByLabelText(/Amount min/i), { target: { value: "1001" } });
    fireEvent.change(screen.getByLabelText(/Amount max/i), { target: { value: "15000" } });

    fireEvent.click(screen.getByRole("button", { name: /Apply filters/i }));

    await waitFor(() => {
      const lastCall = String(vi.mocked(fetch).mock.calls.at(-1)?.[0] ?? "");
      expect(lastCall).toContain("filer_name=Jordan");
      expect(lastCall).toContain("description=Apple");
      expect(lastCall).toContain("trade_type=sale");
      expect(lastCall).toContain("transaction_date=2026-06-01");
      expect(lastCall).toContain("transaction_date_from=2026-05-01");
      expect(lastCall).toContain("transaction_date_to=2026-06-30");
      expect(lastCall).toContain("amount_text=%241%2C001+-+%2415%2C000");
      expect(lastCall).toContain("amount_min=1001");
      expect(lastCall).toContain("amount_max=15000");
      expect(lastCall).toContain("page=1");
      expect(lastCall).toContain("page_size=5");
      expect(lastCall).toContain("sort=transaction_date");
      expect(lastCall).toContain("order=desc");
    });
  });

  it("resets filters and restores the default deterministic query", async () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <AppRoutes />
      </MemoryRouter>
    );

    fireEvent.change(screen.getByLabelText(/Filer name/i), { target: { value: "empty" } });
    fireEvent.click(screen.getByRole("button", { name: /Apply filters/i }));

    expect(await screen.findByText(/No transactions matched the active filters./i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Reset filters/i }));

    await waitFor(() => {
      const lastCall = String(vi.mocked(fetch).mock.calls.at(-1)?.[0] ?? "");
      expect(lastCall).toContain("/transactions?page=1&page_size=5&sort=transaction_date&order=desc");
    });
    expect((screen.getByLabelText(/Filer name/i) as HTMLInputElement).value).toBe("");
  });

  it("supports deterministic pagination state for filtered results", async () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <AppRoutes />
      </MemoryRouter>
    );

    fireEvent.click(await screen.findByRole("button", { name: /Next page/i }));

    await waitFor(() => {
      const lastCall = String(vi.mocked(fetch).mock.calls.at(-1)?.[0] ?? "");
      expect(lastCall).toContain("page=2");
      expect(lastCall).toContain("page_size=5");
      expect(lastCall).toContain("sort=transaction_date");
      expect(lastCall).toContain("order=desc");
    });
  });

  it("shows an empty state for filtered query results", async () => {
    render(
      <MemoryRouter
        initialEntries={[
          "/?filer_name=empty&page=1&page_size=5&sort=transaction_date&order=desc",
        ]}
      >
        <AppRoutes />
      </MemoryRouter>
    );

    expect(await screen.findByText(/No transactions matched the active filters./i)).toBeInTheDocument();
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
