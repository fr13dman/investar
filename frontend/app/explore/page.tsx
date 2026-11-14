import { Suspense } from "react";

import { Explore } from "@/components/explore/Explore";

export default function ExplorePage() {
  return (
    <Suspense fallback={<p className="text-sm text-muted-foreground">Loading explore…</p>}>
      <Explore />
    </Suspense>
  );
}
