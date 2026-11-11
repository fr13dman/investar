"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api, ApiError, type Watchlist } from "@/lib/api";

function WatchlistCard({ w }: { w: Watchlist }) {
  const qc = useQueryClient();
  const [name, setName] = useState(w.name);
  const [ticker, setTicker] = useState("");
  const [error, setError] = useState<string | null>(null);
  const invalidate = () => qc.invalidateQueries({ queryKey: ["watchlists"] });
  const onError = (e: unknown) => setError(e instanceof ApiError ? e.message : "Something went wrong");

  const rename = useMutation({ mutationFn: () => api.renameWatchlist(w.id, name), onSuccess: invalidate, onError });
  const remove = useMutation({ mutationFn: () => api.deleteWatchlist(w.id), onSuccess: invalidate, onError });
  const add = useMutation({
    mutationFn: () => api.addToWatchlist(w.id, ticker),
    onSuccess: () => {
      setTicker("");
      setError(null);
      invalidate();
    },
    onError,
  });
  const drop = useMutation({ mutationFn: (t: string) => api.removeFromWatchlist(w.id, t), onSuccess: invalidate });

  return (
    <Card aria-label={`Watchlist ${w.name}`}>
      <CardHeader className="flex flex-row items-center gap-2">
        <Input aria-label="Watchlist name" value={name} onChange={(e) => setName(e.target.value)} className="max-w-xs" />
        <Button variant="outline" size="sm" disabled={!name.trim() || name === w.name} onClick={() => rename.mutate()}>
          Rename
        </Button>
        <Button variant="destructive" size="sm" className="ml-auto" onClick={() => remove.mutate()}>
          Delete
        </Button>
      </CardHeader>
      <CardContent className="space-y-3">
        <form
          className="flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            if (ticker.trim()) add.mutate();
          }}
        >
          <Input aria-label="Add ticker" placeholder="Add ticker, e.g. NVDA" value={ticker} onChange={(e) => setTicker(e.target.value)} className="max-w-xs" />
          <Button type="submit" size="sm">
            Add
          </Button>
        </form>
        {error && <p role="alert" className="text-sm text-rose-400">{error}</p>}
        <div className="flex flex-wrap gap-2">
          {w.tickers.map((t) => (
            <span key={t} className="flex items-center gap-1 rounded-full border border-border px-3 py-1 text-sm">
              <Link href={`/company/${t}`} className="hover:underline">
                {t}
              </Link>
              <button type="button" aria-label={`Remove ${t}`} className="text-muted-foreground hover:text-foreground" onClick={() => drop.mutate(t)}>
                ×
              </button>
            </span>
          ))}
          {w.tickers.length === 0 && <span className="text-sm text-muted-foreground">No tickers yet.</span>}
        </div>
        {w.tickers.length > 0 && (
          <Link href={`/?wl=${w.id}`} className="text-sm text-muted-foreground underline-offset-4 hover:underline">
            Open in screener
          </Link>
        )}
      </CardContent>
    </Card>
  );
}

export function WatchlistsManager() {
  const qc = useQueryClient();
  const { data } = useQuery({ queryKey: ["watchlists"], queryFn: api.watchlists });
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const create = useMutation({
    mutationFn: () => api.createWatchlist(name.trim()),
    onSuccess: () => {
      setName("");
      setError(null);
      qc.invalidateQueries({ queryKey: ["watchlists"] });
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : "Something went wrong"),
  });

  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-semibold tracking-tight">Watchlists</h1>
      <form
        className="flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          if (name.trim()) create.mutate();
        }}
      >
        <Input aria-label="New watchlist name" placeholder="New watchlist name" value={name} onChange={(e) => setName(e.target.value)} className="max-w-xs" />
        <Button type="submit">Create</Button>
      </form>
      {error && <p role="alert" className="text-sm text-rose-400">{error}</p>}
      <div className="grid gap-4 md:grid-cols-2">
        {(data ?? []).map((w) => (
          <WatchlistCard key={`${w.id}-${w.name}`} w={w} />
        ))}
      </div>
    </div>
  );
}
