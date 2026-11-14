"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api, type CpcBreakdown, type PatentAssignee, type PatentItem, type Patents } from "@/lib/api";
import { useChartColors } from "@/lib/chartTheme";
import { formatDate, formatNumber } from "@/lib/format";

import { selectClass } from "../screener/FilterBar";
import { pollWhileRefreshing, RefreshNote } from "./RefreshNote";

function PatentList({ items, label }: { items: PatentItem[]; label: string }) {
  const [open, setOpen] = useState<string | null>(null);
  if (!items.length) return <p className="text-sm text-muted-foreground">None found.</p>;
  return (
    <ul className="space-y-2" aria-label={label}>
      {items.map((p) => (
        <li key={p.number} className="rounded-lg border border-border p-2 text-sm">
          <div className="flex items-start justify-between gap-2">
            <a href={p.url} target="_blank" rel="noopener noreferrer" className="font-medium hover:underline">
              {p.title ?? p.number}
            </a>
            <span className="shrink-0 text-xs text-muted-foreground">{formatDate(p.date)}</span>
          </div>
          <div className="text-xs text-muted-foreground">
            US {p.number}
            {p.cpc_class && ` · ${p.cpc_class} ${p.cpc_title ?? ""}`}
          </div>
          {p.abstract && (
            <button type="button" className="mt-1 text-left text-xs text-muted-foreground" onClick={() => setOpen(open === p.number ? null : p.number)}>
              {open === p.number ? p.abstract : `${p.abstract.slice(0, 140)}${p.abstract.length > 140 ? "…" : ""}`}
            </button>
          )}
        </li>
      ))}
    </ul>
  );
}

function CpcList({ data, label }: { data: CpcBreakdown; label: string }) {
  const max = Math.max(1, ...data.items.map((i) => i.count));
  return (
    <div>
      <ul className="space-y-1.5" aria-label={label}>
        {data.items.map((c) => (
          <li key={c.code} className="text-sm">
            <div className="flex justify-between gap-2">
              <span>
                <span className="font-mono text-xs">{c.code}</span> {c.title}
              </span>
              <span className="tabular-nums text-muted-foreground">{c.count}</span>
            </div>
            <div className="mt-0.5 h-1 rounded bg-muted">
              <div className="h-1 rounded bg-blue-400" style={{ width: `${(c.count / max) * 100}%` }} />
            </div>
          </li>
        ))}
      </ul>
      {data.note && <p className="mt-2 text-xs text-muted-foreground">Technology areas {data.note}.</p>}
    </div>
  );
}

function AssigneeEditor({ ticker, assignees }: { ticker: string; assignees: PatentAssignee[] }) {
  const qc = useQueryClient();
  const [rows, setRows] = useState<PatentAssignee[]>(assignees);
  const [name, setName] = useState("");
  const [match, setMatch] = useState<"exact" | "prefix">("exact");
  const save = useMutation({
    mutationFn: (next: PatentAssignee[]) => api.setPatentAssignees(ticker, next),
    onSuccess: (res) => {
      setRows(res.assignees);
      qc.setQueryData(["patents", ticker], (old: Patents | undefined) => (old ? { ...old, assignees: res.assignees, refresh: res.refresh } : old));
    },
  });
  return (
    <div className="space-y-2">
      <p className="text-xs text-muted-foreground">
        Patents are filed under legal entity names (for example &ldquo;Google LLC&rdquo; for Alphabet). Edit the names searched for this company.
      </p>
      <ul className="flex flex-wrap gap-2" aria-label="Patent assignee names">
        {rows.map((a) => (
          <li key={`${a.assignee_name}-${a.match}`} className="flex items-center gap-1 rounded-full border border-border px-3 py-1 text-xs">
            {a.assignee_name}
            <span className="text-muted-foreground">({a.match === "prefix" ? "starts with" : "exact"})</span>
            <button
              type="button"
              aria-label={`Remove ${a.assignee_name}`}
              className="text-muted-foreground hover:text-foreground"
              onClick={() => save.mutate(rows.filter((r) => r !== a))}
            >
              ×
            </button>
          </li>
        ))}
      </ul>
      <form
        className="flex flex-wrap gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          if (!name.trim()) return;
          save.mutate([...rows, { assignee_name: name.trim(), match }]);
          setName("");
        }}
      >
        <Input aria-label="Assignee name" placeholder="Assignee name" value={name} onChange={(e) => setName(e.target.value)} className="w-64" />
        <select aria-label="Match type" className={selectClass} value={match} onChange={(e) => setMatch(e.target.value as "exact" | "prefix")}>
          <option value="exact">Exact</option>
          <option value="prefix">Starts with</option>
        </select>
        <Button type="submit" size="sm" variant="outline">
          Add name
        </Button>
      </form>
    </div>
  );
}

export function PatentsPanel({ ticker }: { ticker: string }) {
  const chart = useChartColors();
  const qc = useQueryClient();
  const { data } = useQuery({ queryKey: ["patents", ticker], queryFn: () => api.patents(ticker), refetchInterval: pollWhileRefreshing });
  const sourceLabel = data?.source === "patentsview_bulk" ? "PatentsView bulk files" : "USPTO PatentsView API";

  return (
    <div className="space-y-4">
      <RefreshNote
        source={sourceLabel}
        status={data?.refresh}
        onRefresh={() => api.patents(ticker, true).then((d) => qc.setQueryData(["patents", ticker], d))}
      />
      <div className="grid gap-3 sm:grid-cols-2">
        <Card size="sm">
          <CardContent>
            <div className="text-xs text-muted-foreground">Granted patents, last 10 years</div>
            <div className="text-2xl font-semibold tabular-nums" data-testid="granted-total">
              {formatNumber(data?.granted.total_10y, 0)}
            </div>
          </CardContent>
        </Card>
        <Card size="sm">
          <CardContent>
            <div className="text-xs text-muted-foreground">Pending applications published, last 24 months</div>
            <div className="text-2xl font-semibold tabular-nums" data-testid="applications-total">
              {formatNumber(data?.applications.total_24m, 0)}
            </div>
          </CardContent>
        </Card>
      </div>

      {data && data.granted.by_year.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Granted patents per year</CardTitle>
          </CardHeader>
          <CardContent className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.granted.by_year}>
                <CartesianGrid strokeDasharray="3 3" stroke={chart.grid} />
                <XAxis dataKey="year" stroke={chart.axis} fontSize={12} />
                <YAxis stroke={chart.axis} fontSize={12} />
                <Tooltip contentStyle={chart.tooltip} />
                <Bar dataKey="count" fill={chart.tertiary} name="Granted" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Upcoming: pending applications</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {data && data.applications.top_cpc.items.length > 0 && <CpcList data={data.applications.top_cpc} label="Application technology areas" />}
            <PatentList items={data?.applications.recent ?? []} label="Pending applications" />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Granted: recent patents</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {data && data.granted.top_cpc.items.length > 0 && <CpcList data={data.granted.top_cpc} label="Granted technology areas" />}
            <PatentList items={data?.granted.recent ?? []} label="Granted patents" />
          </CardContent>
        </Card>
      </div>

      {data && (
        <Card>
          <CardHeader>
            <CardTitle>Assignee names</CardTitle>
          </CardHeader>
          <CardContent>
            <AssigneeEditor key={data.assignees.map((a) => a.assignee_name).join("|")} ticker={ticker} assignees={data.assignees} />
          </CardContent>
        </Card>
      )}
    </div>
  );
}
