"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { api, type HeatmapPeriod } from "@/lib/api";

import { PeriodToggle } from "./PeriodToggle";
import { AllocationTreemap } from "./Treemap";

export function HoldingsHeatmap({ ticker }: { ticker: string }) {
  const [period, setPeriod] = useState<HeatmapPeriod>("wow");
  const router = useRouter();
  const qc = useQueryClient();
  const heatmap = useQuery({
    queryKey: ["etf-heatmap", ticker, period],
    queryFn: () => api.etfHeatmap(ticker, period),
  });
  const refresh = useMutation({
    mutationFn: () => api.refreshEtf(ticker),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["etf-heatmap", ticker] });
      void qc.invalidateQueries({ queryKey: ["company", ticker] });
    },
  });

  const nodes = heatmap.data?.nodes ?? [];
  const data = nodes.map((n) => ({
    name: n.name || n.id,
    ticker: n.ticker,
    size: n.weight_pct,
    return_pct: n.return_pct,
    kind: n.kind,
    navigable: n.navigable,
  }));

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-sm font-semibold">Holdings allocation</h2>
          <p className="text-xs text-muted-foreground">
            Top 25 equities by weight; remainder and overlays in Other.
            {heatmap.data?.as_of ? ` As of ${heatmap.data.as_of}.` : ""}
            {heatmap.data?.source ? ` Source: ${heatmap.data.source}.` : ""}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <PeriodToggle value={period} onChange={setPeriod} />
          <Button type="button" variant="outline" size="sm" disabled={refresh.isPending} onClick={() => refresh.mutate()}>
            {refresh.isPending ? "Refreshing…" : "Refresh"}
          </Button>
        </div>
      </div>
      {heatmap.isLoading && <p className="text-sm text-muted-foreground">Loading holdings…</p>}
      {heatmap.isError && (
        <p role="alert" className="text-sm text-rose-600 dark:text-rose-400">
          Could not load holdings.
        </p>
      )}
      <AllocationTreemap
        data={data}
        ariaLabel={`${ticker} holdings heatmap`}
        onSelect={(d) => {
          if (d.navigable !== false && d.ticker) router.push(`/company/${d.ticker}`);
        }}
      />
    </div>
  );
}
