"use client";

import type { SectorNode } from "@/lib/api";
import { cn } from "@/lib/utils";

function Chip({
  active,
  onClick,
  children,
  label,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
  label?: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      aria-label={label}
      className={cn(
        "rounded-full border px-3 py-1 text-xs transition-colors",
        active
          ? "border-primary bg-primary text-primary-foreground"
          : "border-border text-muted-foreground hover:border-foreground/40 hover:text-foreground",
      )}
    >
      {children}
    </button>
  );
}

export function SectorPicker({
  sectors,
  sector,
  industry,
  onChange,
}: {
  sectors: SectorNode[];
  sector?: string;
  industry?: string;
  onChange: (next: { sector?: string; industry?: string }) => void;
}) {
  const active = sectors.find((s) => s.sector === sector);
  const total = sectors.reduce((n, s) => n + s.count, 0);
  return (
    <section aria-label="Sectors and industries" className="space-y-3">
      <div className="flex flex-wrap gap-2" role="group" aria-label="Sector">
        <Chip active={!sector} onClick={() => onChange({})}>
          All sectors <span className="opacity-60">{total}</span>
        </Chip>
        {sectors.map((s) => (
          <Chip
            key={s.sector}
            active={s.sector === sector}
            label={`Sector ${s.sector}`}
            onClick={() => onChange(s.sector === sector ? {} : { sector: s.sector })}
          >
            {s.sector} <span className="opacity-60">{s.count}</span>
          </Chip>
        ))}
      </div>
      {active && active.industries.length > 0 && (
        <div className="flex flex-wrap gap-2 border-l-2 border-border pl-3" role="group" aria-label="Industry">
          <Chip active={!industry} onClick={() => onChange({ sector })}>
            All {active.sector}
          </Chip>
          {active.industries.map((i) => (
            <Chip
              key={i.industry}
              active={i.industry === industry}
              label={`Industry ${i.industry}`}
              onClick={() =>
                onChange({ sector, industry: i.industry === industry ? undefined : i.industry })
              }
            >
              {i.industry} <span className="opacity-60">{i.count}</span>
            </Chip>
          ))}
        </div>
      )}
    </section>
  );
}
