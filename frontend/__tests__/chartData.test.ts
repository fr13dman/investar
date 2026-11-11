import { describe, expect, it } from "vitest";

import { periodReturn, rebaseBenchmark } from "@/components/company/chartData";

const bar = (time: string, close: number) => ({ time, open: close, high: close, low: close, close, volume: 0 });

describe("chart data", () => {
  it("rebases the benchmark to the stock's first close", () => {
    const stock = [bar("2026-01-05", 200), bar("2026-01-06", 210)];
    const spy = [bar("2026-01-02", 480), bar("2026-01-05", 500), bar("2026-01-06", 525)];
    expect(rebaseBenchmark(stock, spy)).toEqual([
      { time: "2026-01-05", value: 200 },
      { time: "2026-01-06", value: 210 },
    ]);
  });

  it("handles empty input", () => {
    expect(rebaseBenchmark([], [bar("2026-01-05", 1)])).toEqual([]);
    expect(rebaseBenchmark([bar("2026-01-05", 1)], [])).toEqual([]);
  });

  it("computes period return", () => {
    expect(periodReturn([{ close: 100 }, { close: 110 }])).toBeCloseTo(10);
    expect(periodReturn([{ close: 100 }])).toBeNull();
  });
});
