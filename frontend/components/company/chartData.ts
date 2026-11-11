import type { PriceBar } from "@/lib/api";

export interface LinePoint {
  time: string | number;
  value: number;
}

/** Rebase the benchmark so it starts at the stock's first close: both lines share one price scale and the
 * gap between them is the relative performance over the window. */
export function rebaseBenchmark(stock: PriceBar[], benchmark: PriceBar[]): LinePoint[] {
  if (!stock.length || !benchmark.length) return [];
  const startTime = stock[0].time;
  const aligned = benchmark.filter((b) => b.time >= startTime);
  if (!aligned.length) return [];
  const factor = stock[0].close / aligned[0].close;
  return aligned.map((b) => ({ time: b.time, value: Math.round(b.close * factor * 100) / 100 }));
}

export function periodReturn(bars: { close: number }[]): number | null {
  if (bars.length < 2 || !bars[0].close) return null;
  return (bars[bars.length - 1].close / bars[0].close - 1) * 100;
}
