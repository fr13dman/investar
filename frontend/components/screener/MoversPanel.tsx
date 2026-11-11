"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { ChangeValue } from "@/components/market/ChangeValue";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api, type ChangeMode, type StockRow, type SwingWindow } from "@/lib/api";
import { formatPrice } from "@/lib/format";
import { cn } from "@/lib/utils";

const WINDOW_LABEL: Record<SwingWindow, string> = { chg_1d: "1D", chg_1w: "1W", chg_ytd: "YTD" };

function MoverList({ title, rows, window, mode }: { title: string; rows: StockRow[]; window: SwingWindow; mode: ChangeMode }) {
  return (
    <div>
      <h3 className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">{title}</h3>
      <ol className="space-y-1" aria-label={title}>
        {rows.map((r) => (
          <li key={r.ticker} className="flex items-center justify-between gap-2 text-sm">
            <Link href={`/company/${r.ticker}`} className="truncate hover:underline">
              <span className="font-medium">{r.ticker}</span>{" "}
              <span className="text-muted-foreground">{r.name}</span>
            </Link>
            <span className="flex shrink-0 items-center gap-3">
              <span className="tabular-nums text-muted-foreground">{formatPrice(r.price)}</span>
              <ChangeValue value={r[`${window}_${mode}` as keyof StockRow] as number | null} mode={mode} />
            </span>
          </li>
        ))}
        {rows.length === 0 && <li className="text-sm text-muted-foreground">No data yet</li>}
      </ol>
    </div>
  );
}

export function MoversPanel({
  sector,
  industry,
  window,
  mode,
  onWindowChange,
}: {
  sector?: string;
  industry?: string;
  window: SwingWindow;
  mode: ChangeMode;
  onWindowChange: (w: SwingWindow) => void;
}) {
  const { data } = useQuery({
    queryKey: ["movers", sector, industry, window, mode],
    queryFn: () => api.movers({ sector, industry, window, mode, limit: 5 }),
  });
  return (
    <Card size="sm">
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Top movers {industry ? `in ${industry}` : sector ? `in ${sector}` : "across all sectors"}</CardTitle>
        <div role="group" aria-label="Mover window" className="flex gap-1">
          {(Object.keys(WINDOW_LABEL) as SwingWindow[]).map((w) => (
            <button
              key={w}
              type="button"
              aria-pressed={window === w}
              onClick={() => onWindowChange(w)}
              className={cn(
                "rounded-md px-2 py-0.5 text-xs",
                window === w ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground",
              )}
            >
              {WINDOW_LABEL[w]}
            </button>
          ))}
        </div>
      </CardHeader>
      <CardContent className="grid gap-6 md:grid-cols-2">
        <MoverList title="Top gainers" rows={data?.gainers ?? []} window={window} mode={mode} />
        <MoverList title="Top losers" rows={data?.losers ?? []} window={window} mode={mode} />
      </CardContent>
    </Card>
  );
}
