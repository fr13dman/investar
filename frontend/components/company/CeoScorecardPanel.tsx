"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { ChangeValue } from "@/components/market/ChangeValue";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api, type CeoScorecard } from "@/lib/api";
import { useChartColors } from "@/lib/chartTheme";
import { formatCompact, formatDate, formatNumber } from "@/lib/format";

import { pollWhileRefreshing, RefreshNote } from "./RefreshNote";

const SOURCE_LABEL: Record<string, string> = {
  manual: "set manually",
  wikidata: "from Wikidata",
  "wikidata-unlabeled": "from Wikidata (unlabeled entry, please verify)",
};

function Metric({ label, value, hint }: { label: string; value: React.ReactNode; hint?: string }) {
  return (
    <div className="rounded-lg border border-border p-3">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="text-lg font-semibold">{value}</div>
      {hint && <div className="text-xs text-muted-foreground">{hint}</div>}
    </div>
  );
}

function OverrideForm({ ticker, card }: { ticker: string; card: CeoScorecard | null }) {
  const qc = useQueryClient();
  const [name, setName] = useState(card?.ceo_name ?? "");
  const [start, setStart] = useState(card?.tenure_start ?? "");
  const save = useMutation({
    mutationFn: () => api.setCeoOverride(ticker, { ceo_name: name || null, tenure_start: start || null }),
    onSuccess: (data) => qc.setQueryData(["ceo", ticker], (old: object | undefined) => ({ ...(old ?? {}), scorecard: data.scorecard })),
  });
  return (
    <form
      className="flex flex-wrap items-end gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        save.mutate();
      }}
    >
      <label className="text-xs text-muted-foreground">
        CEO name
        <Input aria-label="CEO name" value={name} onChange={(e) => setName(e.target.value)} className="mt-1 w-56" />
      </label>
      <label className="text-xs text-muted-foreground">
        Tenure start
        <Input aria-label="Tenure start" type="date" value={start} onChange={(e) => setStart(e.target.value)} className="mt-1 w-44" />
      </label>
      <Button type="submit" size="sm" variant="outline" disabled={save.isPending}>
        Save override
      </Button>
    </form>
  );
}

export function CeoScorecardPanel({ ticker }: { ticker: string }) {
  const chart = useChartColors();
  const qc = useQueryClient();
  const { data } = useQuery({
    queryKey: ["ceo", ticker],
    queryFn: () => api.ceo(ticker),
    refetchInterval: pollWhileRefreshing,
  });
  const card = data?.scorecard ?? null;
  const pvp = [...(card?.pay_vs_performance ?? [])].reverse().map((r) => ({
    year: r.fiscal_year_end.slice(0, 4),
    "Total comp (summary table)": r.peo_total_comp,
    "Compensation actually paid": r.peo_comp_actually_paid,
  }));

  return (
    <div className="space-y-4">
      <RefreshNote
        source="SEC EDGAR + Wikidata"
        status={data?.refresh}
        onRefresh={() => api.ceo(ticker, true).then((d) => qc.setQueryData(["ceo", ticker], d))}
      />
      {!card && (
        <p className="text-sm text-muted-foreground">
          {data?.refresh.refreshing ? "Building the CEO scorecard from SEC filings…" : "No CEO scorecard yet."}
        </p>
      )}
      {card && (
        <>
          <Card>
            <CardHeader>
              <CardTitle>
                {card.ceo_name ?? "Unknown CEO"}
                <span className="ml-2 text-sm font-normal text-muted-foreground">
                  {card.tenure_start
                    ? `CEO since ${formatDate(card.tenure_start)} (${SOURCE_LABEL[card.tenure_source ?? ""] ?? card.tenure_source})`
                    : "tenure start unknown"}
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                <Metric
                  label="Return vs SPY"
                  value={<ChangeValue value={card.excess_return_pct} />}
                  hint={card.window_start ? `since ${formatDate(card.window_start)}` : undefined}
                />
                <Metric
                  label="Stock total return"
                  value={<ChangeValue value={card.tsr_pct} />}
                  hint={card.tsr_annualized_pct !== null ? `${formatNumber(card.tsr_annualized_pct, 1)}% a year` : undefined}
                />
                <Metric
                  label="SPY total return"
                  value={<ChangeValue value={card.spy_tsr_pct} />}
                  hint={card.spy_annualized_pct !== null ? `${formatNumber(card.spy_annualized_pct, 1)}% a year` : undefined}
                />
                <Metric
                  label="Net margin"
                  value={`${formatNumber(card.margin_start_pct, 1)}% → ${formatNumber(card.margin_end_pct, 1)}%`}
                  hint="first fiscal year of tenure → latest"
                />
                <Metric label="Revenue growth (CAGR)" value={<ChangeValue value={card.revenue_cagr_pct} />} />
                <Metric label="EPS growth (CAGR)" value={<ChangeValue value={card.eps_cagr_pct} />} />
              </div>
              {card.window_truncated && (
                <p className="text-xs text-amber-600 dark:text-amber-400">
                  {card.tenure_start
                    ? "The tenure started before the stored price history, so returns cover the available window only."
                    : "Tenure start unknown: returns cover the full stored price history. Set the start date below."}
                </p>
              )}
              <OverrideForm key={`${card.ceo_name}-${card.tenure_start}`} ticker={ticker} card={card} />
            </CardContent>
          </Card>

          {card.fundamentals.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Fundamentals by fiscal year (SEC 10-K)</CardTitle>
              </CardHeader>
              <CardContent className="overflow-x-auto">
                <table className="w-full text-sm" aria-label="Fundamentals">
                  <thead className="text-xs text-muted-foreground">
                    <tr>
                      <th className="text-left font-normal">Fiscal year end</th>
                      <th className="text-right font-normal">Revenue</th>
                      <th className="text-right font-normal">Net income</th>
                      <th className="text-right font-normal">Net margin</th>
                      <th className="text-right font-normal">Diluted EPS</th>
                    </tr>
                  </thead>
                  <tbody className="tabular-nums">
                    {[...card.fundamentals].reverse().slice(0, 10).map((r) => (
                      <tr key={r.fiscal_year_end} className="border-t border-border/50">
                        <td className="py-1">{formatDate(r.fiscal_year_end)}</td>
                        <td className="text-right">{formatCompact(r.revenue, "$")}</td>
                        <td className="text-right">{formatCompact(r.net_income, "$")}</td>
                        <td className="text-right">{r.net_margin_pct !== null ? `${formatNumber(r.net_margin_pct, 1)}%` : "—"}</td>
                        <td className="text-right">{r.eps !== null ? `$${formatNumber(r.eps, 2)}` : "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader>
              <CardTitle>Pay versus performance (proxy statement)</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {card.pay_vs_performance.length === 0 ? (
                <p className="text-sm text-muted-foreground">No pay-versus-performance disclosure found in the latest proxy.</p>
              ) : (
                <>
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={pvp}>
                        <CartesianGrid strokeDasharray="3 3" stroke={chart.grid} />
                        <XAxis dataKey="year" stroke={chart.axis} fontSize={12} />
                        <YAxis stroke={chart.axis} fontSize={12} tickFormatter={(v: number) => formatCompact(v, "$")} />
                        <Tooltip formatter={(v) => formatCompact(Number(v), "$")} contentStyle={chart.tooltip} />
                        <Legend />
                        <Bar dataKey="Total comp (summary table)" fill={chart.benchmark} />
                        <Bar dataKey="Compensation actually paid" fill={chart.secondary} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                  <table className="w-full text-sm" aria-label="Pay versus performance">
                    <thead className="text-xs text-muted-foreground">
                      <tr>
                        <th className="text-left font-normal">Fiscal year end</th>
                        <th className="text-left font-normal">CEO</th>
                        <th className="text-right font-normal">Total comp</th>
                        <th className="text-right font-normal">Actually paid</th>
                        <th className="text-right font-normal">$100 invested became</th>
                        <th className="text-right font-normal">Peer group</th>
                      </tr>
                    </thead>
                    <tbody className="tabular-nums">
                      {card.pay_vs_performance.map((r) => (
                        <tr key={r.fiscal_year_end} className="border-t border-border/50">
                          <td className="py-1">{formatDate(r.fiscal_year_end)}</td>
                          <td>{r.peo_names?.join(", ") ?? "—"}</td>
                          <td className="text-right">{formatCompact(r.peo_total_comp, "$")}</td>
                          <td className="text-right">{formatCompact(r.peo_comp_actually_paid, "$")}</td>
                          <td className="text-right">{r.tsr_value !== undefined ? `$${formatNumber(r.tsr_value, 2)}` : "—"}</td>
                          <td className="text-right">{r.peer_tsr_value !== undefined ? `$${formatNumber(r.peer_tsr_value, 2)}` : "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
