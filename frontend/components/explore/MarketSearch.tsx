"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { NicheChecklist } from "@/components/niches/NicheChecklist";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api, ApiError, type NicheNode, type SearchResult } from "@/lib/api";

const POLL_MS = 2000;

function useDebounced<T>(value: T, ms: number): T {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return v;
}

/** Polls the background backfill for a just-added symbol until it is ready or failed. */
function TrackProgress({ ticker, onReady }: { ticker: string; onReady: () => void }) {
  const { data } = useQuery({
    queryKey: ["track-status", ticker],
    queryFn: () => api.trackStatus(ticker),
    refetchInterval: (q) => (q.state.data?.status === "ready" || q.state.data?.status === "error" ? false : POLL_MS),
  });
  const status = data?.status ?? "adding";
  const notified = useRef(false);
  useEffect(() => {
    if (status === "ready" && !notified.current) {
      notified.current = true;
      onReady();
    }
  }, [status, onReady]);
  if (status === "ready")
    return (
      <span role="status" className="text-sm text-emerald-600 dark:text-emerald-400">
        Added.{" "}
        <Link href={`/company/${ticker}`} className="underline">
          Open {ticker}
        </Link>
      </span>
    );
  if (status === "error")
    return (
      <span role="status" className="text-sm text-rose-600 dark:text-rose-400">
        Could not load prices: {data?.message ?? "unknown error"}
      </span>
    );
  return (
    <span role="status" className="text-sm text-amber-600 dark:text-amber-400">
      Adding… fetching profile and 5 years of prices
    </span>
  );
}

function ResultRow({
  r,
  niches,
  added,
  onAdded,
}: {
  r: SearchResult;
  niches: NicheNode[];
  added: boolean;
  onAdded: (ticker: string) => void;
}) {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [ids, setIds] = useState<number[]>([]);
  const track = useMutation({
    mutationFn: () => api.track(r.symbol, ids),
    onSuccess: (row) => {
      setOpen(false);
      onAdded(row.ticker);
    },
  });
  const refresh = () => {
    for (const key of ["stocks", "niches", "sectors", "movers", "market-search"]) qc.invalidateQueries({ queryKey: [key] });
  };

  let action: React.ReactNode;
  if (added) action = <TrackProgress ticker={r.symbol} onReady={refresh} />;
  else if (r.tracked)
    action = (
      <Link href={`/company/${r.symbol}`} className="text-sm text-muted-foreground underline">
        Already tracked
      </Link>
    );
  else if (!r.asset_type) action = <span className="text-sm text-muted-foreground">Only stocks and ETFs</span>;
  else if (!r.us_listed) action = <span className="text-sm text-muted-foreground">Not US-listed</span>;
  else
    action = (
      <Button size="sm" variant="outline" onClick={() => setOpen((o) => !o)} aria-expanded={open}>
        Add {r.symbol}
      </Button>
    );

  return (
    <li className="space-y-3 py-3" data-symbol={r.symbol}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <span className="font-semibold">{r.symbol}</span> <span className="text-muted-foreground">{r.name}</span>
          <span className="ml-2 inline-flex gap-1 align-middle">
            {r.asset_type === "etf" && <Badge variant="secondary">ETF</Badge>}
            {r.exchange && <Badge variant="outline">{r.exchange}</Badge>}
          </span>
        </div>
        {action}
      </div>
      {open && (
        <div className="space-y-3 rounded-lg border border-border p-3">
          <p className="text-sm text-muted-foreground">Optionally tag {r.symbol} with niches, then add it to the screener.</p>
          <NicheChecklist niches={niches} selected={ids} onChange={setIds} />
          <div className="flex items-center gap-2">
            <Button size="sm" onClick={() => track.mutate()} disabled={track.isPending}>
              {track.isPending ? "Adding…" : "Add to screener"}
            </Button>
            <Button size="sm" variant="ghost" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            {track.isError && (
              <span role="alert" className="text-sm text-rose-600 dark:text-rose-400">
                {track.error instanceof ApiError ? track.error.message : "Could not add symbol"}
              </span>
            )}
          </div>
        </div>
      )}
    </li>
  );
}

export function MarketSearch({ niches }: { niches: NicheNode[] }) {
  const [text, setText] = useState("");
  const q = useDebounced(text.trim(), 300);
  const [added, setAdded] = useState<string[]>([]);
  const results = useQuery({
    queryKey: ["market-search", q],
    queryFn: () => api.searchMarket(q),
    enabled: q.length > 0,
    staleTime: 60_000,
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Search the market</CardTitle>
        <p className="text-sm text-muted-foreground">
          Find any US-listed stock or ETF by ticker or name and add it to the screener.
        </p>
      </CardHeader>
      <CardContent className="space-y-2">
        <Input
          aria-label="Search the market"
          placeholder="e.g. Nebius, uranium ETF, IONQ"
          value={text}
          onChange={(e) => setText(e.target.value)}
          className="max-w-md"
        />
        {results.isFetching && <p className="text-sm text-muted-foreground">Searching…</p>}
        {results.isError && (
          <p role="alert" className="text-sm text-rose-600 dark:text-rose-400">
            Market search is unavailable right now.
          </p>
        )}
        {results.data && results.data.length === 0 && q && (
          <p className="text-sm text-muted-foreground">No matches for &ldquo;{q}&rdquo;.</p>
        )}
        {results.data && results.data.length > 0 && (
          <ul aria-label="Market search results" className="divide-y divide-border">
            {results.data.map((r) => (
              <ResultRow
                key={r.symbol}
                r={r}
                niches={niches}
                added={added.includes(r.symbol)}
                onAdded={(t) => setAdded((a) => [...a, t])}
              />
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
