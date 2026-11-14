import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { NichePicker, nicheName } from "@/components/screener/NichePicker";
import { DEFAULT_STATE, parseParams, serializeParams, toStocksQuery } from "@/components/screener/params";
import { Screener } from "@/components/screener/Screener";
import { StocksTable } from "@/components/screener/StocksTable";
import { toQueryString } from "@/lib/api";

import { mockFetch, NICHES, renderWithQuery, stock } from "./helpers";


const replace = vi.fn();
let search = "";
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, push: vi.fn() }),
  usePathname: () => "/",
  useSearchParams: () => new URLSearchParams(search),
}));

describe("NichePicker", () => {
  it("shows parents, then the selected parent's sub-niches", () => {
    const onChange = vi.fn();
    const { rerender } = render(<NichePicker niches={NICHES} onChange={onChange} />);
    expect(screen.queryByRole("group", { name: "Sub-niche" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Niche AI" }));
    expect(onChange).toHaveBeenLastCalledWith({ niche: "ai", sub: undefined });

    rerender(<NichePicker niches={NICHES} niche="ai" onChange={onChange} />);
    const subs = screen.getByRole("group", { name: "Sub-niche" });
    expect(within(subs).getByRole("button", { name: "Sub-niche Neoclouds" })).toHaveAttribute("title", "GPU clouds");
    fireEvent.click(within(subs).getByRole("button", { name: "Sub-niche Neoclouds" }));
    expect(onChange).toHaveBeenLastCalledWith({ niche: "ai", sub: "neoclouds" });

    rerender(<NichePicker niches={NICHES} niche="ai" sub="neoclouds" onChange={onChange} />);
    fireEvent.click(screen.getByRole("button", { name: "Sub-niche Neoclouds" }));
    expect(onChange).toHaveBeenLastCalledWith({ niche: "ai", sub: undefined });
    fireEvent.click(screen.getByRole("button", { name: /All niches/ }));
    expect(onChange).toHaveBeenLastCalledWith({});
  });

  it("looks up names for parents and sub-niches", () => {
    expect(nicheName(NICHES, "ai")).toBe("AI");
    expect(nicheName(NICHES, "small-modular-reactors")).toBe("Small Modular Reactors");
    expect(nicheName(NICHES, "nope")).toBeUndefined();
    expect(nicheName(NICHES)).toBeUndefined();
  });
});

describe("screener niche URL state", () => {
  it("round-trips browse, niche, sub-niche and asset type", () => {
    const state = { ...DEFAULT_STATE, browse: "niches" as const, niche: "ai", sub: "neoclouds", type: "etf" as const, index: "other" as const };
    const qs = serializeParams(state);
    expect(qs).toBe("browse=niches&niche=ai&sub=neoclouds&type=etf&index=other");
    expect(parseParams(new URLSearchParams(qs))).toMatchObject(state);
    expect(parseParams(new URLSearchParams("browse=bogus&type=bond")).browse).toBe("sectors");
    expect(parseParams(new URLSearchParams("type=bond")).type).toBe("all");
  });

  it("sends the sub-niche (or its parent) and ignores sector filters while browsing niches", () => {
    const base = { ...DEFAULT_STATE, sector: "Technology", niche: "ai" };
    expect(toStocksQuery({ ...base, browse: "niches" }, 50)).toMatchObject({ niche: "ai", sector: undefined });
    expect(toStocksQuery({ ...base, browse: "niches", sub: "neoclouds" }, 50).niche).toBe("neoclouds");
    expect(toStocksQuery({ ...base, browse: "sectors" }, 50)).toMatchObject({ niche: undefined, sector: "Technology" });
    expect(toQueryString(toStocksQuery({ ...DEFAULT_STATE, type: "etf" }, 10))).toContain("asset_type=etf");
  });
});

describe("Screener niches mode", () => {
  beforeEach(() => replace.mockReset());

  const routes = {
    "/api/sectors": [{ sector: "Technology", count: 1, industries: [] }],
    "/api/niches": NICHES,
    "/api/watchlists": [],
    "/api/status": { market_open: false, companies: 1, price_rows: 1, jobs: {}, refreshing: {} },
    "/api/movers": { window: "chg_1d", mode: "pct", gainers: [], losers: [] },
    "/api/stocks": { total: 1, page: 1, page_size: 50, items: [stock({ ticker: "CRWV", name: "CoreWeave", extra_source: "curated", in_sp500: false, in_ndx100: false })] },
  };

  it("switches from sectors to niches and clears sector filters", async () => {
    search = "sector=Technology";
    mockFetch(routes);
    renderWithQuery(<Screener />);
    fireEvent.click(within(screen.getByRole("group", { name: "Browse by" })).getByRole("button", { name: "Niches" }));
    expect(replace).toHaveBeenLastCalledWith("/?browse=niches", { scroll: false });
  });

  it("filters stocks and movers by the selected niche", async () => {
    search = "browse=niches&niche=ai&sub=neoclouds";
    const fetchSpy = mockFetch(routes);
    renderWithQuery(<Screener />);
    expect(await screen.findByRole("link", { name: "CRWV" })).toBeInTheDocument();
    expect(await screen.findByText("Top movers in Neoclouds")).toBeInTheDocument();
    const urls = fetchSpy.mock.calls.map((c) => String(c[0]));
    expect(urls.find((u) => u.startsWith("/api/stocks"))).toContain("niche=neoclouds");
    expect(urls.find((u) => u.startsWith("/api/movers"))).toContain("niche=neoclouds");
    expect(screen.queryByRole("group", { name: "Sector" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sub-niche Neoclouds" })).toHaveAttribute("aria-pressed", "true");

    fireEvent.change(screen.getByLabelText("Asset type"), { target: { value: "etf" } });
    await waitFor(() => expect(replace).toHaveBeenLastCalledWith("/?browse=niches&niche=ai&sub=neoclouds&type=etf", { scroll: false }));
  });
});

describe("StocksTable badges", () => {
  it("marks ETFs and symbols the user added", () => {
    renderWithQuery(
      <StocksTable
        rows={[
          stock({ ticker: "URA", name: "Global X Uranium ETF", asset_type: "etf", in_sp500: false, in_ndx100: false, extra_source: "curated" }),
          stock({ ticker: "NBIS", name: "Nebius", in_sp500: false, in_ndx100: false, extra_source: "user" }),
        ]}
        mode="pct"
        sort="market_cap"
        order="desc"
        watchlists={[]}
        onSort={() => {}}
      />,
    );
    const ura = screen.getByRole("link", { name: "URA" }).closest("tr")!;
    expect(within(ura).getByText("ETF")).toBeInTheDocument();
    expect(within(ura).queryByText("Added")).not.toBeInTheDocument();
    const nbis = screen.getByRole("link", { name: "NBIS" }).closest("tr")!;
    expect(within(nbis).getByText("Added")).toBeInTheDocument();
  });
});
