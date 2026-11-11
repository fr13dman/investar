import { describe, expect, it } from "vitest";

import { changeTone, formatChange, formatCompact, formatMarketCap, formatPrice } from "@/lib/format";

describe("formatters", () => {
  it("formats market caps compactly", () => {
    expect(formatMarketCap(3.12e12)).toBe("$3.12T");
    expect(formatMarketCap(845e9)).toBe("$845.00B");
    expect(formatMarketCap(12.5e6)).toBe("$12.50M");
    expect(formatMarketCap(null)).toBe("—");
    expect(formatCompact(-2500)).toBe("-2.50K");
  });

  it("formats prices", () => {
    expect(formatPrice(1234.5)).toBe("$1,234.50");
    expect(formatPrice(undefined)).toBe("—");
  });

  it("formats signed changes in percent and dollars", () => {
    expect(formatChange(1.234, "pct")).toBe("+1.23%");
    expect(formatChange(-0.5, "pct")).toBe("-0.50%");
    expect(formatChange(-2.5, "abs")).toBe("-$2.50");
    expect(formatChange(0, "pct")).toBe("0.00%");
    expect(formatChange(Number.NaN, "pct")).toBe("—");
  });

  it("classifies tone", () => {
    expect(changeTone(2)).toBe("gain");
    expect(changeTone(-0.1)).toBe("loss");
    expect(changeTone(0)).toBe("flat");
    expect(changeTone(null)).toBe("flat");
  });
});
