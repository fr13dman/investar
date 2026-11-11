import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { CompanyResearch } from "@/components/company/CompanyResearch";
import type { CeoScorecard, CompanyProfile, NewsResponse } from "@/lib/api";

import { mockFetch, renderWithQuery, stock } from "./helpers";

const series = { setData: vi.fn() };
vi.mock("lightweight-charts", () => ({
  createChart: vi.fn(() => ({ addSeries: vi.fn(() => series), timeScale: () => ({ fitContent: vi.fn() }), remove: vi.fn() })),
  CandlestickSeries: "Candlestick",
  LineSeries: "Line",
  ColorType: { Solid: "solid" },
}));

vi.mock("react-simple-maps", () => ({ ComposableMap: () => null, Geographies: () => null, Geography: () => null }));

const fresh = { fetched_at: "2026-11-10T12:00:00", status: "ok", message: null, refreshing: false };

const company: CompanyProfile = {
  ...stock(),
  cik: "0000320193",
  exchange: "NMS",
  gics_sector: "Information Technology",
  gics_sub_industry: "Technology Hardware",
  website: "https://www.apple.com",
  description: "Apple designs phones.",
  headquarters: "Cupertino, CA, United States",
  country: "United States",
  employees: 167000,
  founded: "1976",
  is_benchmark: false,
  quote: null,
  executives: [{ name: "John Ternus", title: "CEO & Director", total_pay: 1e7, is_ceo: true }],
  refresh: fresh,
};

const scorecard: CeoScorecard = {
  ceo_name: "John Ternus",
  tenure_start: "2026-09-01",
  tenure_source: "wikidata-unlabeled",
  window_start: "2026-09-01",
  window_truncated: false,
  tsr_pct: 7.2,
  spy_tsr_pct: -1.3,
  excess_return_pct: 8.5,
  tsr_annualized_pct: 40,
  spy_annualized_pct: -5,
  revenue_cagr_pct: 15.1,
  eps_cagr_pct: 20.5,
  margin_start_pct: 26.9,
  margin_end_pct: 27.6,
  fundamentals: [{ fiscal_year_end: "2026-09-26", revenue: 478.8e9, eps: 8.1, net_income: 132e9, net_margin_pct: 27.6 }],
  pay_vs_performance: [
    { fiscal_year_end: "2025-09-27", peo_total_comp: 74.3e6, peo_comp_actually_paid: 108.4e6, tsr_value: 233.88, peer_tsr_value: 279.51, peo_names: ["Mr. Cook"] },
  ],
  tenures: [],
  computed_at: "2026-11-10T12:00:00",
};

const news: NewsResponse = {
  items: [
    { headline: "Apple beats estimates", summary: null, source: "Reuters", url: "https://n/1", image: null, published_at: "2026-11-10T10:00:00", sentiment: { label: "positive", score: 0.8, model: "finbert" } },
    { headline: "Apple sued", summary: "Lawsuit", source: "Bloomberg", url: "https://n/2", image: null, published_at: "2026-11-09T10:00:00", sentiment: { label: "negative", score: -0.7, model: "finbert" } },
  ],
  summary: { positive: 1, neutral: 0, negative: 1, average_score: 0.05 },
  refresh: fresh,
  configured: true,
};

function routes(overrides: Record<string, unknown> = {}) {
  return mockFetch({
    "/api/companies/AAPL/quote": { ticker: "AAPL", source: "finnhub", price: 250.5, chg_1d_pct: 2.1, chg_1d_abs: 5.2, as_of: "2026-11-10T15:00:00" },
    "/api/companies/AAPL/prices": { ticker: "AAPL", range: "1y", interval: "1d", bars: [{ time: "2026-01-02", open: 1, high: 1, low: 1, close: 100, volume: 1 }, { time: "2026-01-05", open: 1, high: 1, low: 1, close: 110, volume: 1 }], benchmark: { ticker: "SPY", bars: [{ time: "2026-01-02", open: 1, high: 1, low: 1, close: 500, volume: 1 }, { time: "2026-01-05", open: 1, high: 1, low: 1, close: 505, volume: 1 }] } },
    "/api/companies/AAPL/ceo": { scorecard, refresh: fresh },
    "/api/companies/AAPL/news": news,
    "/api/companies/AAPL": company,
    ...overrides,
  });
}

describe("CompanyResearch", () => {
  it("renders the header with the live quote and the chart with SPY", async () => {
    routes();
    renderWithQuery(<CompanyResearch ticker="AAPL" />);
    expect(await screen.findByRole("heading", { name: "Apple Inc." })).toBeInTheDocument();
    await waitFor(() => expect(screen.getByTestId("live-price")).toHaveTextContent("$250.50"));
    expect(screen.getByText("Real-time (Finnhub)", { exact: false })).toBeInTheDocument();
    expect(screen.getByText("Apple designs phones.")).toBeInTheDocument();
    await waitFor(() => expect(series.setData).toHaveBeenCalledTimes(2));
    expect(screen.getByRole("link", { name: "Consumer Electronics" })).toHaveAttribute(
      "href",
      "/?sector=Technology&industry=Consumer%20Electronics",
    );
  });

  it("shows the CEO scorecard and saves an override", async () => {
    const fetchSpy = routes();
    renderWithQuery(<CompanyResearch ticker="AAPL" />);
    fireEvent.click(await screen.findByRole("tab", { name: "CEO performance" }));
    expect(await screen.findByText("John Ternus")).toBeInTheDocument();
    expect(screen.getByText(/unlabeled entry, please verify/)).toBeInTheDocument();
    expect(screen.getByText("+8.50%")).toBeInTheDocument();
    const pvp = screen.getByRole("table", { name: "Pay versus performance" });
    expect(within(pvp).getByText("$108.40M")).toBeInTheDocument();
    expect(within(pvp).getByText("$233.88")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Tenure start"), { target: { value: "2026-08-15" } });
    fireEvent.click(screen.getByRole("button", { name: "Save override" }));
    await waitFor(() =>
      expect(fetchSpy.mock.calls.some(([u, init]) => String(u) === "/api/companies/AAPL/ceo" && init?.method === "PUT")).toBe(true),
    );
    const put = fetchSpy.mock.calls.find(([, init]) => init?.method === "PUT")!;
    expect(JSON.parse(String(put[1]!.body))).toEqual({ ceo_name: "John Ternus", tenure_start: "2026-08-15" });
  });

  it("lists news with sentiment and filters by tone", async () => {
    routes();
    renderWithQuery(<CompanyResearch ticker="AAPL" />);
    fireEvent.click(await screen.findByRole("tab", { name: "News" }));
    const list = await screen.findByRole("list", { name: "News" });
    expect(await within(list).findAllByRole("listitem")).toHaveLength(2);
    expect(within(list).getByText("positive")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "negative 1" }));
    expect(within(list).getAllByRole("listitem")).toHaveLength(1);
    expect(within(list).getByRole("link", { name: "Apple sued" })).toHaveAttribute("target", "_blank");
  });

  it("explains how to enable news when no key is configured", async () => {
    routes({ "/api/companies/AAPL/news": { ...news, items: [], configured: false, summary: { positive: 0, neutral: 0, negative: 0, average_score: null } } });
    renderWithQuery(<CompanyResearch ticker="AAPL" />);
    fireEvent.click(await screen.findByRole("tab", { name: "News" }));
    expect(await screen.findByText(/FINNHUB_API_KEY/)).toBeInTheDocument();
  });

  it("shows a friendly message for unknown tickers", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ detail: "unknown ticker ZZZZ" }), { status: 404 })));
    renderWithQuery(<CompanyResearch ticker="ZZZZ" />);
    expect(await screen.findByRole("heading", { name: "Unknown ticker ZZZZ" })).toBeInTheDocument();
  });
});
