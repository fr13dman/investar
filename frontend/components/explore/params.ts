import { ASSET_FILTERS, CAPS, INDEXES, pick, WINDOWS } from "@/components/screener/params";
import type { AssetFilter, CapBand, IndexFilter, SortKey, StocksQuery, SwingWindow } from "@/lib/api";

export interface ExploreState {
  niche?: string;
  sub?: string;
  type: AssetFilter;
  cap?: CapBand;
  index: IndexFilter;
  window: SwingWindow;
  /** Percent bounds for `window`; gainers-only raises the floor to 0. */
  min?: number;
  max?: number;
  gainers: boolean;
  q?: string;
  sort: SortKey;
  order: "asc" | "desc";
  page: number;
}

export const EXPLORE_DEFAULTS: ExploreState = {
  type: "all",
  index: "all",
  window: "chg_ytd",
  gainers: false,
  sort: "market_cap",
  order: "desc",
  page: 1,
};

const SORTS: SortKey[] = ["ticker", "name", "price", "market_cap", "volume", "pe_ratio", "chg_1d", "chg_1w", "chg_ytd"];

function num(v: string | null): number | undefined {
  if (v === null || v.trim() === "") return undefined;
  const n = Number(v);
  return Number.isFinite(n) ? n : undefined;
}

export function parseExplore(sp: URLSearchParams): ExploreState {
  const page = Number(sp.get("page"));
  const cap = sp.get("cap");
  return {
    niche: sp.get("niche") || undefined,
    sub: sp.get("sub") || undefined,
    type: pick(sp.get("type"), ASSET_FILTERS, EXPLORE_DEFAULTS.type),
    cap: cap && (CAPS as string[]).includes(cap) ? (cap as CapBand) : undefined,
    index: pick(sp.get("index"), INDEXES, EXPLORE_DEFAULTS.index),
    window: pick(sp.get("window"), WINDOWS, EXPLORE_DEFAULTS.window),
    min: num(sp.get("min")),
    max: num(sp.get("max")),
    gainers: sp.get("gainers") === "1",
    q: sp.get("q") || undefined,
    sort: pick(sp.get("sort"), SORTS, EXPLORE_DEFAULTS.sort),
    order: sp.get("order") === "asc" ? "asc" : "desc",
    page: Number.isInteger(page) && page > 0 ? page : 1,
  };
}

export function serializeExplore(s: ExploreState): string {
  const sp = new URLSearchParams();
  const entries: [string, string | number | undefined][] = [
    ["niche", s.niche],
    ["sub", s.sub],
    ["type", s.type !== EXPLORE_DEFAULTS.type ? s.type : undefined],
    ["cap", s.cap],
    ["index", s.index !== EXPLORE_DEFAULTS.index ? s.index : undefined],
    ["window", s.window !== EXPLORE_DEFAULTS.window ? s.window : undefined],
    ["min", s.min],
    ["max", s.max],
    ["gainers", s.gainers ? 1 : undefined],
    ["q", s.q],
    ["sort", s.sort !== EXPLORE_DEFAULTS.sort ? s.sort : undefined],
    ["order", s.order !== EXPLORE_DEFAULTS.order ? s.order : undefined],
    ["page", s.page > 1 ? s.page : undefined],
  ];
  for (const [k, v] of entries) if (v !== undefined && v !== "") sp.set(k, String(v));
  return sp.toString();
}

export function toExploreQuery(s: ExploreState, pageSize: number): StocksQuery {
  const min = s.gainers ? Math.max(s.min ?? 0, 0) : s.min;
  const ranged = min !== undefined || s.max !== undefined;
  return {
    niche: s.sub ?? s.niche,
    asset_type: s.type !== "all" ? s.type : undefined,
    cap_band: s.cap,
    index: s.index,
    q: s.q,
    chg_window: ranged ? s.window : undefined,
    chg_min: min,
    chg_max: s.max,
    sort: s.sort,
    order: s.order,
    mode: "pct",
    page: s.page,
    page_size: pageSize,
  };
}
