import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CompanyResearch } from "@/components/company/CompanyResearch";
import { Explore } from "@/components/explore/Explore";
import { EXPLORE_DEFAULTS, parseExplore, serializeExplore, toExploreQuery } from "@/components/explore/params";
import { toQueryString, type CompanyProfile, type SearchResult } from "@/lib/api";

import { mockFetch, NICHES, renderWithQuery, stock } from "./helpers";

const replace = vi.fn();
const push = vi.fn();
let search = "";
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, push }),
  usePathname: () => "/explore",
  useSearchParams: () => new URLSearchParams(search),
}));
vi.mock("lightweight-charts", () => ({
  createChart: vi.fn(() => ({
    addSeries: vi.fn(() => ({ setData: vi.fn(), applyOptions: vi.fn() })),
    applyOptions: vi.fn(),
    timeScale: () => ({ fitContent: vi.fn() }),
    remove: vi.fn(),
  })),
  CandlestickSeries: "Candlestick",
  LineSeries: "Line",
  ColorType: { Solid: "solid" },
}));

const RESULTS: SearchResult[] = [
  { symbol: "NBIS", name: "Nebius Group N.V.", exchange: "NMS", quote_type: "EQUITY", asset_type: "stock", us_listed: true, tracked: false, addable: true },
  { symbol: "YDX.DE", name: "Nebius Group N.V.", exchange: "GER", quote_type: "EQUITY", asset_type: "stock", us_listed: false, tracked: false, addable: false },
  { symbol: "^NBI", name: "Nasdaq Biotech", exchange: "NIM", quote_type: "INDEX", asset_type: null, us_listed: false, tracked: false, addable: false },
  { symbol: "NVDA", name: "NVIDIA", exchange: "NMS", quote_type: "EQUITY", asset_type: "stock", us_listed: true, tracked: true, addable: false },
];

const baseRoutes = {
  "/api/niches": NICHES,
  "/api/watchlists": [],
  "/api/stocks": { total: 1, page: 1, page_size: 50, items: [stock({ ticker: "CRWV", name: "CoreWeave", extra_source: "curated" })] },
};

describe("explore URL state", () => {
  it("round-trips filters and drops defaults", () => {
    const state = { ...EXPLORE_DEFAULTS, niche: "ai", sub: "neoclouds", type: "stock" as const, cap: "mid" as const, window: "chg_1w" as const, min: -5, max: 20, gainers: true, q: "core" };
    const qs = serializeExplore(state);
    expect(qs).toBe("niche=ai&sub=neoclouds&type=stock&cap=mid&window=chg_1w&min=-5&max=20&gainers=1&q=core");
    expect(parseExplore(new URLSearchParams(qs))).toMatchObject(state);
    expect(serializeExplore(EXPLORE_DEFAULTS)).toBe("");
    expect(parseExplore(new URLSearchParams("min=abc&window=chg_5y")).min).toBeUndefined();
  });

  it("turns gain filters into change-range API parameters", () => {
    expect(toExploreQuery({ ...EXPLORE_DEFAULTS, gainers: true }, 50)).toMatchObject({ chg_window: "chg_ytd", chg_min: 0, chg_max: undefined });
    expect(toExploreQuery({ ...EXPLORE_DEFAULTS, gainers: true, min: 10 }, 50).chg_min).toBe(10);
    expect(toExploreQuery({ ...EXPLORE_DEFAULTS, gainers: true, min: -10 }, 50).chg_min).toBe(0);
    expect(toExploreQuery({ ...EXPLORE_DEFAULTS, window: "chg_1d", max: -2 }, 50)).toMatchObject({ chg_window: "chg_1d", chg_max: -2 });
    expect(toExploreQuery(EXPLORE_DEFAULTS, 50).chg_window).toBeUndefined();
    expect(toQueryString(toExploreQuery({ ...EXPLORE_DEFAULTS, niche: "ai", sub: "neoclouds" }, 50))).toContain("niche=neoclouds");
  });
});

describe("Explore page", () => {
  beforeEach(() => {
    replace.mockReset();
    search = "";
  });

  it("filters by niche, sub-niche and gains through the URL", async () => {
    search = "niche=ai&gainers=1";
    const fetchSpy = mockFetch(baseRoutes);
    renderWithQuery(<Explore />);
    expect(await screen.findByRole("link", { name: "CRWV" })).toBeInTheDocument();
    const stocksUrl = fetchSpy.mock.calls.map((c) => String(c[0])).find((u) => u.startsWith("/api/stocks"))!;
    expect(stocksUrl).toContain("niche=ai");
    expect(stocksUrl).toContain("chg_window=chg_ytd");
    expect(stocksUrl).toContain("chg_min=0");

    const sub = await screen.findByLabelText("Sub-niche");
    await waitFor(() => expect(sub).not.toBeDisabled());
    fireEvent.change(sub, { target: { value: "neoclouds" } });
    expect(replace).toHaveBeenLastCalledWith("/explore?niche=ai&sub=neoclouds&gainers=1", { scroll: false });

    fireEvent.change(screen.getByLabelText("Niche"), { target: { value: "energy-transition" } });
    expect(replace).toHaveBeenLastCalledWith("/explore?niche=energy-transition&gainers=1", { scroll: false });

    fireEvent.click(screen.getByLabelText("Gainers only"));
    expect(replace).toHaveBeenLastCalledWith("/explore?niche=ai", { scroll: false });

    fireEvent.change(screen.getByLabelText("Min change"), { target: { value: "5" } });
    await waitFor(() => expect(replace).toHaveBeenLastCalledWith("/explore?niche=ai&min=5&gainers=1", { scroll: false }));
  });

  it("searches the market and adds a symbol with niches", async () => {
    let posted: unknown;
    mockFetch({
      ...baseRoutes,
      "/api/search": RESULTS,
      "/api/tracked/NBIS/status": { ticker: "NBIS", status: "ready", message: null },
      "/api/tracked": (_url: string, init?: RequestInit) => {
        posted = JSON.parse(String(init?.body));
        return { ...stock({ ticker: "NBIS", extra_source: "user" }), status: "adding" };
      },
    });
    renderWithQuery(<Explore />);
    fireEvent.change(screen.getByLabelText("Search the market"), { target: { value: "nebius" } });
    const results = await screen.findByRole("list", { name: "Market search results" });
    const row = (s: string) => results.querySelector(`[data-symbol="${s}"]`) as HTMLElement;
    expect(within(row("YDX.DE")).getByText("Not US-listed")).toBeInTheDocument();
    expect(within(row("^NBI")).getByText("Only stocks and ETFs")).toBeInTheDocument();
    expect(within(row("NVDA")).getByText("Already tracked")).toBeInTheDocument();

    fireEvent.click(within(row("NBIS")).getByRole("button", { name: "Add NBIS" }));
    fireEvent.click(within(row("NBIS")).getByLabelText("Neoclouds"));
    fireEvent.click(within(row("NBIS")).getByRole("button", { name: "Add to screener" }));
    expect(await within(row("NBIS")).findByText(/Added\./)).toBeInTheDocument();
    expect(posted).toEqual({ ticker: "NBIS", niche_ids: [3] });
    expect(within(row("NBIS")).getByRole("link", { name: "Open NBIS" })).toHaveAttribute("href", "/company/NBIS");
  });

  it("shows why a symbol could not be added", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url === "/api/tracked")
          return new Response(JSON.stringify({ detail: "NBIS is priced in EUR; only USD symbols can be added" }), { status: 422 });
        if (url.startsWith("/api/search")) return Response.json(RESULTS);
        if (url.startsWith("/api/niches")) return Response.json(NICHES);
        if (url.startsWith("/api/watchlists")) return Response.json([]);
        return Response.json(baseRoutes["/api/stocks"]);
      }),
    );
    renderWithQuery(<Explore />);
    fireEvent.change(screen.getByLabelText("Search the market"), { target: { value: "neb" } });
    const results = await screen.findByRole("list", { name: "Market search results" });
    fireEvent.click(within(results).getByRole("button", { name: "Add NBIS" }));
    fireEvent.click(within(results).getByRole("button", { name: "Add to screener" }));
    expect(await within(results).findByRole("alert")).toHaveTextContent("only USD symbols");
  });
});

const fresh = { fetched_at: "2026-11-10T12:00:00", status: "ok", message: null, refreshing: false };

function profile(overrides: Partial<CompanyProfile>): CompanyProfile {
  return {
    ...stock(),
    cik: null,
    exchange: "PCX",
    gics_sector: null,
    gics_sub_industry: null,
    website: null,
    description: null,
    headquarters: null,
    country: null,
    employees: null,
    founded: null,
    is_benchmark: false,
    quote: null,
    executives: [],
    niches: [],
    refresh: fresh,
    ...overrides,
  };
}

describe("Company page for niche symbols", () => {
  beforeEach(() => push.mockReset());

  it("ETFs show only overview and news and list curated niches", async () => {
    mockFetch({
      "/api/companies/URA/quote": { ticker: "URA", source: "stored", price: 30, chg_1d_pct: 1, chg_1d_abs: 0.3, as_of: null },
      "/api/companies/URA/prices": { ticker: "URA", range: "1y", interval: "1d", bars: [], benchmark: { ticker: "SPY", bars: [] } },
      "/api/companies/URA": profile({
        ticker: "URA",
        name: "Global X Uranium ETF",
        asset_type: "etf",
        sector: null,
        extra_source: "curated",
        niches: [{ id: 4, slug: "energy-transition", name: "Energy Transition", parent_slug: null, parent_name: null, source: "curated" }],
      }),
    });
    renderWithQuery(<CompanyResearch ticker="URA" />);
    expect(await screen.findByRole("heading", { name: "Global X Uranium ETF" })).toBeInTheDocument();
    expect(screen.getByText("Exchange-traded fund")).toBeInTheDocument();
    expect(screen.getByText("Net assets")).toBeInTheDocument();
    expect(screen.getAllByRole("tab").map((t) => t.textContent)).toEqual(["Overview", "News"]);
    const niches = screen.getByRole("list", { name: "Company niches" });
    expect(within(niches).getByRole("link")).toHaveAttribute("href", "/?browse=niches&niche=energy-transition");
    expect(screen.queryByRole("button", { name: "Stop tracking" })).not.toBeInTheDocument();
  });

  it("user-added stocks can edit their own niches and stop tracking", async () => {
    let saved: unknown;
    let deleted = false;
    mockFetch({
      "/api/niches": NICHES,
      "/api/companies/NBIS/quote": { ticker: "NBIS", source: "stored", price: 50, chg_1d_pct: 1, chg_1d_abs: 0.5, as_of: null },
      "/api/companies/NBIS/prices": { ticker: "NBIS", range: "1y", interval: "1d", bars: [], benchmark: { ticker: "SPY", bars: [] } },
      "/api/companies/NBIS/niches": (_u: string, init?: RequestInit) => {
        saved = JSON.parse(String(init?.body));
        return { niches: [] };
      },
      "/api/companies/NBIS": profile({
        ticker: "NBIS",
        name: "Nebius Group N.V.",
        extra_source: "user",
        in_sp500: false,
        in_ndx100: false,
        niches: [
          { id: 3, slug: "neoclouds", name: "Neoclouds", parent_slug: "ai", parent_name: "AI", source: "user" },
          { id: 2, slug: "hyperscalers", name: "Hyperscalers", parent_slug: "ai", parent_name: "AI", source: "curated" },
        ],
      }),
      "/api/tracked/NBIS": () => {
        deleted = true;
        return null;
      },
    });
    renderWithQuery(<CompanyResearch ticker="NBIS" />);
    expect(await screen.findByText("AI › Neoclouds")).toBeInTheDocument();
    expect(screen.getAllByRole("tab")).toHaveLength(5);

    fireEvent.click(screen.getByRole("button", { name: "Edit niches" }));
    const hyperscalers = await screen.findByLabelText("Hyperscalers");
    expect(hyperscalers).toBeChecked();
    expect(hyperscalers).toBeDisabled();
    expect(screen.getByLabelText("Neoclouds")).toBeChecked();
    fireEvent.click(screen.getByLabelText("Neoclouds"));
    fireEvent.click(screen.getByLabelText("Small Modular Reactors"));
    fireEvent.click(screen.getByRole("button", { name: "Save niches" }));
    await waitFor(() => expect(saved).toEqual({ niche_ids: [5] }));

    fireEvent.click(screen.getByRole("button", { name: "Stop tracking" }));
    fireEvent.click(screen.getByRole("button", { name: "Confirm: stop tracking NBIS" }));
    await waitFor(() => expect(push).toHaveBeenCalledWith("/explore"));
    expect(deleted).toBe(true);
  });
});
