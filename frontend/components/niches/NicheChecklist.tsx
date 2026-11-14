"use client";

import type { NicheNode } from "@/lib/api";

/** Checkbox list of niches grouped by parent; `locked` ids (curated tags) are shown checked and disabled. */
export function NicheChecklist({
  niches,
  selected,
  locked = [],
  onChange,
}: {
  niches: NicheNode[];
  selected: number[];
  locked?: number[];
  onChange: (ids: number[]) => void;
}) {
  const toggle = (id: number) =>
    onChange(selected.includes(id) ? selected.filter((x) => x !== id) : [...selected, id]);
  const box = (id: number, label: string, strong = false) => (
    <label key={id} className="flex items-center gap-2 text-sm">
      <input
        type="checkbox"
        checked={locked.includes(id) || selected.includes(id)}
        disabled={locked.includes(id)}
        onChange={() => toggle(id)}
        className="size-3.5 accent-primary"
      />
      <span className={strong ? "font-medium" : "text-muted-foreground"}>{label}</span>
    </label>
  );
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3" role="group" aria-label="Niches">
      {niches.map((n) => (
        <fieldset key={n.id} className="space-y-1">
          <legend className="sr-only">{n.name}</legend>
          {box(n.id, n.name, true)}
          <div className="space-y-1 pl-4">{n.children.map((c) => box(c.id, c.name))}</div>
        </fieldset>
      ))}
    </div>
  );
}
