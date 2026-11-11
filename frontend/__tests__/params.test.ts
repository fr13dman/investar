import { describe, expect, it } from "vitest";

import { DEFAULT_STATE, nextSort, parseParams, serializeParams, toStocksQuery } from "@/components/screener/params";
import { toQueryString } from "@/lib/api";

describe("screener URL state", () => {
  it("parses defaults from an empty query", () => {
    expect(parseParams(new URLSearchParams())).toEqual({ ...DEFAULT_STATE, sector: undefined, industry: undefined, cap: undefined, q: undefined, wl: undefined });
  });

  it("round-trips non-default values and drops defaults", () => {
    const state = { ...DEFAULT_STATE, sector: "Technology", industry: "Semiconductors", sort: "chg_ytd" as const, order: "asc" as const, mode: "abs" as const, page: 2, cap: "mega" as const };
    const qs = serializeParams(state);
    expect(qs).toBe("sector=Technology&industry=Semiconductors&cap=mega&sort=chg_ytd&order=asc&mode=abs&page=2");
    expect(parseParams(new URLSearchParams(qs))).toMatchObject(state);
    expect(serializeParams(DEFAULT_STATE)).toBe("");
  });

  it("ignores invalid values", () => {
    const s = parseParams(new URLSearchParams("sort=evil&index=nope&page=-3&cap=giant&wl=abc"));
    expect(s.sort).toBe("market_cap");
    expect(s.index).toBe("all");
    expect(s.page).toBe(1);
    expect(s.cap).toBeUndefined();
    expect(s.wl).toBeUndefined();
  });

  it("toggles sort direction and resets the page", () => {
    const s = { ...DEFAULT_STATE, page: 4 };
    expect(nextSort(s, "market_cap")).toEqual({ sort: "market_cap", order: "asc", page: 1 });
    expect(nextSort(s, "chg_1d")).toEqual({ sort: "chg_1d", order: "desc", page: 1 });
    expect(nextSort(s, "ticker")).toEqual({ sort: "ticker", order: "asc", page: 1 });
  });

  it("builds the API query string", () => {
    const q = toStocksQuery({ ...DEFAULT_STATE, sector: "Energy", wl: 3 }, 50);
    expect(toQueryString(q)).toBe("?sector=Energy&index=all&watchlist_id=3&sort=market_cap&order=desc&mode=pct&page=1&page_size=50");
  });
});
