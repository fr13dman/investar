"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { StarIcon } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { api, type Watchlist } from "@/lib/api";
import { cn } from "@/lib/utils";

export function WatchButton({ ticker, watchlists }: { ticker: string; watchlists: Watchlist[] }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const qc = useQueryClient();
  const watched = watchlists.some((w) => w.tickers.includes(ticker));

  const toggle = useMutation({
    mutationFn: async (w: Watchlist) =>
      w.tickers.includes(ticker) ? api.removeFromWatchlist(w.id, ticker) : api.addToWatchlist(w.id, ticker),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["watchlists"] }),
  });
  const create = useMutation({
    mutationFn: async () => {
      const w = await api.createWatchlist("My watchlist");
      return api.addToWatchlist(w.id, ticker);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["watchlists"] }),
  });

  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [open]);

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        aria-label={`Watchlists for ${ticker}`}
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        className="rounded p-1 text-muted-foreground hover:text-foreground"
      >
        <StarIcon className={cn("size-4", watched && "fill-amber-400 text-amber-400")} />
      </button>
      {open && (
        <div
          role="menu"
          className="absolute left-0 z-20 mt-1 w-48 rounded-lg border border-border bg-popover p-1 shadow-lg"
        >
          {watchlists.length === 0 && (
            <button
              role="menuitem"
              type="button"
              className="w-full rounded px-2 py-1 text-left text-sm hover:bg-muted"
              onClick={() => create.mutate()}
            >
              Create &ldquo;My watchlist&rdquo;
            </button>
          )}
          {watchlists.map((w) => (
            <button
              key={w.id}
              role="menuitemcheckbox"
              aria-checked={w.tickers.includes(ticker)}
              type="button"
              className="flex w-full items-center justify-between rounded px-2 py-1 text-left text-sm hover:bg-muted"
              onClick={() => toggle.mutate(w)}
            >
              {w.name}
              {w.tickers.includes(ticker) && <span className="text-xs text-amber-400">added</span>}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
