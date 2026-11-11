import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { Screener } from "@/components/screener/Screener";
import { api, ApiError } from "@/lib/api";

import { mockFetch, renderWithQuery, stock } from "./helpers";

const replace = vi.fn();
let search = "";
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace }),
  usePathname: () => "/",
  useSearchParams: () => new URLSearchParams(search),
}));

describe("Screener page", () => {
  beforeEach(() => {
    replace.mockReset();
    search = "sector=Technology";
  });

  it("loads sectors, movers and stocks for the URL state and updates the URL on interaction", async () => {
    const fetchSpy = mockFetch({
      "/api/sectors": [{ sector: "Technology", count: 1, industries: [{ industry: "Semiconductors", count: 1 }] }],
      "/api/watchlists": [],
      "/api/status": { market_open: true, companies: 1, price_rows: 10, jobs: {}, refreshing: { prices: false } },
      "/api/benchmarks": [stock({ ticker: "SPY", name: "SPDR" })],
      "/api/movers": { window: "chg_1d", mode: "pct", gainers: [stock({ ticker: "NVDA", name: "NVIDIA" })], losers: [] },
      "/api/stocks": { total: 1, page: 1, page_size: 50, items: [stock({ ticker: "NVDA", name: "NVIDIA" })] },
    });
    renderWithQuery(<Screener />);

    expect(await screen.findByRole("link", { name: "NVDA" })).toBeInTheDocument();
    expect(screen.getByText("Top movers in Technology")).toBeInTheDocument();
    expect(await screen.findByText("Market open")).toBeInTheDocument();
    const stockCalls = fetchSpy.mock.calls.map((c) => String(c[0])).filter((u) => u.startsWith("/api/stocks"));
    expect(stockCalls[0]).toContain("sector=Technology");

    fireEvent.click(within(screen.getByRole("group", { name: "Mover window" })).getByRole("button", { name: "YTD" }));
    await waitFor(() => expect(replace).toHaveBeenCalled());
    expect(replace.mock.calls.at(-1)?.[0]).toBe("/?sector=Technology&window=chg_ytd");

    fireEvent.click(within(screen.getByRole("table", { name: "Stocks" })).getByRole("button", { name: "1W" }));
    expect(replace.mock.calls.at(-1)?.[0]).toBe("/?sector=Technology&sort=chg_1w");
  });

  it("surfaces API errors", async () => {
    mockFetch({ "/api/sectors": [], "/api/watchlists": [], "/api/benchmarks": [] });
    renderWithQuery(<Screener />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Could not load stocks");
  });
});

describe("api client", () => {
  it("throws ApiError with the server detail", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ detail: "a watchlist with that name already exists" }), { status: 409 })));
    await expect(api.createWatchlist("x")).rejects.toEqual(new ApiError(409, "a watchlist with that name already exists"));
  });
});
