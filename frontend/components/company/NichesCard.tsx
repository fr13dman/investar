"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { NicheChecklist } from "@/components/niches/NicheChecklist";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api, ApiError, type CompanyNiche, type CompanyProfile } from "@/lib/api";

function nicheHref(n: CompanyNiche): string {
  const qs = n.parent_slug ? `niche=${n.parent_slug}&sub=${n.slug}` : `niche=${n.slug}`;
  return `/?browse=niches&${qs}`;
}

function ErrorText({ error }: { error: unknown }) {
  if (!error) return null;
  return (
    <p role="alert" className="text-sm text-rose-600 dark:text-rose-400">
      {error instanceof ApiError ? error.message : "Something went wrong"}
    </p>
  );
}

/** Tag editing for a symbol the user added; curated tags stay checked and locked. */
function EditNiches({ company, onDone }: { company: CompanyProfile; onDone: () => void }) {
  const qc = useQueryClient();
  const niches = useQuery({ queryKey: ["niches"], queryFn: api.niches });
  const [ids, setIds] = useState(() => company.niches.filter((n) => n.source === "user").map((n) => n.id));
  const curated = company.niches.filter((n) => n.source === "curated").map((n) => n.id);
  const save = useMutation({
    mutationFn: () => api.setNiches(company.ticker, ids),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["company", company.ticker] });
      qc.invalidateQueries({ queryKey: ["niches"] });
      onDone();
    },
  });
  return (
    <div className="space-y-3 rounded-lg border border-border p-3">
      <NicheChecklist niches={niches.data ?? []} selected={ids} locked={curated} onChange={setIds} />
      <div className="flex gap-2">
        <Button size="sm" onClick={() => save.mutate()} disabled={save.isPending}>
          Save niches
        </Button>
        <Button size="sm" variant="ghost" onClick={onDone}>
          Cancel
        </Button>
      </div>
      <ErrorText error={save.error} />
    </div>
  );
}

function StopTracking({ ticker }: { ticker: string }) {
  const qc = useQueryClient();
  const router = useRouter();
  const [confirm, setConfirm] = useState(false);
  const remove = useMutation({
    mutationFn: () => api.untrack(ticker),
    onSuccess: () => {
      for (const key of ["stocks", "niches", "sectors", "movers"]) qc.invalidateQueries({ queryKey: [key] });
      router.push("/explore");
    },
  });
  if (!confirm)
    return (
      <Button size="sm" variant="ghost" onClick={() => setConfirm(true)}>
        Stop tracking
      </Button>
    );
  return (
    <>
      <Button size="sm" variant="destructive" onClick={() => remove.mutate()} disabled={remove.isPending}>
        Confirm: stop tracking {ticker}
      </Button>
      <Button size="sm" variant="ghost" onClick={() => setConfirm(false)}>
        Cancel
      </Button>
      <ErrorText error={remove.error} />
    </>
  );
}

export function NichesCard({ company }: { company: CompanyProfile }) {
  const userAdded = company.extra_source === "user";
  const [editing, setEditing] = useState(false);
  if (!userAdded && company.niches.length === 0) return null;

  return (
    <Card size="sm">
      <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-2">
        <CardTitle>Niches</CardTitle>
        {userAdded && (
          <div className="flex flex-wrap items-center gap-2">
            {!editing && (
              <Button size="sm" variant="outline" onClick={() => setEditing(true)}>
                Edit niches
              </Button>
            )}
            <StopTracking ticker={company.ticker} />
          </div>
        )}
      </CardHeader>
      <CardContent className="space-y-3">
        {company.niches.length > 0 ? (
          <ul aria-label="Company niches" className="flex flex-wrap gap-2">
            {company.niches.map((n) => (
              <li key={n.id}>
                <Link href={nicheHref(n)}>
                  <Badge variant={n.source === "user" ? "outline" : "secondary"}>
                    {n.parent_name ? `${n.parent_name} › ${n.name}` : n.name}
                    {n.source === "user" && <span className="opacity-60"> (yours)</span>}
                  </Badge>
                </Link>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-muted-foreground">Not tagged with any niche yet.</p>
        )}
        {userAdded && <p className="text-xs text-muted-foreground">You added {company.ticker} from Explore.</p>}
        {editing && <EditNiches company={company} onDone={() => setEditing(false)} />}
      </CardContent>
    </Card>
  );
}
