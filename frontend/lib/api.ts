export type IndexFilter = "all" | "sp500" | "ndx100" | "both";
export type CapBand = "mega" | "large" | "mid" | "small";
export type SwingWindow = "chg_1d" | "chg_1w" | "chg_ytd";
export type ChangeMode = "pct" | "abs";
export type SortKey =
  | "ticker"
  | "name"
  | "sector"
  | "industry"
  | "price"
  | "market_cap"
  | "volume"
  | "pe_ratio"
  | SwingWindow;

export interface StockRow {
  ticker: string;
  name: string;
  sector: string | null;
  industry: string | null;
  in_sp500: boolean;
  in_ndx100: boolean;
  price: number | null;
  market_cap: number | null;
  volume: number | null;
  pe_ratio: number | null;
  week52_high: number | null;
  week52_low: number | null;
  chg_1d_pct: number | null;
  chg_1d_abs: number | null;
  chg_1w_pct: number | null;
  chg_1w_abs: number | null;
  chg_ytd_pct: number | null;
  chg_ytd_abs: number | null;
  sparkline: number[] | null;
  as_of: string | null;
}

export interface StocksPage {
  total: number;
  page: number;
  page_size: number;
  items: StockRow[];
}

export interface SectorNode {
  sector: string;
  count: number;
  industries: { industry: string; count: number }[];
}

export interface Movers {
  window: SwingWindow;
  mode: ChangeMode;
  gainers: StockRow[];
  losers: StockRow[];
}

export interface Watchlist {
  id: number;
  name: string;
  tickers: string[];
}

export interface JobStatus {
  fetched_at: string;
  status: string;
  message: string | null;
  refreshing: boolean;
}

export interface AppStatus {
  market_open: boolean;
  companies: number;
  price_rows: number;
  jobs: Record<string, JobStatus>;
  refreshing: Record<string, boolean>;
}

export interface RefreshStatus {
  fetched_at: string | null;
  status: string | null;
  message: string | null;
  refreshing: boolean;
}

export interface Executive {
  name: string;
  title: string | null;
  total_pay: number | null;
  is_ceo: boolean;
}

export interface CompanyProfile extends StockRow {
  cik: string | null;
  exchange: string | null;
  gics_sector: string | null;
  gics_sub_industry: string | null;
  website: string | null;
  description: string | null;
  headquarters: string | null;
  country: string | null;
  employees: number | null;
  founded: string | null;
  is_benchmark: boolean;
  quote: { price: number; prev_close: number | null; source: string; as_of: string } | null;
  executives: Executive[];
  refresh: RefreshStatus;
}

export interface LiveQuote {
  ticker: string;
  source: "finnhub" | "stored";
  price: number | null;
  chg_1d_pct: number | null;
  chg_1d_abs: number | null;
  as_of: string | null;
}

export type PriceRange = "1d" | "1w" | "1m" | "ytd" | "1y" | "5y";

export interface PriceBar {
  time: string | number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number | null;
}

export interface PriceSeries {
  ticker: string;
  range: PriceRange;
  interval: string;
  bars: PriceBar[];
  benchmark: { ticker: string; bars: PriceBar[] };
}

export interface FundamentalsRow {
  fiscal_year_end: string;
  revenue: number | null;
  eps: number | null;
  net_income: number | null;
  net_margin_pct: number | null;
}

export interface PayVsPerformanceRow {
  fiscal_year_end: string;
  peo_total_comp?: number;
  peo_comp_actually_paid?: number;
  tsr_value?: number;
  peer_tsr_value?: number;
  net_income?: number;
  peo_names?: string[];
}

export interface CeoScorecard {
  ceo_name: string | null;
  tenure_start: string | null;
  tenure_source: string | null;
  window_start: string | null;
  window_truncated: boolean;
  tsr_pct: number | null;
  spy_tsr_pct: number | null;
  excess_return_pct: number | null;
  tsr_annualized_pct: number | null;
  spy_annualized_pct: number | null;
  revenue_cagr_pct: number | null;
  eps_cagr_pct: number | null;
  margin_start_pct: number | null;
  margin_end_pct: number | null;
  fundamentals: FundamentalsRow[];
  pay_vs_performance: PayVsPerformanceRow[];
  tenures: { name: string; start: string | null; end: string | null }[];
  computed_at: string | null;
}

export interface NewsItem {
  headline: string;
  summary: string | null;
  source: string | null;
  url: string;
  image: string | null;
  published_at: string;
  sentiment: { label: "positive" | "neutral" | "negative" | null; score: number | null; model: string | null };
}

export interface NewsResponse {
  items: NewsItem[];
  summary: { positive: number; neutral: number; negative: number; average_score: number | null };
  refresh: RefreshStatus;
  configured: boolean;
}

export interface GlobalPresence {
  subsidiaries: { name: string; jurisdiction: string | null; country_name: string | null; country_alpha2: string | null }[];
  countries: { country_name: string; alpha2: string; numeric: string; count: number }[];
  unmapped: number;
  revenue_by_region: {
    axis: "geographic" | "segment";
    period_end: string;
    total: number | null;
    regions: { region: string; member: string; revenue: number; country_alpha2: string | null; share_pct: number | null }[];
  }[];
  filing: { accession: string | null; url: string | null };
  refresh: RefreshStatus;
}

export interface PatentItem {
  number: string;
  title: string | null;
  abstract: string | null;
  date: string | null;
  cpc_class: string | null;
  cpc_title: string | null;
  assignee: string | null;
  url: string;
  source: string;
}

export interface CpcBreakdown {
  items: { code: string; title: string; count: number }[];
  note: string | null;
}

export interface PatentAssignee {
  assignee_name: string;
  match: "exact" | "prefix";
  source?: string;
}

export interface Patents {
  granted: { total_10y: number | null; by_year: { year: string; count: number }[]; top_cpc: CpcBreakdown; recent: PatentItem[] };
  applications: { total_24m: number | null; top_cpc: CpcBreakdown; recent: PatentItem[] };
  assignees: PatentAssignee[];
  source: string | null;
  refresh: RefreshStatus;
}

export interface StocksQuery {
  sector?: string;
  industry?: string;
  index?: IndexFilter;
  cap_band?: CapBand;
  q?: string;
  watchlist_id?: number;
  sort?: SortKey;
  order?: "asc" | "desc";
  mode?: ChangeMode;
  page?: number;
  page_size?: number;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

export function toQueryString(params: object): string {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === "") continue;
    qs.set(k, String(v));
  }
  const s = qs.toString();
  return s ? `?${s}` : "";
}

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  sectors: () => request<SectorNode[]>("/api/sectors"),
  stocks: (q: StocksQuery) => request<StocksPage>(`/api/stocks${toQueryString(q)}`),
  movers: (q: { sector?: string; industry?: string; window?: SwingWindow; mode?: ChangeMode; limit?: number }) =>
    request<Movers>(`/api/movers${toQueryString(q)}`),
  benchmarks: () => request<StockRow[]>("/api/benchmarks"),
  status: () => request<AppStatus>("/api/status"),
  refresh: (scope: "prices" | "backfill" | "profiles" | "universe") =>
    request<{ started: boolean }>("/api/refresh", { method: "POST", body: JSON.stringify({ scope }) }),
  watchlists: () => request<Watchlist[]>("/api/watchlists"),
  createWatchlist: (name: string) =>
    request<Watchlist>("/api/watchlists", { method: "POST", body: JSON.stringify({ name }) }),
  renameWatchlist: (id: number, name: string) =>
    request<Watchlist>(`/api/watchlists/${id}`, { method: "PUT", body: JSON.stringify({ name }) }),
  deleteWatchlist: (id: number) => request<void>(`/api/watchlists/${id}`, { method: "DELETE" }),
  addToWatchlist: (id: number, ticker: string) =>
    request<Watchlist>(`/api/watchlists/${id}/items`, { method: "POST", body: JSON.stringify({ ticker }) }),
  removeFromWatchlist: (id: number, ticker: string) =>
    request<Watchlist>(`/api/watchlists/${id}/items/${encodeURIComponent(ticker)}`, { method: "DELETE" }),
  company: (ticker: string) => request<CompanyProfile>(`/api/companies/${encodeURIComponent(ticker)}`),
  quote: (ticker: string) => request<LiveQuote>(`/api/companies/${encodeURIComponent(ticker)}/quote`),
  prices: (ticker: string, range: PriceRange) =>
    request<PriceSeries>(`/api/companies/${encodeURIComponent(ticker)}/prices?range=${range}`),
  news: (ticker: string, force = false) =>
    request<NewsResponse>(`/api/companies/${encodeURIComponent(ticker)}/news${force ? "?force=true" : ""}`),
  ceo: (ticker: string, force = false) =>
    request<{ scorecard: CeoScorecard | null; refresh: RefreshStatus }>(
      `/api/companies/${encodeURIComponent(ticker)}/ceo${force ? "?force=true" : ""}`,
    ),
  globalPresence: (ticker: string, force = false) =>
    request<GlobalPresence>(`/api/companies/${encodeURIComponent(ticker)}/global${force ? "?force=true" : ""}`),
  patents: (ticker: string, force = false) =>
    request<Patents>(`/api/companies/${encodeURIComponent(ticker)}/patents${force ? "?force=true" : ""}`),
  setPatentAssignees: (ticker: string, assignees: PatentAssignee[]) =>
    request<{ assignees: PatentAssignee[]; refresh: RefreshStatus }>(
      `/api/companies/${encodeURIComponent(ticker)}/patent-assignees`,
      { method: "PUT", body: JSON.stringify(assignees.map(({ assignee_name, match }) => ({ assignee_name, match }))) },
    ),
  setCeoOverride: (ticker: string, body: { ceo_name?: string | null; tenure_start?: string | null }) =>
    request<{ scorecard: CeoScorecard }>(`/api/companies/${encodeURIComponent(ticker)}/ceo`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
};
