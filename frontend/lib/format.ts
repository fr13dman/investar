const DASH = "—";

export function formatCompact(value: number | null | undefined, prefix = ""): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return DASH;
  const abs = Math.abs(value);
  const sign = value < 0 ? "-" : "";
  const units: [number, string][] = [
    [1e12, "T"],
    [1e9, "B"],
    [1e6, "M"],
    [1e3, "K"],
  ];
  for (const [size, suffix] of units) {
    if (abs >= size) return `${sign}${prefix}${(abs / size).toFixed(2)}${suffix}`;
  }
  return `${sign}${prefix}${abs.toFixed(0)}`;
}

export const formatMarketCap = (v: number | null | undefined) => formatCompact(v, "$");

export function formatPrice(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return DASH;
  return `$${value.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function formatChange(value: number | null | undefined, mode: "pct" | "abs"): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return DASH;
  const sign = value > 0 ? "+" : value < 0 ? "-" : "";
  const abs = Math.abs(value);
  return mode === "pct" ? `${sign}${abs.toFixed(2)}%` : `${sign}$${abs.toFixed(2)}`;
}

export function changeTone(value: number | null | undefined): "gain" | "loss" | "flat" {
  if (value === null || value === undefined || !Number.isFinite(value) || value === 0) return "flat";
  return value > 0 ? "gain" : "loss";
}

export function formatNumber(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return DASH;
  return value.toLocaleString("en-US", { maximumFractionDigits: digits });
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return DASH;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return DASH;
  return d.toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return DASH;
  const d = new Date(iso.length === 10 ? `${iso}T00:00:00` : iso);
  if (Number.isNaN(d.getTime())) return DASH;
  return d.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
}
