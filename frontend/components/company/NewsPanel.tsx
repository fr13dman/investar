"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { api, type NewsItem } from "@/lib/api";
import { formatDateTime, formatNumber } from "@/lib/format";
import { cn } from "@/lib/utils";

import { pollWhileRefreshing, RefreshNote } from "./RefreshNote";

type Filter = "all" | "positive" | "neutral" | "negative";
const TONE: Record<string, string> = {
  positive: "border-emerald-500/40 text-emerald-600 dark:text-emerald-400",
  negative: "border-rose-500/40 text-rose-600 dark:text-rose-400",
  neutral: "border-border text-muted-foreground",
};

export function SentimentBadge({ sentiment }: { sentiment: NewsItem["sentiment"] }) {
  const label = sentiment.label ?? "neutral";
  return (
    <Badge variant="outline" className={TONE[label]} title={sentiment.model ? `${sentiment.model} score ${sentiment.score}` : undefined}>
      {label}
    </Badge>
  );
}

export function NewsPanel({ ticker }: { ticker: string }) {
  const qc = useQueryClient();
  const [filter, setFilter] = useState<Filter>("all");
  const { data } = useQuery({ queryKey: ["news", ticker], queryFn: () => api.news(ticker), refetchInterval: pollWhileRefreshing });
  const items = (data?.items ?? []).filter((i) => filter === "all" || (i.sentiment.label ?? "neutral") === filter);
  const s = data?.summary;

  return (
    <div className="space-y-4">
      <RefreshNote
        source="Finnhub company news"
        status={data?.refresh}
        onRefresh={() => api.news(ticker, true).then((d) => qc.setQueryData(["news", ticker], d))}
      />
      {data && !data.configured && data.items.length === 0 && (
        <p className="rounded-lg border border-border p-3 text-sm text-muted-foreground">
          Add a free Finnhub key as <code>FINNHUB_API_KEY</code> in <code>.env</code> to load company news.
        </p>
      )}
      {s && (
        <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Sentiment filter">
          {(["all", "positive", "neutral", "negative"] as Filter[]).map((f) => (
            <button
              key={f}
              type="button"
              aria-pressed={filter === f}
              onClick={() => setFilter(f)}
              className={cn(
                "rounded-full border px-3 py-1 text-xs capitalize",
                filter === f ? "border-primary bg-primary text-primary-foreground" : "border-border text-muted-foreground",
              )}
            >
              {f} {f !== "all" ? s[f] : s.positive + s.neutral + s.negative}
            </button>
          ))}
          {s.average_score !== null && (
            <span className="ml-auto text-xs text-muted-foreground">
              Average sentiment {formatNumber(s.average_score, 2)} (-1 to +1, last 30 days)
            </span>
          )}
        </div>
      )}
      <ul className="space-y-3" aria-label="News">
        {items.map((n) => (
          <li key={n.url} className="rounded-lg border border-border p-3">
            <div className="flex items-start justify-between gap-3">
              <a href={n.url} target="_blank" rel="noopener noreferrer" className="font-medium hover:underline">
                {n.headline}
              </a>
              <SentimentBadge sentiment={n.sentiment} />
            </div>
            {n.summary && <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">{n.summary}</p>}
            <div className="mt-1 text-xs text-muted-foreground">
              {n.source} · {formatDateTime(n.published_at)}
            </div>
          </li>
        ))}
        {data && items.length === 0 && data.items.length > 0 && (
          <li className="text-sm text-muted-foreground">No {filter} headlines.</li>
        )}
      </ul>
    </div>
  );
}
