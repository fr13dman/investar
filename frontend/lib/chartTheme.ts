import { useTheme, type ResolvedTheme } from "./theme";

export interface ChartColors {
  axis: string;
  grid: string;
  gridFaint: string;
  tooltip: { background: string; border: string; color: string };
  up: string;
  down: string;
  benchmark: string;
  secondary: string;
  tertiary: string;
  mapEmpty: string;
  mapStroke: string;
  /** "r, g, b" of the map fill, combined with a per-country alpha. */
  mapRgb: string;
}

export const CHART_COLORS: Record<ResolvedTheme, ChartColors> = {
  dark: {
    axis: "#a3a3a3",
    grid: "rgba(255,255,255,0.06)",
    gridFaint: "rgba(255,255,255,0.04)",
    tooltip: { background: "#171717", border: "none", color: "#fafafa" },
    up: "#34d399",
    down: "#fb7185",
    benchmark: "#60a5fa",
    secondary: "#34d399",
    tertiary: "#a78bfa",
    mapEmpty: "rgba(255,255,255,0.06)",
    mapStroke: "rgba(255,255,255,0.15)",
    mapRgb: "52, 211, 153",
  },
  light: {
    axis: "#525252",
    grid: "rgba(0,0,0,0.08)",
    gridFaint: "rgba(0,0,0,0.05)",
    tooltip: { background: "#ffffff", border: "1px solid #e5e5e5", color: "#171717" },
    up: "#059669",
    down: "#e11d48",
    benchmark: "#2563eb",
    secondary: "#059669",
    tertiary: "#7c3aed",
    mapEmpty: "rgba(0,0,0,0.06)",
    mapStroke: "rgba(0,0,0,0.25)",
    mapRgb: "5, 150, 105",
  },
};

export function useChartColors(): ChartColors {
  return CHART_COLORS[useTheme().resolved];
}
