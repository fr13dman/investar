"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { ComposableMap, Geographies, Geography } from "react-simple-maps";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api, type GlobalPresence } from "@/lib/api";
import { formatCompact, formatDate, formatNumber } from "@/lib/format";
import { cn } from "@/lib/utils";

import { pollWhileRefreshing, RefreshNote } from "./RefreshNote";

const MAP_URL = "/maps/countries-110m.json";
// Countries too small for the 110m world map; listed but not drawn.
const NOT_ON_MAP = new Set(["344", "702", "442", "438", "492", "674", "336", "446", "060", "136", "092", "831", "832", "833"]);

export function fillFor(count: number, max: number): string {
  if (!count) return "rgba(255,255,255,0.06)";
  const alpha = 0.3 + 0.7 * (count / Math.max(max, 1));
  return `rgba(52, 211, 153, ${alpha.toFixed(2)})`;
}

function SubsidiaryMap({ countries }: { countries: GlobalPresence["countries"] }) {
  const byNumeric = useMemo(() => new Map(countries.map((c) => [c.numeric, c])), [countries]);
  const max = Math.max(0, ...countries.map((c) => c.count));
  return (
    <ComposableMap projectionConfig={{ scale: 150 }} className="h-auto w-full" aria-label="Subsidiary countries map">
      <Geographies geography={MAP_URL}>
        {({ geographies }) =>
          geographies.map((geo) => {
            const c = byNumeric.get(String(geo.id));
            return (
              <Geography
                key={geo.rsmKey}
                geography={geo}
                data-country={c ? c.alpha2 : undefined}
                fill={fillFor(c?.count ?? 0, max)}
                stroke="rgba(255,255,255,0.15)"
                strokeWidth={0.4}
                className={cn("outline-none", c && "hover:fill-amber-400")}
              >
                <title>{c ? `${c.country_name}: ${c.count} subsidiar${c.count === 1 ? "y" : "ies"}` : String(geo.properties?.name ?? "")}</title>
              </Geography>
            );
          })
        }
      </Geographies>
    </ComposableMap>
  );
}

export function GlobalPresencePanel({ ticker }: { ticker: string }) {
  const qc = useQueryClient();
  const [filter, setFilter] = useState("");
  const [axis, setAxis] = useState<"geographic" | "segment">("geographic");
  const { data } = useQuery({
    queryKey: ["global", ticker],
    queryFn: () => api.globalPresence(ticker),
    refetchInterval: pollWhileRefreshing,
  });

  const axes = Array.from(new Set((data?.revenue_by_region ?? []).map((r) => r.axis)));
  const activeAxis = axes.includes(axis) ? axis : axes[0];
  const latest = data?.revenue_by_region.find((r) => r.axis === activeAxis);
  const subs = (data?.subsidiaries ?? []).filter(
    (s) => !filter || `${s.name} ${s.country_name ?? ""} ${s.jurisdiction ?? ""}`.toLowerCase().includes(filter.toLowerCase()),
  );

  return (
    <div className="space-y-4">
      <RefreshNote
        source="SEC 10-K (Exhibit 21 and XBRL)"
        status={data?.refresh}
        onRefresh={() => api.globalPresence(ticker, true).then((d) => qc.setQueryData(["global", ticker], d))}
      />
      {data?.filing.url && (
        <a href={data.filing.url} target="_blank" rel="noopener noreferrer" className="text-xs text-muted-foreground underline-offset-4 hover:underline">
          Source filing {data.filing.accession}
        </a>
      )}
      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>
              Subsidiaries in {data?.countries.length ?? 0} countries
              <span className="ml-2 text-sm font-normal text-muted-foreground">{data?.subsidiaries.length ?? 0} significant subsidiaries</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {data && data.countries.length > 0 ? (
              <SubsidiaryMap countries={data.countries} />
            ) : (
              <p className="text-sm text-muted-foreground">
                {data?.refresh.refreshing ? "Reading the latest 10-K…" : "No Exhibit 21 subsidiary list found in the latest annual report."}
              </p>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>By country</CardTitle>
          </CardHeader>
          <CardContent>
            <ol className="space-y-1 text-sm" aria-label="Subsidiaries by country">
              {(data?.countries ?? []).map((c) => (
                <li key={c.alpha2} className="flex justify-between gap-2">
                  <span>
                    {c.country_name}
                    {NOT_ON_MAP.has(c.numeric) && <span className="ml-1 text-xs text-muted-foreground">(not on map)</span>}
                  </span>
                  <span className="tabular-nums text-muted-foreground">{c.count}</span>
                </li>
              ))}
            </ol>
            {data && data.unmapped > 0 && (
              <p className="mt-2 text-xs text-muted-foreground">{data.unmapped} with an unrecognized jurisdiction</p>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-2">
          <CardTitle>
            Revenue by region
            {latest && <span className="ml-2 text-sm font-normal text-muted-foreground">fiscal year ended {formatDate(latest.period_end)}</span>}
          </CardTitle>
          {axes.length > 1 && (
            <div role="group" aria-label="Revenue breakdown" className="flex gap-1">
              {axes.map((a) => (
                <button
                  key={a}
                  type="button"
                  aria-pressed={activeAxis === a}
                  onClick={() => setAxis(a)}
                  className={cn("rounded-md px-2 py-0.5 text-xs", activeAxis === a ? "bg-primary text-primary-foreground" : "text-muted-foreground")}
                >
                  {a === "geographic" ? "Geographic disclosure" : "Geographic segments"}
                </button>
              ))}
            </div>
          )}
        </CardHeader>
        <CardContent>
          {!latest ? (
            <p className="text-sm text-muted-foreground">
              {data?.refresh.refreshing && !data.refresh.fetched_at
                ? "Reading the latest 10-K…"
                : "Not reported: the latest 10-K has no tagged revenue-by-geography breakdown."}
            </p>
          ) : (
            <div className="grid gap-4 lg:grid-cols-2">
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={latest.regions} layout="vertical" margin={{ left: 40 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                    <XAxis type="number" stroke="#a3a3a3" fontSize={12} tickFormatter={(v: number) => formatCompact(v, "$")} />
                    <YAxis type="category" dataKey="region" stroke="#a3a3a3" fontSize={12} width={120} />
                    <Tooltip formatter={(v) => formatCompact(Number(v), "$")} contentStyle={{ background: "#171717", border: "none" }} />
                    <Bar dataKey="revenue" fill="#60a5fa" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <table className="w-full text-sm" aria-label="Revenue by region">
                <thead className="text-xs text-muted-foreground">
                  <tr>
                    <th className="text-left font-normal">Region</th>
                    <th className="text-right font-normal">Revenue</th>
                    <th className="text-right font-normal">Share</th>
                  </tr>
                </thead>
                <tbody className="tabular-nums">
                  {latest.regions.map((r) => (
                    <tr key={r.member} className="border-t border-border/50">
                      <td className="py-1">{r.region}</td>
                      <td className="text-right">{formatCompact(r.revenue, "$")}</td>
                      <td className="text-right">{r.share_pct !== null ? `${formatNumber(r.share_pct, 1)}%` : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {data && data.subsidiaries.length > 0 && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between gap-2">
            <CardTitle>Subsidiaries</CardTitle>
            <Input aria-label="Filter subsidiaries" placeholder="Filter" value={filter} onChange={(e) => setFilter(e.target.value)} className="w-48" />
          </CardHeader>
          <CardContent>
            <ul className="grid gap-x-10 gap-y-1 text-sm sm:grid-cols-2" aria-label="Subsidiaries">
              {subs.map((s) => (
                <li key={`${s.name}-${s.jurisdiction}`} className="flex justify-between gap-2 border-b border-border/40 py-1">
                  <span className="truncate">{s.name}</span>
                  <span className="shrink-0 text-muted-foreground">{s.jurisdiction}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
