"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { selectClass } from "@/components/screener/FilterBar";
import { nextSort } from "@/components/screener/params";
import { StocksTable } from "@/components/screener/StocksTable";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api, type AssetFilter, type CapBand, type IndexFilter, type SwingWindow } from "@/lib/api";

import { MarketSearch } from "./MarketSearch";
import { parseExplore, serializeExplore, toExploreQuery, type ExploreState } from "./params";

const PAGE_SIZE = 50;
const WINDOW_LABEL: Record<SwingWindow, string> = { chg_1d: "1 day", chg_1w: "1 week", chg_ytd: "Year to date" };

/** Text/number input that commits to the URL after a pause instead of on every keystroke. */
function useCommitted(value: string, commit: (v: string) => void) {
  const [draft, setDraft] = useState(value);
  const [synced, setSynced] = useState(value);
  if (value !== synced) {
    setSynced(value);
    setDraft(value);
  }
  useEffect(() => {
    if (draft === value) return;
    const t = setTimeout(() => commit(draft), 400);
    return () => clearTimeout(t);
  }, [draft, value, commit]);
  return [draft, setDraft] as const;
}

function PercentInput({ label, value, onCommit }: { label: string; value?: number; onCommit: (v?: number) => void }) {
  const commit = useCallback(
    (v: string) => onCommit(v.trim() === "" || !Number.isFinite(Number(v)) ? undefined : Number(v)),
    [onCommit],
  );
  const [draft, setDraft] = useCommitted(value === undefined ? "" : String(value), commit);
  return (
    <label className="flex items-center gap-2 text-sm text-muted-foreground">
      {label}
      <Input
        aria-label={label}
        type="number"
        inputMode="decimal"
        step="any"
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        className="w-20"
      />
      %
    </label>
  );
}

export function Explore() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const state = useMemo(() => parseExplore(new URLSearchParams(searchParams.toString())), [searchParams]);
  const update = useCallback(
    (patch: Partial<ExploreState>) => {
      const qs = serializeExplore({ ...state, page: 1, ...patch });
      router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    },
    [state, router, pathname],
  );
  const commitQ = useCallback((v: string) => update({ q: v.trim() || undefined }), [update]);
  const [search, setSearch] = useCommitted(state.q ?? "", commitQ);

  const niches = useQuery({ queryKey: ["niches"], queryFn: api.niches });
  const watchlists = useQuery({ queryKey: ["watchlists"], queryFn: api.watchlists });
  const query = toExploreQuery(state, PAGE_SIZE);
  const stocks = useQuery({ queryKey: ["stocks", query], queryFn: () => api.stocks(query), placeholderData: keepPreviousData });
  const parent = niches.data?.find((n) => n.slug === state.niche);
  const total = stocks.data?.total ?? 0;
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Explore niches</h1>
        <p className="text-sm text-muted-foreground">
          Filter stocks and ETFs by niche sector, size and recent gains, or search the whole market and add new symbols
          to the screener.
        </p>
      </div>

      <section aria-label="Explore filters" className="flex flex-wrap items-center gap-3">
        <label className="flex items-center gap-2 text-sm text-muted-foreground">
          Niche
          <select
            aria-label="Niche"
            className={selectClass}
            value={state.niche ?? ""}
            onChange={(e) => update({ niche: e.target.value || undefined, sub: undefined })}
          >
            <option value="">Any niche</option>
            {(niches.data ?? []).map((n) => (
              <option key={n.slug} value={n.slug}>
                {n.name} ({n.count})
              </option>
            ))}
          </select>
        </label>
        <label className="flex items-center gap-2 text-sm text-muted-foreground">
          Sub-niche
          <select
            aria-label="Sub-niche"
            className={selectClass}
            value={state.sub ?? ""}
            disabled={!parent}
            onChange={(e) => update({ sub: e.target.value || undefined })}
          >
            <option value="">{parent ? `All ${parent.name}` : "Pick a niche first"}</option>
            {(parent?.children ?? []).map((c) => (
              <option key={c.slug} value={c.slug}>
                {c.name} ({c.count})
              </option>
            ))}
          </select>
        </label>
        <label className="flex items-center gap-2 text-sm text-muted-foreground">
          Type
          <select
            aria-label="Asset type"
            className={selectClass}
            value={state.type}
            onChange={(e) => update({ type: e.target.value as AssetFilter })}
          >
            <option value="all">Stocks + ETFs</option>
            <option value="stock">Stocks</option>
            <option value="etf">ETFs</option>
          </select>
        </label>
        <label className="flex items-center gap-2 text-sm text-muted-foreground">
          Market cap
          <select
            aria-label="Market cap"
            className={selectClass}
            value={state.cap ?? ""}
            onChange={(e) => update({ cap: (e.target.value || undefined) as CapBand | undefined })}
          >
            <option value="">Any</option>
            <option value="mega">Mega (200B+)</option>
            <option value="large">Large (10B-200B)</option>
            <option value="mid">Mid (2B-10B)</option>
            <option value="small">Small (under 2B)</option>
          </select>
        </label>
        <label className="flex items-center gap-2 text-sm text-muted-foreground">
          Index
          <select
            aria-label="Index"
            className={selectClass}
            value={state.index}
            onChange={(e) => update({ index: e.target.value as IndexFilter })}
          >
            <option value="all">All tracked</option>
            <option value="sp500">S&amp;P 500</option>
            <option value="ndx100">Nasdaq-100</option>
            <option value="both">In both</option>
            <option value="other">Not in an index</option>
          </select>
        </label>
      </section>

      <section aria-label="Gain filters" className="flex flex-wrap items-center gap-3">
        <label className="flex items-center gap-2 text-sm text-muted-foreground">
          Change over
          <select
            aria-label="Change window"
            className={selectClass}
            value={state.window}
            onChange={(e) => update({ window: e.target.value as SwingWindow })}
          >
            {(Object.keys(WINDOW_LABEL) as SwingWindow[]).map((w) => (
              <option key={w} value={w}>
                {WINDOW_LABEL[w]}
              </option>
            ))}
          </select>
        </label>
        <PercentInput label="Min change" value={state.min} onCommit={(min) => update({ min })} />
        <PercentInput label="Max change" value={state.max} onCommit={(max) => update({ max })} />
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={state.gainers}
            onChange={(e) => update({ gainers: e.target.checked })}
            className="size-3.5 accent-primary"
          />
          Gainers only
        </label>
        <Input
          aria-label="Filter by ticker or name"
          placeholder="Ticker or name"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-48"
        />
        <Button variant="ghost" size="sm" onClick={() => router.replace(pathname, { scroll: false })}>
          Reset filters
        </Button>
      </section>

      {stocks.isError && (
        <p role="alert" className="text-sm text-rose-600 dark:text-rose-400">
          Could not load results. Is the API running on port 8010?
        </p>
      )}
      <StocksTable
        rows={stocks.data?.items}
        mode="pct"
        sort={state.sort}
        order={state.order}
        watchlists={watchlists.data ?? []}
        loading={stocks.isFetching}
        onSort={(key) => update(nextSort(state, key))}
      />
      <div className="flex items-center justify-between text-sm text-muted-foreground">
        <span>
          {total} {total === 1 ? "result" : "results"}
        </span>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" disabled={state.page <= 1} onClick={() => update({ page: state.page - 1 })}>
            Previous
          </Button>
          <span>
            Page {Math.min(state.page, pages)} of {pages}
          </span>
          <Button variant="outline" size="sm" disabled={state.page >= pages} onClick={() => update({ page: state.page + 1 })}>
            Next
          </Button>
        </div>
      </div>

      <MarketSearch niches={niches.data ?? []} />
    </div>
  );
}
