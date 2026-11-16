import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { EtfHub } from "@/components/etf/EtfHub";
import { DEFAULT_STATE, parseParams, serializeParams, toStocksQuery } from "@/components/screener/params";
import type { EtfTile } from "@/lib/api";

import { mockFetch, NICHES, renderWithQuery, stock } from "./helpers";

const replace = vi.fn();
let search = "";
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, push: vi.fn() }),
  usePathname: () => "/etfs",
  useSearchParams: () => new URLSearchParams(search),
}));

function etfTile(overrides: Partial<EtfTile> = {}): EtfTile {
  return {
    ...stock({ ticker: "AIS", name: "VistaShares AI", asset_type: "etf" }),
    aum: 1e9,
    size: 1e9,
    return_pct: 2.5,
    ...overrides,
  };
}

describe("screener ETFs browse mode", () => {
  it("round-trips browse=etfs and forces asset_type=etf", () => {
    const state = { ...DEFAULT_STATE, browse: "etfs" as const, niche: "ai", type: "etf" as const };
    const qs = serializeParams(state);
    expect(qs).toContain("browse=etfs");
    expect(parseParams(new URLSearchParams(qs)).browse).toBe("etfs");
    expect(toStocksQuery(state, 50)).toMatchObject({ asset_type: "etf", niche: "ai", sector: undefined });
  });
});

describe("EtfHub", () => {
  beforeEach(() => {
    replace.mockReset();
    search = "";
  });

  it("renders niche ETF map rows and period chips", async () => {
    const tile = etfTile();
    mockFetch({
      "/api/niches": NICHES,
      "/api/etfs": {
        period: "wow",
        groups: [{ slug: "ai", name: "AI", etfs: [tile] }],
        etfs: [tile],
      },
    });
    renderWithQuery(<EtfHub mode="niches" />);
    expect(await screen.findByRole("heading", { name: "Niche ETFs" })).toBeInTheDocument();
    expect(await screen.findByRole("link", { name: "AIS" })).toHaveAttribute("href", "/company/AIS");
    expect(screen.getByRole("button", { name: "Refresh" })).toBeEnabled();
    fireEvent.click(screen.getByRole("button", { name: "MoM" }));
    await waitFor(() => expect(replace).toHaveBeenCalled());
  });

  it("ignores invalid period query params", async () => {
    search = "period=nope";
    const tile = etfTile({ size: 50, aum: 1 });
    mockFetch({
      "/api/niches": NICHES,
      "/api/etfs": {
        period: "wow",
        groups: [{ slug: "ai", name: "AI", etfs: [tile] }],
        etfs: [tile],
      },
    });
    renderWithQuery(<EtfHub mode="niches" />);
    expect(await screen.findByRole("heading", { name: "Niche ETFs" })).toBeInTheDocument();
    await waitFor(() => {
      const calls = (global.fetch as ReturnType<typeof vi.fn>).mock.calls.map((c) => String(c[0]));
      expect(calls.some((u) => u.includes("/api/etfs") && !u.includes("period=nope"))).toBe(true);
    });
  });
});
