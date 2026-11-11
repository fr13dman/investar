import { Suspense } from "react";

import { Screener } from "@/components/screener/Screener";

export default function Home() {
  return (
    <Suspense fallback={<p className="text-sm text-muted-foreground">Loading screener…</p>}>
      <Screener />
    </Suspense>
  );
}
