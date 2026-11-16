"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useMemo } from "react";

import { pick } from "@/components/screener/params";
import { Button } from "@/components/ui/button";
import { api, type EtfTile, type HeatmapPeriod } from "@/lib/api";
import { cn } from "@/lib/utils";

import { formatAum } from "./format";
import { heatText } from "./heatColor";
import { PeriodToggle } from "./PeriodToggle";
import { EtfMapTreemap } from "./Treemap";

const PERIODS: HeatmapPeriod[] = ["wow", "mom", "yoy"];

function EtfTable({ rows }: { rows: EtfTile[] }) {
  return (
    <div className="overflow-x-auto rounded border border-border">
      <table className="w-full text-left text-xs" aria-label="ETF list">
        <thead className="bg-muted/50 text-muted-foreground">
          <tr>
            <th className="px-2 py-1.5 font-medium">Ticker</th>
            <th className="px-2 py-1.5 font-medium">Name</th>
            <th className="px-2 py-1.5 font-medium text-right">AUM</th>
            <th className="px-2 py-1.5 font-medium text-right">Price</th>
            <th className="px-2 py-1.5 font-medium text-right">Return</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.ticker} className="border-t border-border hover:bg-muted/40">
              <td className="px-2 py-1 font-semibold">
                <Link href={`/company/${r.ticker}`} className="hover:underline">
                  {r.ticker}
                </Link>
              </td>
              <td className="max-w-[20rem] truncate px-2 py-1 text-muted-foreground">{r.name}</td>
              <td className="px-2 py-1 text-right tabular-nums">{formatAum(r.aum)}</td>
              <td className="px-2 py-1 text-right tabular-nums">{r.price != null ? r.price.toFixed(2) : "—"}</td>
              <td className="px-2 py-1 text-right tabular-nums">{heatText(r.return_pct)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function EtfHub({ mode }: { mode: "niches" | "vistashares" }) {
  const router = useRouter();
  const sp = useSearchParams();
  const period = pick(sp.get("period"), PERIODS, "wow");
  const niche = sp.get("niche") || undefined;
  const family = sp.get("family") || undefined;
  const qc = useQueryClient();

  const setParam = (key: string, value: string | undefined) => {
    const next = new URLSearchParams(sp.toString());
    if (!value) next.delete(key);
    else next.set(key, value);
    const qs = next.toString();
    router.replace(qs ? `?${qs}` : "?", { scroll: false });
  };

  const niches = useQuery({ queryKey: ["niches"], queryFn: api.niches, enabled: mode === "niches" });
  const list = useQuery({
    queryKey: mode === "niches" ? ["etfs", niche, period] : ["vistashares", family, period],
    queryFn: () =>
      mode === "niches"
        ? api.etfs({ niche, period })
        : api.vistasharesEtfs({ family, period }),
  });

  const refresh = useMutation({
    mutationFn: () => api.refreshEtfs((list.data?.etfs ?? []).map((e) => e.ticker)),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: mode === "niches" ? ["etfs"] : ["vistashares"] });
    },
  });

  const mapData = useMemo(
    () =>
      (list.data?.etfs ?? []).map((e) => ({
        name: e.name,
        ticker: e.ticker,
        // Always use API `size` (includes AUM floor so small launches stay visible).
        size: e.size > 0 ? e.size : 1,
        return_pct: e.return_pct,
        navigable: true,
      })),
    [list.data],
  );

  const chips =
    mode === "niches"
      ? [{ id: "", name: "All niches" }, ...(niches.data ?? []).map((n) => ({ id: n.slug, name: n.name }))]
      : [{ id: "", name: "All families" }, ...(list.data?.families ?? []).map((f) => ({ id: f.id, name: f.name }))];

  const active = mode === "niches" ? niche || "" : family || "";

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            {mode === "niches" ? "Niche ETFs" : "VistaShares ETFs"}
          </h1>
          <p className="text-sm text-muted-foreground">
            {mode === "niches"
              ? "Curated ETFs across Investar niches. Tile size is net assets; color is period return."
              : "All VistaShares funds by family. Tile size is net assets (with a floor for small launches)."}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <PeriodToggle value={period} onChange={(p) => setParam("period", p === "wow" ? undefined : p)} />
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={refresh.isPending || !(list.data?.etfs.length)}
            onClick={() => refresh.mutate()}
          >
            {refresh.isPending ? "Refreshing…" : "Refresh"}
          </Button>
        </div>
      </div>

      <div className="flex flex-wrap gap-4 text-sm">
        <Link
          href="/etfs"
          className={cn(mode === "niches" ? "font-semibold text-foreground" : "text-muted-foreground hover:text-foreground")}
        >
          By niche
        </Link>
        <Link
          href="/etfs/vistashares"
          className={cn(
            mode === "vistashares" ? "font-semibold text-foreground" : "text-muted-foreground hover:text-foreground",
          )}
        >
          VistaShares
        </Link>
      </div>

      <div role="group" aria-label={mode === "niches" ? "Niche filter" : "Family filter"} className="flex flex-wrap gap-1.5">
        {chips.map((c) => (
          <button
            key={c.id || "all"}
            type="button"
            aria-pressed={active === c.id}
            onClick={() => setParam(mode === "niches" ? "niche" : "family", c.id || undefined)}
            className={cn(
              "rounded border px-2 py-0.5 text-xs",
              active === c.id
                ? "border-primary bg-primary text-primary-foreground"
                : "border-input text-muted-foreground hover:text-foreground",
            )}
          >
            {c.name}
          </button>
        ))}
      </div>

      {list.isError && (
        <p role="alert" className="text-sm text-rose-600 dark:text-rose-400">
          Could not load ETFs.
        </p>
      )}

      <EtfMapTreemap
        data={mapData}
        ariaLabel="ETF performance map"
        onSelect={(d) => d.ticker && router.push(`/company/${d.ticker}`)}
      />

      {(list.data?.groups ?? []).map((g) => (
        <section key={g.slug} className="space-y-2">
          <h2 className="text-sm font-semibold">{g.name}</h2>
          <EtfTable rows={g.etfs} />
        </section>
      ))}
    </div>
  );
}
