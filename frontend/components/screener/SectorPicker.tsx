"use client";

import type { SectorNode } from "@/lib/api";

import { TwoLevelPicker } from "./TwoLevelPicker";

const LABELS = { section: "Sectors and industries", parent: "Sector", child: "Industry", all: "All sectors" };

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
  const nodes = sectors.map((s) => ({
    key: s.sector,
    label: s.sector,
    count: s.count,
    children: s.industries.map((i) => ({ key: i.industry, label: i.industry, count: i.count })),
  }));
  return (
    <TwoLevelPicker
      nodes={nodes}
      parent={sector}
      child={industry}
      labels={LABELS}
      showTotal
      onChange={({ parent, child }) => onChange({ sector: parent, industry: child })}
    />
  );
}
