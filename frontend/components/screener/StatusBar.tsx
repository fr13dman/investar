"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCwIcon } from "lucide-react";
import { useEffect, useRef } from "react";

import { ChangeValue } from "@/components/market/ChangeValue";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { formatDateTime, formatPrice } from "@/lib/format";
import { cn } from "@/lib/utils";

export function StatusBar() {
  const qc = useQueryClient();
  const status = useQuery({
    queryKey: ["status"],
    queryFn: api.status,
    refetchInterval: (q) => (q.state.data?.refreshing.prices ? 3_000 : 60_000),
  });
  const benchmarks = useQuery({ queryKey: ["benchmarks"], queryFn: api.benchmarks, refetchInterval: 60_000 });
  const refresh = useMutation({
    mutationFn: () => api.refresh("prices"),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["status"] }),
  });

  const refreshing = Boolean(status.data?.refreshing.prices);
  const wasRefreshing = useRef(false);
  useEffect(() => {
    if (wasRefreshing.current && !refreshing) {
      for (const key of ["stocks", "movers", "benchmarks", "sectors"]) qc.invalidateQueries({ queryKey: [key] });
    }
    wasRefreshing.current = refreshing;
  }, [refreshing, qc]);

  const last = status.data?.jobs.prices_intraday ?? status.data?.jobs.prices_backfill;
  return (
    <div className="flex flex-wrap items-center gap-4 text-sm">
      {(benchmarks.data ?? []).map((b) => (
        <div key={b.ticker} className="flex items-center gap-2 rounded-lg border border-border px-3 py-1.5">
          <span className="font-semibold">{b.ticker}</span>
          <span className="tabular-nums">{formatPrice(b.price)}</span>
          <ChangeValue value={b.chg_1d_pct} />
          <span className="text-xs text-muted-foreground">YTD</span>
          <ChangeValue value={b.chg_ytd_pct} />
        </div>
      ))}
      <div className="ml-auto flex items-center gap-3 text-muted-foreground">
        <span className="flex items-center gap-1.5">
          <span
            className={cn("size-2 rounded-full", status.data?.market_open ? "bg-emerald-400" : "bg-muted-foreground")}
          />
          {status.data?.market_open ? "Market open" : "Market closed"}
        </span>
        <span>Updated {formatDateTime(last?.fetched_at)}</span>
        <Button variant="outline" size="sm" onClick={() => refresh.mutate()} disabled={refreshing}>
          <RefreshCwIcon className={cn(refreshing && "animate-spin")} />
          {refreshing ? "Refreshing" : "Refresh now"}
        </Button>
      </div>
    </div>
  );
}
