"use client";

import { useMemo } from "react";
import { ResponsiveContainer, Tooltip, Treemap as ReTreemap } from "recharts";

import { formatAum } from "./format";
import { heatColor, heatText } from "./heatColor";

export interface TreemapDatum {
  name: string;
  ticker?: string | null;
  size: number;
  return_pct: number | null;
  kind?: string;
  navigable?: boolean;
}

/** Recharts clones content with node layout props; leaf fields live on `payload`. */
function Content(props: {
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  name?: string;
  return_pct?: number | null;
  ticker?: string | null;
  kind?: string;
  payload?: TreemapDatum & { name?: string };
}) {
  const { x = 0, y = 0, width = 0, height = 0, payload } = props;
  if (width < 2 || height < 2) return null;
  const ticker = props.ticker ?? payload?.ticker ?? null;
  const kind = props.kind ?? payload?.kind;
  const return_pct = props.return_pct ?? payload?.return_pct ?? null;
  const name = props.name ?? payload?.name ?? "";
  const label = ticker || name || "";
  const showReturn = width > 48 && height > 28;
  const showLabel = width > 28 && height > 16;
  return (
    <g>
      <rect
        x={x}
        y={y}
        width={width}
        height={height}
        style={{ fill: heatColor(return_pct, kind === "other"), stroke: "var(--background)", strokeWidth: 1 }}
      />
      {showLabel && (
        <text x={x + 4} y={y + 14} fill="var(--heat-label)" fontSize={11} fontWeight={600}>
          {label.length > width / 7 ? `${label.slice(0, Math.max(2, Math.floor(width / 7)))}…` : label}
        </text>
      )}
      {showReturn && (
        <text x={x + 4} y={y + 28} fill="var(--heat-label)" fontSize={10}>
          {heatText(return_pct)}
        </text>
      )}
    </g>
  );
}

export function AllocationTreemap({
  data,
  onSelect,
  ariaLabel,
  sizeIsWeight = true,
}: {
  data: TreemapDatum[];
  onSelect?: (d: TreemapDatum) => void;
  ariaLabel: string;
  /** ETF maps size by AUM; holdings maps size by weight %. */
  sizeIsWeight?: boolean;
}) {
  const tree = useMemo(
    () =>
      data
        .filter((d) => d.size > 0)
        .map((d) => ({
          ...d,
          // Recharts nameKey defaults to "name"; keep ticker visible as the node name.
          name: d.ticker || d.name,
        })),
    [data],
  );

  if (tree.length === 0) {
    return <p className="text-sm text-muted-foreground">No allocation data yet.</p>;
  }

  return (
    <div className="h-72 w-full rounded border border-border bg-[var(--heat-neutral)]" role="img" aria-label={ariaLabel}>
      <ResponsiveContainer width="100%" height="100%">
        <ReTreemap
          data={tree}
          dataKey="size"
          nameKey="name"
          aspectRatio={4 / 3}
          stroke="var(--background)"
          content={<Content />}
          isAnimationActive={false}
          onClick={(node) => {
            const raw = node as unknown as TreemapDatum & { payload?: TreemapDatum };
            const d = raw.payload ?? raw;
            if (d?.navigable !== false && (d.ticker || d.name)) onSelect?.(d);
          }}
        >
          <Tooltip
            content={({ payload }) => {
              const d = payload?.[0]?.payload as TreemapDatum | undefined;
              if (!d) return null;
              return (
                <div className="rounded border border-border bg-popover px-2 py-1 text-xs shadow">
                  <div className="font-semibold">{d.ticker || d.name}</div>
                  {d.name && d.ticker && d.name !== d.ticker && (
                    <div className="text-muted-foreground">{d.name}</div>
                  )}
                  <div>
                    {sizeIsWeight ? `Weight ${d.size.toFixed(2)}%` : `AUM ${formatAum(d.size)}`}
                  </div>
                  <div>{heatText(d.return_pct)}</div>
                </div>
              );
            }}
          />
        </ReTreemap>
      </ResponsiveContainer>
    </div>
  );
}

export function EtfMapTreemap({
  data,
  onSelect,
  ariaLabel,
}: {
  data: TreemapDatum[];
  onSelect?: (d: TreemapDatum) => void;
  ariaLabel: string;
}) {
  return <AllocationTreemap data={data} onSelect={onSelect} ariaLabel={ariaLabel} sizeIsWeight={false} />;
}
