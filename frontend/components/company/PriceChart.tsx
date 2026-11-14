"use client";

import { useQuery } from "@tanstack/react-query";
import {
  CandlestickSeries,
  ColorType,
  createChart,
  LineSeries,
  type IChartApi,
  type ISeriesApi,
  type Time,
} from "lightweight-charts";
import { useEffect, useRef, useState } from "react";

import { ChangeValue } from "@/components/market/ChangeValue";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api, type PriceRange } from "@/lib/api";
import { useChartColors, type ChartColors } from "@/lib/chartTheme";
import { cn } from "@/lib/utils";

import { periodReturn, rebaseBenchmark } from "./chartData";

const RANGES: { value: PriceRange; label: string }[] = [
  { value: "1d", label: "1D" },
  { value: "1w", label: "1W" },
  { value: "1m", label: "1M" },
  { value: "ytd", label: "YTD" },
  { value: "1y", label: "1Y" },
  { value: "5y", label: "5Y" },
];

function applyChartColors(
  chart: IChartApi,
  series: { candles: ISeriesApi<"Candlestick">; spy: ISeriesApi<"Line"> },
  c: ChartColors,
) {
  chart.applyOptions({
    layout: { textColor: c.axis },
    grid: { vertLines: { color: c.gridFaint }, horzLines: { color: c.gridFaint } },
  });
  series.candles.applyOptions({ upColor: c.up, downColor: c.down, wickUpColor: c.up, wickDownColor: c.down });
  series.spy.applyOptions({ color: c.benchmark });
}

export function PriceChart({ ticker }: { ticker: string }) {
  const [range, setRange] = useState<PriceRange>("1y");
  const container = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<{ candles: ISeriesApi<"Candlestick">; spy: ISeriesApi<"Line"> } | null>(null);
  const colors = useChartColors();
  const colorsRef = useRef(colors);
  const { data, isLoading } = useQuery({ queryKey: ["prices", ticker, range], queryFn: () => api.prices(ticker, range) });

  useEffect(() => {
    if (!container.current || !data) return;
    const chart = createChart(container.current, {
      autoSize: true,
      height: 360,
      layout: { background: { type: ColorType.Solid, color: "transparent" } },
      timeScale: { timeVisible: data.interval !== "1d", borderVisible: false },
      rightPriceScale: { borderVisible: false },
    });
    chartRef.current = chart;
    const candles = chart.addSeries(CandlestickSeries, { borderVisible: false });
    candles.setData(data.bars.map((b) => ({ time: b.time as Time, open: b.open, high: b.high, low: b.low, close: b.close })));
    const spy = chart.addSeries(LineSeries, { lineWidth: 2, priceLineVisible: false, lastValueVisible: false });
    spy.setData(rebaseBenchmark(data.bars, data.benchmark.bars).map((p) => ({ time: p.time as Time, value: p.value })));
    seriesRef.current = { candles, spy };
    applyChartColors(chart, seriesRef.current, colorsRef.current);
    chart.timeScale().fitContent();
    return () => {
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, [data]);

  useEffect(() => {
    colorsRef.current = colors;
    if (chartRef.current && seriesRef.current) applyChartColors(chartRef.current, seriesRef.current, colors);
  }, [colors]);

  const stockRet = data ? periodReturn(data.bars) : null;
  const spyRet = data ? periodReturn(data.benchmark.bars.filter((b) => !data.bars.length || b.time >= data.bars[0].time)) : null;

  return (
    <Card>
      <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-3">
        <CardTitle className="flex flex-wrap items-center gap-4">
          Price
          <span className="flex items-center gap-1 text-sm font-normal">
            {ticker} <ChangeValue value={stockRet} />
          </span>
          <span className="flex items-center gap-1 text-sm font-normal text-blue-600 dark:text-blue-400">
            SPY (rebased) <ChangeValue value={spyRet} />
          </span>
        </CardTitle>
        <div role="group" aria-label="Chart range" className="flex gap-1">
          {RANGES.map((r) => (
            <button
              key={r.value}
              type="button"
              aria-pressed={range === r.value}
              onClick={() => setRange(r.value)}
              className={cn(
                "rounded-md px-2 py-0.5 text-xs",
                range === r.value ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground",
              )}
            >
              {r.label}
            </button>
          ))}
        </div>
      </CardHeader>
      <CardContent>
        {isLoading && <p className="text-sm text-muted-foreground">Loading prices…</p>}
        {data && data.bars.length === 0 && <p className="text-sm text-muted-foreground">No price history yet.</p>}
        <div ref={container} data-testid="price-chart" className="h-[360px] w-full" />
      </CardContent>
    </Card>
  );
}
