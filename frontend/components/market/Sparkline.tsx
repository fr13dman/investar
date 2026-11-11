export function sparklinePath(values: number[], width: number, height: number, pad = 2): string {
  if (values.length < 2) return "";
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const step = (width - pad * 2) / (values.length - 1);
  return values
    .map((v, i) => {
      const x = pad + i * step;
      const y = pad + (height - pad * 2) * (1 - (v - min) / span);
      return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
}

export function Sparkline({
  values,
  width = 80,
  height = 24,
}: {
  values: number[] | null | undefined;
  width?: number;
  height?: number;
}) {
  if (!values || values.length < 2) return <span className="text-muted-foreground">—</span>;
  const up = values[values.length - 1] >= values[0];
  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label={`5-day trend ${up ? "up" : "down"}`}
    >
      <path
        d={sparklinePath(values, width, height)}
        fill="none"
        strokeWidth={1.5}
        className={up ? "stroke-emerald-400" : "stroke-rose-400"}
      />
    </svg>
  );
}
