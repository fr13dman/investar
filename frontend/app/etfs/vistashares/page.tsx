import { Suspense } from "react";

import { EtfHub } from "@/components/etf/EtfHub";

export default function VistaSharesEtfsPage() {
  return (
    <Suspense fallback={<p className="text-sm text-muted-foreground">Loading VistaShares…</p>}>
      <EtfHub mode="vistashares" />
    </Suspense>
  );
}
