"use client";

import type { HeatmapPeriod } from "@/lib/api";
import { cn } from "@/lib/utils";

const OPTIONS: { id: HeatmapPeriod; label: string; hint: string }[] = [
  { id: "wow", label: "WoW", hint: "Trailing 1 week" },
  { id: "mom", label: "MoM", hint: "Trailing 1 month" },
  { id: "yoy", label: "YoY", hint: "Trailing 1 year" },
];

export function PeriodToggle({
  value,
  onChange,
}: {
  value: HeatmapPeriod;
  onChange: (p: HeatmapPeriod) => void;
}) {
  return (
    <div role="group" aria-label="Performance period" className="flex w-fit overflow-hidden rounded border border-input">
      {OPTIONS.map((o) => (
        <button
          key={o.id}
          type="button"
          title={o.hint}
          aria-pressed={value === o.id}
          onClick={() => onChange(o.id)}
          className={cn(
            "px-2.5 py-1 text-xs font-medium",
            value === o.id ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground",
          )}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}
