"use client";

import type { NicheNode } from "@/lib/api";

import { TwoLevelPicker } from "./TwoLevelPicker";

const LABELS = { section: "Niches and sub-niches", parent: "Niche", child: "Sub-niche", all: "All niches" };

export function nicheName(niches: NicheNode[], slug?: string): string | undefined {
  if (!slug) return undefined;
  for (const n of niches) {
    if (n.slug === slug) return n.name;
    const c = n.children.find((x) => x.slug === slug);
    if (c) return c.name;
  }
  return undefined;
}

export function NichePicker({
  niches,
  niche,
  sub,
  onChange,
}: {
  niches: NicheNode[];
  niche?: string;
  sub?: string;
  onChange: (next: { niche?: string; sub?: string }) => void;
}) {
  const nodes = niches.map((n) => ({
    key: n.slug,
    label: n.name,
    count: n.count,
    title: n.description ?? undefined,
    children: n.children.map((c) => ({ key: c.slug, label: c.name, count: c.count, title: c.description ?? undefined })),
  }));
  return (
    <TwoLevelPicker
      nodes={nodes}
      parent={niche}
      child={sub}
      labels={LABELS}
      onChange={({ parent, child }) => onChange({ niche: parent, sub: child })}
    />
  );
}
