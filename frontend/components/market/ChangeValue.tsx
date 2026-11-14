import { changeTone, formatChange } from "@/lib/format";
import { cn } from "@/lib/utils";

const TONE = {
  gain: "text-emerald-600 dark:text-emerald-400",
  loss: "text-rose-600 dark:text-rose-400",
  flat: "text-muted-foreground",
} as const;

export function ChangeValue({
  value,
  mode = "pct",
  className,
}: {
  value: number | null | undefined;
  mode?: "pct" | "abs";
  className?: string;
}) {
  const tone = changeTone(value);
  return (
    <span data-tone={tone} className={cn("tabular-nums", TONE[tone], className)}>
      {formatChange(value, mode)}
    </span>
  );
}
