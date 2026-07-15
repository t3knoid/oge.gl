import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { AppRoutes } from "../src/routes";

describe("frontend shell routing", () => {
  it("renders the search shell route", () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <AppRoutes />
      </MemoryRouter>
    );

    expect(screen.getByRole("heading", { level: 2, name: "Search" })).toBeInTheDocument();
    expect(screen.getByText(/Loading State Placeholder/i)).toBeInTheDocument();
  });

  it("navigates to the transaction detail route", () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <AppRoutes />
      </MemoryRouter>
    );

    fireEvent.click(screen.getByRole("link", { name: "Transaction Detail" }));

    expect(screen.getByRole("heading", { level: 2, name: "Transaction Detail" })).toBeInTheDocument();
    expect(screen.getByText(/Transaction ID: example/i)).toBeInTheDocument();
    expect(screen.getByText(/Source PDF Provenance Placeholder/i)).toBeInTheDocument();
  });
});
