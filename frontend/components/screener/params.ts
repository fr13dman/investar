import type { CapBand, ChangeMode, IndexFilter, SortKey, StocksQuery, SwingWindow } from "@/lib/api";

export interface ScreenerState {
  sector?: string;
  industry?: string;
  index: IndexFilter;
  cap?: CapBand;
  q?: string;
  wl?: number;
  sort: SortKey;
  order: "asc" | "desc";
  mode: ChangeMode;
  window: SwingWindow;
  page: number;
}

export const DEFAULT_STATE: ScreenerState = {
  index: "all",
  sort: "market_cap",
  order: "desc",
  mode: "pct",
  window: "chg_1d",
  page: 1,
};

const SORTS: SortKey[] = [
  "ticker",
  "name",
  "sector",
  "industry",
  "price",
  "market_cap",
  "volume",
  "pe_ratio",
  "chg_1d",
  "chg_1w",
  "chg_ytd",
];
const INDEXES: IndexFilter[] = ["all", "sp500", "ndx100", "both"];
const CAPS: CapBand[] = ["mega", "large", "mid", "small"];
const WINDOWS: SwingWindow[] = ["chg_1d", "chg_1w", "chg_ytd"];

function pick<T extends string>(value: string | null, allowed: readonly T[], fallback: T): T {
  return value && (allowed as readonly string[]).includes(value) ? (value as T) : fallback;
}

export function parseParams(sp: URLSearchParams): ScreenerState {
  const page = Number(sp.get("page"));
  const wl = Number(sp.get("wl"));
  const cap = sp.get("cap");
  return {
    sector: sp.get("sector") || undefined,
    industry: sp.get("industry") || undefined,
    index: pick(sp.get("index"), INDEXES, DEFAULT_STATE.index),
    cap: cap && (CAPS as string[]).includes(cap) ? (cap as CapBand) : undefined,
    q: sp.get("q") || undefined,
    wl: Number.isInteger(wl) && wl > 0 ? wl : undefined,
    sort: pick(sp.get("sort"), SORTS, DEFAULT_STATE.sort),
    order: sp.get("order") === "asc" ? "asc" : "desc",
    mode: sp.get("mode") === "abs" ? "abs" : "pct",
    window: pick(sp.get("window"), WINDOWS, DEFAULT_STATE.window),
    page: Number.isInteger(page) && page > 0 ? page : 1,
  };
}

export function serializeParams(state: ScreenerState): string {
  const sp = new URLSearchParams();
  const entries: [string, string | number | undefined][] = [
    ["sector", state.sector],
    ["industry", state.industry],
    ["index", state.index !== DEFAULT_STATE.index ? state.index : undefined],
    ["cap", state.cap],
    ["q", state.q],
    ["wl", state.wl],
    ["sort", state.sort !== DEFAULT_STATE.sort ? state.sort : undefined],
    ["order", state.order !== DEFAULT_STATE.order ? state.order : undefined],
    ["mode", state.mode !== DEFAULT_STATE.mode ? state.mode : undefined],
    ["window", state.window !== DEFAULT_STATE.window ? state.window : undefined],
    ["page", state.page > 1 ? state.page : undefined],
  ];
  for (const [k, v] of entries) if (v !== undefined && v !== "") sp.set(k, String(v));
  return sp.toString();
}

export function toStocksQuery(state: ScreenerState, pageSize: number): StocksQuery {
  return {
    sector: state.sector,
    industry: state.industry,
    index: state.index,
    cap_band: state.cap,
    q: state.q,
    watchlist_id: state.wl,
    sort: state.sort,
    order: state.order,
    mode: state.mode,
    page: state.page,
    page_size: pageSize,
  };
}

/** Clicking the active column flips direction; a new column starts descending (ascending for text). */
export function nextSort(state: ScreenerState, key: SortKey): Pick<ScreenerState, "sort" | "order" | "page"> {
  if (state.sort === key) return { sort: key, order: state.order === "desc" ? "asc" : "desc", page: 1 };
  const textual = key === "ticker" || key === "name" || key === "sector" || key === "industry";
  return { sort: key, order: textual ? "asc" : "desc", page: 1 };
}
