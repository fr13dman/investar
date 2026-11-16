import { Suspense } from "react";

import { EtfHub } from "@/components/etf/EtfHub";

export default function EtfsPage() {
  return (
    <Suspense fallback={<p className="text-sm text-muted-foreground">Loading ETFs…</p>}>
      <EtfHub mode="niches" />
    </Suspense>
  );
}
