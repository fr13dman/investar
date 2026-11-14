"use client";

import { createColumnHelper, tableFeatures, useTable } from "@tanstack/react-table";
import { ArrowDownIcon, ArrowUpIcon } from "lucide-react";
import Link from "next/link";
import { createContext, useContext, useMemo } from "react";

import { ChangeValue } from "@/components/market/ChangeValue";
import { Sparkline } from "@/components/market/Sparkline";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { WatchButton } from "@/components/watchlists/WatchButton";
import type { ChangeMode, SortKey, StockRow, SwingWindow, Watchlist } from "@/lib/api";
import { formatCompact, formatMarketCap, formatNumber, formatPrice } from "@/lib/format";
import { cn } from "@/lib/utils";

// Table v9 keeps its column definitions stable, so per-render inputs reach cells through context.
const CellContext = createContext<{ mode: ChangeMode; watchlists: Watchlist[] }>({ mode: "pct", watchlists: [] });

function ChangeCell({ row, window }: { row: StockRow; window: SwingWindow }) {
  const { mode } = useContext(CellContext);
  return <ChangeValue value={row[`${window}_${mode}`]} mode={mode} />;
}

function WatchCell({ ticker }: { ticker: string }) {
  const { watchlists } = useContext(CellContext);
  return <WatchButton ticker={ticker} watchlists={watchlists} />;
}

const features = tableFeatures({});
const helper = createColumnHelper<typeof features, StockRow>();
const emptyRows: StockRow[] = [];

const change = (key: SwingWindow, header: string) =>
  helper.display({ id: key, header, cell: (info) => <ChangeCell row={info.row.original} window={key} /> });

const columns = helper.columns([
  helper.display({ id: "watch", header: "", cell: (info) => <WatchCell ticker={info.row.original.ticker} /> }),
  helper.accessor("ticker", {
    header: "Ticker",
    cell: (info) => (
      <Link href={`/company/${info.getValue()}`} className="font-semibold hover:underline">
        {info.getValue()}
      </Link>
    ),
  }),
  helper.accessor("name", {
    header: "Company",
    cell: (info) => (
      <div className="max-w-56">
        <div className="truncate">{info.getValue()}</div>
        <div className="flex gap-1 pt-0.5">
          {info.row.original.asset_type === "etf" && <Badge variant="secondary">ETF</Badge>}
          {info.row.original.in_sp500 && <Badge variant="outline">S&amp;P 500</Badge>}
          {info.row.original.in_ndx100 && <Badge variant="outline">NDX</Badge>}
          {info.row.original.extra_source === "user" && <Badge variant="outline">Added</Badge>}
        </div>
      </div>
    ),
  }),
  helper.accessor("sector", {
    header: "Sector / Industry",
    cell: (info) => (
      <div className="max-w-48 text-xs">
        <div className="truncate">{info.getValue() ?? "—"}</div>
        <div className="truncate text-muted-foreground">{info.row.original.industry ?? ""}</div>
      </div>
    ),
  }),
  helper.accessor("price", { header: "Price", cell: (info) => formatPrice(info.getValue()) }),
  change("chg_1d", "1D"),
  change("chg_1w", "1W"),
  change("chg_ytd", "YTD"),
  helper.accessor("market_cap", { header: "Market cap", cell: (info) => formatMarketCap(info.getValue()) }),
  helper.accessor("volume", { header: "Volume", cell: (info) => formatCompact(info.getValue()) }),
  helper.accessor("pe_ratio", { header: "P/E", cell: (info) => formatNumber(info.getValue(), 1) }),
  helper.accessor("sparkline", { header: "5D", cell: (info) => <Sparkline values={info.getValue()} /> }),
]);

/** Column id -> server sort key. Columns not listed are not sortable. */
export const SORTABLE: Partial<Record<string, SortKey>> = {
  ticker: "ticker",
  name: "name",
  sector: "sector",
  price: "price",
  chg_1d: "chg_1d",
  chg_1w: "chg_1w",
  chg_ytd: "chg_ytd",
  market_cap: "market_cap",
  volume: "volume",
  pe_ratio: "pe_ratio",
};
const NUMERIC = new Set(["price", "chg_1d", "chg_1w", "chg_ytd", "market_cap", "volume", "pe_ratio"]);

export function StocksTable({
  rows,
  mode,
  sort,
  order,
  watchlists,
  loading,
  onSort,
}: {
  rows: StockRow[] | undefined;
  mode: ChangeMode;
  sort: SortKey;
  order: "asc" | "desc";
  watchlists: Watchlist[];
  loading?: boolean;
  onSort: (key: SortKey) => void;
}) {
  const table = useTable({ features, columns, data: rows ?? emptyRows });
  const ctx = useMemo(() => ({ mode, watchlists }), [mode, watchlists]);

  return (
    <CellContext.Provider value={ctx}>
      <div className={cn("rounded-xl border border-border", loading && "opacity-60")}>
        <Table aria-label="Stocks">
          <TableHeader>
            {table.getHeaderGroups().map((group) => (
              <TableRow key={group.id}>
                {group.headers.map((header) => {
                  const key = SORTABLE[header.column.id];
                  const active = key !== undefined && key === sort;
                  return (
                    <TableHead
                      key={header.id}
                      aria-sort={active ? (order === "asc" ? "ascending" : "descending") : undefined}
                      className={cn(NUMERIC.has(header.column.id) && "text-right")}
                    >
                      {key ? (
                        <button
                          type="button"
                          onClick={() => onSort(key)}
                          className={cn(
                            "inline-flex items-center gap-1 hover:text-foreground",
                            active ? "text-foreground" : "text-muted-foreground",
                          )}
                        >
                          <table.FlexRender header={header} />
                          {active &&
                            (order === "asc" ? (
                              <ArrowUpIcon className="size-3" />
                            ) : (
                              <ArrowDownIcon className="size-3" />
                            ))}
                        </button>
                      ) : (
                        <table.FlexRender header={header} />
                      )}
                    </TableHead>
                  );
                })}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows.map((row) => (
              <TableRow key={row.id} data-ticker={row.original.ticker}>
                {row.getAllCells().map((cell) => (
                  <TableCell key={cell.id} className={cn(NUMERIC.has(cell.column.id) && "text-right tabular-nums")}>
                    <table.FlexRender cell={cell} />
                  </TableCell>
                ))}
              </TableRow>
            ))}
            {rows && rows.length === 0 && (
              <TableRow>
                <TableCell colSpan={columns.length} className="py-10 text-center text-muted-foreground">
                  No stocks match these filters.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    </CellContext.Provider>
  );
}
