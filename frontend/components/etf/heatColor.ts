/** Finviz-style green/red heat from a percent return. */

export function heatColor(pct: number | null | undefined, muted = false): string {
  if (pct == null || Number.isNaN(pct)) return muted ? "var(--heat-neutral-muted)" : "var(--heat-neutral)";
  const mag = Math.min(Math.abs(pct) / 8, 1); // saturate around ±8%
  if (pct >= 0) {
    return `color-mix(in oklab, var(--heat-up) ${Math.round(35 + mag * 65)}%, var(--heat-neutral))`;
  }
  return `color-mix(in oklab, var(--heat-down) ${Math.round(35 + mag * 65)}%, var(--heat-neutral))`;
}

export function heatText(pct: number | null | undefined): string {
  if (pct == null || Number.isNaN(pct)) return "—";
  const sign = pct > 0 ? "+" : "";
  return `${sign}${pct.toFixed(2)}%`;
}
