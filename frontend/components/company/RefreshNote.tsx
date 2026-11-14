import { RefreshCwIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import type { RefreshStatus } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { cn } from "@/lib/utils";

export function RefreshNote({ status, onRefresh, source }: { status?: RefreshStatus; onRefresh?: () => void; source: string }) {
  if (!status) return null;
  return (
    <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
      <span>
        {source}
        {status.fetched_at ? ` · updated ${formatDateTime(status.fetched_at)}` : " · not fetched yet"}
      </span>
      {status.refreshing && <span className="text-amber-600 dark:text-amber-400">refreshing…</span>}
      {status.status === "error" && !status.refreshing && (
        <span role="status" className="text-rose-600 dark:text-rose-400">
          last refresh failed: {status.message}
        </span>
      )}
      {onRefresh && (
        <Button variant="ghost" size="xs" onClick={onRefresh} disabled={status.refreshing} aria-label={`Refresh ${source}`}>
          <RefreshCwIcon className={cn(status.refreshing && "animate-spin")} />
        </Button>
      )}
    </div>
  );
}

/** Poll while the server reports a background refresh in progress. */
export const pollWhileRefreshing = (q: { state: { data?: { refresh?: RefreshStatus } } }) =>
  q.state.data?.refresh?.refreshing ? 2_500 : false;
