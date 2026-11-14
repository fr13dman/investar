import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { sparklinePath, Sparkline } from "@/components/market/Sparkline";
import { FilterBar } from "@/components/screener/FilterBar";
import { SectorPicker } from "@/components/screener/SectorPicker";
import { StocksTable } from "@/components/screener/StocksTable";

import { renderWithQuery, stock } from "./helpers";

const SECTORS = [
  { sector: "Technology", count: 3, industries: [{ industry: "Semiconductors", count: 2 }, { industry: "Software", count: 1 }] },
  { sector: "Energy", count: 1, industries: [{ industry: "Oil & Gas", count: 1 }] },
];

describe("Sparkline", () => {
  it("draws a path scaled to the box", () => {
    expect(sparklinePath([1, 2], 10, 10, 0)).toBe("M0.0,10.0 L10.0,0.0");
    expect(sparklinePath([5], 10, 10)).toBe("");
  });

  it("labels trend direction", () => {
    render(<Sparkline values={[3, 2, 1]} />);
    expect(screen.getByRole("img", { name: "5-day trend down" })).toBeInTheDocument();
  });
});

describe("SectorPicker", () => {
  it("selects a sector, then shows and selects its industries", () => {
    const onChange = vi.fn();
    const { rerender } = render(<SectorPicker sectors={SECTORS} onChange={onChange} />);
    expect(screen.queryByRole("group", { name: "Industry" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Sector Technology" }));
    expect(onChange).toHaveBeenCalledWith({ sector: "Technology" });

    rerender(<SectorPicker sectors={SECTORS} sector="Technology" onChange={onChange} />);
    const industries = screen.getByRole("group", { name: "Industry" });
    fireEvent.click(within(industries).getByRole("button", { name: "Industry Semiconductors" }));
    expect(onChange).toHaveBeenLastCalledWith({ sector: "Technology", industry: "Semiconductors" });
    expect(screen.getByRole("button", { name: "Sector Technology" })).toHaveAttribute("aria-pressed", "true");
  });
});

describe("FilterBar", () => {
  it("emits index, cap band and unit changes", () => {
    const onChange = vi.fn();
    render(<FilterBar type="all" index="all" mode="pct" watchlists={[]} onChange={onChange} />);
    fireEvent.change(screen.getByLabelText("Index"), { target: { value: "ndx100" } });
    expect(onChange).toHaveBeenCalledWith({ index: "ndx100" });
    fireEvent.change(screen.getByLabelText("Market cap"), { target: { value: "mega" } });
    expect(onChange).toHaveBeenCalledWith({ cap: "mega" });
    fireEvent.click(screen.getByRole("button", { name: "$" }));
    expect(onChange).toHaveBeenCalledWith({ mode: "abs" });
    expect(screen.queryByLabelText("Watchlist")).not.toBeInTheDocument();
  });

  it("debounces search", async () => {
    vi.useFakeTimers();
    const onChange = vi.fn();
    render(<FilterBar type="all" index="all" mode="pct" watchlists={[]} onChange={onChange} />);
    fireEvent.change(screen.getByLabelText("Search ticker or company"), { target: { value: "nv" } });
    expect(onChange).not.toHaveBeenCalled();
    vi.advanceTimersByTime(350);
    expect(onChange).toHaveBeenCalledWith({ q: "nv" });
    vi.useRealTimers();
  });
});

describe("StocksTable", () => {
  const rows = [stock(), stock({ ticker: "XOM", name: "Exxon", in_ndx100: false, chg_1d_pct: -2.1, chg_1d_abs: -2.3 })];

  it("renders rows with formatted values and index badges", () => {
    renderWithQuery(<StocksTable rows={rows} mode="pct" sort="market_cap" order="desc" watchlists={[]} onSort={vi.fn()} />);
    const aapl = screen.getByRole("link", { name: "AAPL" }).closest("tr")!;
    expect(within(aapl).getByText("$200.00")).toBeInTheDocument();
    expect(within(aapl).getByText("+1.25%")).toHaveAttribute("data-tone", "gain");
    expect(within(aapl).getByText("$3.10T")).toBeInTheDocument();
    expect(within(aapl).getByText("NDX")).toBeInTheDocument();
    const xom = screen.getByRole("link", { name: "XOM" }).closest("tr")!;
    expect(within(xom).getByText("-2.10%")).toHaveAttribute("data-tone", "loss");
    expect(within(xom).queryByText("NDX")).not.toBeInTheDocument();
  });

  it("shows dollar changes in abs mode", () => {
    renderWithQuery(<StocksTable rows={rows} mode="abs" sort="chg_1d" order="desc" watchlists={[]} onSort={vi.fn()} />);
    expect(screen.getByText("+$2.47")).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: /1D/ })).toHaveAttribute("aria-sort", "descending");
  });

  it("updates change cells when the mode prop changes on the same table", () => {
    const { rerender } = renderWithQuery(
      <StocksTable rows={rows} mode="pct" sort="market_cap" order="desc" watchlists={[]} onSort={vi.fn()} />,
    );
    expect(screen.getByText("+1.25%")).toBeInTheDocument();
    rerender(
      <QueryClientProvider client={new QueryClient()}>
        <StocksTable rows={rows} mode="abs" sort="market_cap" order="desc" watchlists={[]} onSort={vi.fn()} />
      </QueryClientProvider>,
    );
    expect(screen.getByText("+$2.47")).toBeInTheDocument();
    expect(screen.queryByText("+1.25%")).not.toBeInTheDocument();
  });

  it("requests server sorting from header clicks", () => {
    const onSort = vi.fn();
    renderWithQuery(<StocksTable rows={rows} mode="pct" sort="market_cap" order="desc" watchlists={[]} onSort={onSort} />);
    fireEvent.click(screen.getByRole("button", { name: "YTD" }));
    expect(onSort).toHaveBeenCalledWith("chg_ytd");
    fireEvent.click(screen.getByRole("button", { name: /Market cap/ }));
    expect(onSort).toHaveBeenCalledWith("market_cap");
    expect(screen.queryByRole("button", { name: "5D" })).not.toBeInTheDocument();
  });

  it("shows an empty state", () => {
    renderWithQuery(<StocksTable rows={[]} mode="pct" sort="market_cap" order="desc" watchlists={[]} onSort={vi.fn()} />);
    expect(screen.getByText("No stocks match these filters.")).toBeInTheDocument();
  });
});
