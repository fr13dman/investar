"use client";

import { cn } from "@/lib/utils";

export interface PickerLeaf {
  key: string;
  label: string;
  count: number;
  title?: string;
}

export interface PickerNode extends PickerLeaf {
  children: PickerLeaf[];
}

function Chip({
  active,
  onClick,
  children,
  label,
  title,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
  label?: string;
  title?: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      aria-label={label}
      title={title}
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

/** Parent chips, then the selected parent's children; used for sector/industry and niche/sub-niche. */
export function TwoLevelPicker({
  nodes,
  parent,
  child,
  onChange,
  labels,
  showTotal = false,
}: {
  nodes: PickerNode[];
  parent?: string;
  child?: string;
  onChange: (next: { parent?: string; child?: string }) => void;
  labels: { section: string; parent: string; child: string; all: string };
  /** Only meaningful when parents don't overlap (sectors do not; niches can). */
  showTotal?: boolean;
}) {
  const active = nodes.find((n) => n.key === parent);
  const total = showTotal ? nodes.reduce((n, s) => n + s.count, 0) : undefined;
  return (
    <section aria-label={labels.section} className="space-y-3">
      <div className="flex flex-wrap gap-2" role="group" aria-label={labels.parent}>
        <Chip active={!parent} onClick={() => onChange({})}>
          {labels.all} {total !== undefined && <span className="opacity-60">{total}</span>}
        </Chip>
        {nodes.map((n) => (
          <Chip
            key={n.key}
            active={n.key === parent}
            label={`${labels.parent} ${n.label}`}
            title={n.title}
            onClick={() => onChange(n.key === parent ? {} : { parent: n.key })}
          >
            {n.label} <span className="opacity-60">{n.count}</span>
          </Chip>
        ))}
      </div>
      {active && active.children.length > 0 && (
        <div className="flex flex-wrap gap-2 border-l-2 border-border pl-3" role="group" aria-label={labels.child}>
          <Chip active={!child} onClick={() => onChange({ parent })}>
            All {active.label}
          </Chip>
          {active.children.map((c) => (
            <Chip
              key={c.key}
              active={c.key === child}
              label={`${labels.child} ${c.label}`}
              title={c.title}
              onClick={() => onChange({ parent, child: c.key === child ? undefined : c.key })}
            >
              {c.label} <span className="opacity-60">{c.count}</span>
            </Chip>
          ))}
        </div>
      )}
    </section>
  );
}
