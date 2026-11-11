"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useMemo } from "react";

import { Button } from "@/components/ui/button";
import { api, type SortKey } from "@/lib/api";

import { FilterBar } from "./FilterBar";
import { MoversPanel } from "./MoversPanel";
import { nextSort, parseParams, serializeParams, toStocksQuery, type ScreenerState } from "./params";
import { SectorPicker } from "./SectorPicker";
import { StatusBar } from "./StatusBar";
import { StocksTable } from "./StocksTable";

const PAGE_SIZE = 50;

export function Screener() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const state = useMemo(() => parseParams(new URLSearchParams(searchParams.toString())), [searchParams]);

  const update = useCallback(
    (patch: Partial<ScreenerState>) => {
      const next = { ...state, ...patch };
      const qs = serializeParams(next);
      router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    },
    [state, router, pathname],
  );

  const sectors = useQuery({ queryKey: ["sectors"], queryFn: api.sectors });
  const watchlists = useQuery({ queryKey: ["watchlists"], queryFn: api.watchlists });
  const query = toStocksQuery(state, PAGE_SIZE);
  const stocks = useQuery({
    queryKey: ["stocks", query],
    queryFn: () => api.stocks(query),
    placeholderData: keepPreviousData,
    refetchInterval: 5 * 60_000,
  });

  const total = stocks.data?.total ?? 0;
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Stock screener</h1>
        <p className="text-sm text-muted-foreground">
          S&amp;P 500 and Nasdaq-100 companies. Pick a sector and industry, then sort by size or by the biggest moves
          over the last trading day, week or year to date.
        </p>
      </div>
      <StatusBar />
      <SectorPicker
        sectors={sectors.data ?? []}
        sector={state.sector}
        industry={state.industry}
        onChange={({ sector, industry }) => update({ sector, industry, page: 1 })}
      />
      <MoversPanel
        sector={state.sector}
        industry={state.industry}
        window={state.window}
        mode={state.mode}
        onWindowChange={(window) => update({ window })}
      />
      <FilterBar
        index={state.index}
        cap={state.cap}
        q={state.q}
        mode={state.mode}
        wl={state.wl}
        watchlists={watchlists.data ?? []}
        onChange={(patch) => update({ ...patch, page: 1 })}
      />
      {stocks.isError && (
        <p role="alert" className="text-sm text-rose-400">
          Could not load stocks. Is the API running on port 8010?
        </p>
      )}
      <StocksTable
        rows={stocks.data?.items}
        mode={state.mode}
        sort={state.sort}
        order={state.order}
        watchlists={watchlists.data ?? []}
        loading={stocks.isFetching}
        onSort={(key: SortKey) => update(nextSort(state, key))}
      />
      <div className="flex items-center justify-between text-sm text-muted-foreground">
        <span>
          {total} {total === 1 ? "stock" : "stocks"}
        </span>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" disabled={state.page <= 1} onClick={() => update({ page: state.page - 1 })}>
            Previous
          </Button>
          <span>
            Page {Math.min(state.page, pages)} of {pages}
          </span>
          <Button
            variant="outline"
            size="sm"
            disabled={state.page >= pages}
            onClick={() => update({ page: state.page + 1 })}
          >
            Next
          </Button>
        </div>
      </div>
    </div>
  );
}
