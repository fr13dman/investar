"use client";

import { useEffect, useState } from "react";

import { Input } from "@/components/ui/input";
import type { AssetFilter, CapBand, ChangeMode, IndexFilter, Watchlist } from "@/lib/api";
import { cn } from "@/lib/utils";

export const selectClass =
  "h-8 rounded-lg border border-input bg-transparent px-2 text-sm outline-none focus-visible:ring-3 focus-visible:ring-ring/50 dark:bg-input/30";

export function FilterBar({
  type,
  index,
  cap,
  q,
  mode,
  wl,
  watchlists,
  onChange,
}: {
  type: AssetFilter;
  index: IndexFilter;
  cap?: CapBand;
  q?: string;
  mode: ChangeMode;
  wl?: number;
  watchlists: Watchlist[];
  onChange: (patch: {
    type?: AssetFilter;
    index?: IndexFilter;
    cap?: CapBand;
    q?: string;
    mode?: ChangeMode;
    wl?: number;
  }) => void;
}) {
  const [search, setSearch] = useState(q ?? "");
  const [syncedQ, setSyncedQ] = useState(q);
  if (q !== syncedQ) {
    // URL changed elsewhere (back button, sector link): adopt it during render rather than in an effect.
    setSyncedQ(q);
    setSearch(q ?? "");
  }
  useEffect(() => {
    const t = setTimeout(() => {
      if ((q ?? "") !== search) onChange({ q: search || undefined });
    }, 300);
    return () => clearTimeout(t);
  }, [search, q, onChange]);

  return (
    <div className="flex flex-wrap items-center gap-3">
      <Input
        aria-label="Search ticker or company"
        placeholder="Search ticker or company"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="w-56"
      />
      <label className="flex items-center gap-2 text-sm text-muted-foreground">
        Type
        <select
          aria-label="Asset type"
          className={selectClass}
          value={type}
          onChange={(e) => onChange({ type: e.target.value as AssetFilter })}
        >
          <option value="all">Stocks + ETFs</option>
          <option value="stock">Stocks</option>
          <option value="etf">ETFs</option>
        </select>
      </label>
      <label className="flex items-center gap-2 text-sm text-muted-foreground">
        Index
        <select
          aria-label="Index"
          className={selectClass}
          value={index}
          onChange={(e) => onChange({ index: e.target.value as IndexFilter })}
        >
          <option value="all">All tracked</option>
          <option value="sp500">S&amp;P 500</option>
          <option value="ndx100">Nasdaq-100</option>
          <option value="both">In both</option>
          <option value="other">Not in an index</option>
        </select>
      </label>
      <label className="flex items-center gap-2 text-sm text-muted-foreground">
        Market cap
        <select
          aria-label="Market cap"
          className={selectClass}
          value={cap ?? ""}
          onChange={(e) => onChange({ cap: (e.target.value || undefined) as CapBand | undefined })}
        >
          <option value="">Any</option>
          <option value="mega">Mega (200B+)</option>
          <option value="large">Large (10B-200B)</option>
          <option value="mid">Mid (2B-10B)</option>
          <option value="small">Small (under 2B)</option>
        </select>
      </label>
      {watchlists.length > 0 && (
        <label className="flex items-center gap-2 text-sm text-muted-foreground">
          Watchlist
          <select
            aria-label="Watchlist"
            className={selectClass}
            value={wl ?? ""}
            onChange={(e) => onChange({ wl: e.target.value ? Number(e.target.value) : undefined })}
          >
            <option value="">None</option>
            {watchlists.map((w) => (
              <option key={w.id} value={w.id}>
                {w.name}
              </option>
            ))}
          </select>
        </label>
      )}
      <div role="group" aria-label="Change units" className="ml-auto flex overflow-hidden rounded-lg border border-input">
        {(["pct", "abs"] as const).map((m) => (
          <button
            key={m}
            type="button"
            aria-pressed={mode === m}
            onClick={() => onChange({ mode: m })}
            className={cn(
              "px-3 py-1 text-sm",
              mode === m ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground",
            )}
          >
            {m === "pct" ? "%" : "$"}
          </button>
        ))}
      </div>
    </div>
  );
}
