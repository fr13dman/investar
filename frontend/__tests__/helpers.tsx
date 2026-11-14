import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { vi } from "vitest";

import type { NicheNode, StockRow } from "@/lib/api";

export function renderWithQuery(ui: React.ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

export function stock(overrides: Partial<StockRow> = {}): StockRow {
  return {
    ticker: "AAPL",
    name: "Apple Inc.",
    sector: "Technology",
    industry: "Consumer Electronics",
    asset_type: "stock",
    extra_source: null,
    in_sp500: true,
    in_ndx100: true,
    price: 200,
    market_cap: 3.1e12,
    volume: 5.2e7,
    pe_ratio: 31.2,
    week52_high: 230,
    week52_low: 160,
    chg_1d_pct: 1.25,
    chg_1d_abs: 2.47,
    chg_1w_pct: -0.5,
    chg_1w_abs: -1,
    chg_ytd_pct: 12.3,
    chg_ytd_abs: 21.9,
    sparkline: [195, 197, 196, 199, 200],
    as_of: "2026-11-10T15:00:00",
    ...overrides,
  };
}

/** Route fetch(url) calls to handlers keyed by path prefix. */
export function mockFetch(routes: Record<string, unknown | ((url: string, init?: RequestInit) => unknown)>) {
  const spy = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const key = Object.keys(routes)
      .sort((a, b) => b.length - a.length)
      .find((k) => url.startsWith(k));
    if (!key) return new Response(JSON.stringify({ detail: "not mocked" }), { status: 404 });
    const value = routes[key];
    const body = typeof value === "function" ? (value as (u: string, i?: RequestInit) => unknown)(url, init) : value;
    return new Response(JSON.stringify(body), { status: 200, headers: { "Content-Type": "application/json" } });
  });
  vi.stubGlobal("fetch", spy);
  return spy;
}

export const NICHES: NicheNode[] = [
  {
    id: 1,
    slug: "ai",
    name: "AI",
    description: "Artificial intelligence",
    count: 7,
    children: [
      { id: 2, slug: "hyperscalers", name: "Hyperscalers", description: null, count: 3 },
      { id: 3, slug: "neoclouds", name: "Neoclouds", description: "GPU clouds", count: 1 },
    ],
  },
  {
    id: 4,
    slug: "energy-transition",
    name: "Energy Transition",
    description: null,
    count: 2,
    children: [{ id: 5, slug: "small-modular-reactors", name: "Small Modular Reactors", description: null, count: 1 }],
  },
];
